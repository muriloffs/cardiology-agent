"""Fetch cardiology Substack posts via Gemini API with Google Search grounding.

Substack blocks GitHub Actions runner IPs (datacenter blocking via Cloudflare),
so direct RSS fails with 403 in CI. Gemini grounding works around this by
having Google's crawler fetch the content.

Pattern (validated empirically by user research): grounded query asking for
recent posts from a specific Substack publication → multi-line text response
with rich fields (TITLE/URL/DATE/AUTOR/TEMA/BULLETS/RESUMO/TAGS) → block
parser → structured items.

12 Substacks targeted (9 international + 3 Brazilian), 7-day window.

Returns a flat list of substack items for direct injection into report['substacks'].
"""

import os
import re
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_CALL_TIMEOUT = 90
DEFAULT_DAYS_BACK = 7  # Substacks publish 1-3x/week
DEFAULT_MAX_ITEMS = 3


# ──────────────────────────────────────────────────────────────────────
# CLIENT + GROUNDED CALL HELPER (same pattern as fetch_gemini_external.py)
# ──────────────────────────────────────────────────────────────────────

def _get_client():
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return None
    try:
        from google import genai
        return genai.Client(api_key=api_key)
    except ImportError:
        logger.error("google-genai SDK not installed — pip install google-genai")
        return None


def _extract_text(response) -> str:
    if hasattr(response, "text") and response.text:
        return response.text.strip()
    if hasattr(response, "candidates") and response.candidates:
        parts_text = []
        for cand in response.candidates:
            if hasattr(cand, "content") and cand.content and hasattr(cand.content, "parts"):
                for part in cand.content.parts or []:
                    if hasattr(part, "text") and part.text:
                        parts_text.append(part.text)
        return "\n".join(parts_text).strip()
    return ""


def _grounded_call(client, prompt: str, label: str) -> str:
    try:
        from google.genai import types
        config = types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.2,  # tiny bit of creativity helps with summarization
        )
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=config,
        )
        text = _extract_text(response)
        if not text:
            logger.warning(f"[{label}] Gemini returned empty text")
        return text
    except Exception as e:
        logger.warning(f"[{label}] Gemini call failed: {type(e).__name__}: {e}")
        return ""


# ──────────────────────────────────────────────────────────────────────
# RICH BLOCK PARSER
# ──────────────────────────────────────────────────────────────────────

def _parse_substack_blocks(text: str) -> list[dict]:
    """Parse Gemini rich-format response into a list of post dicts.

    Expected format per post (separated by '---' or blank lines):
        TITLE: <title>
        URL: <url>
        DATE: <YYYY-MM-DD>
        AUTOR: <author>
        TEMA: <theme>
        BULLETS:
        - bullet 1
        - bullet 2
        RESUMO: <summary>
        TAGS: tag1, tag2, tag3
    """
    if not text or text.strip().upper() == "NONE":
        return []

    # Strip markdown code fences if Gemini added any
    text = re.sub(r"```\w*\n?", "", text)
    text = text.replace("```", "")

    # Split into post blocks. Try '---' separator first; fall back to double newline
    if "---" in text:
        blocks = re.split(r"\n\s*---+\s*\n", text)
    else:
        blocks = re.split(r"\n\s*\n+", text)

    posts = []
    for raw_block in blocks:
        block = raw_block.strip()
        if not block or block.upper() == "NONE":
            continue

        post = _parse_single_block(block)
        if post and post.get("titulo") and post.get("url"):
            posts.append(post)

    return posts


def _parse_single_block(block: str) -> dict | None:
    """Extract fields from one post block."""
    lines = block.split("\n")

    post = {
        "titulo": "",
        "url": "",
        "data_pub": "",
        "autor": "",
        "tema": "",
        "bullets": [],
        "resumo": "",
        "tags": [],
    }

    current_field = None
    bullet_buffer = []

    for raw_line in lines:
        line = raw_line.rstrip()
        if not line.strip():
            continue

        # Match LABEL: value pattern (case-insensitive)
        m = re.match(r"^\s*([A-Za-zÁÉÍÓÚá-ú]+)\s*:\s*(.*)$", line)
        if m:
            label = m.group(1).upper()
            value = m.group(2).strip()

            if label in ("TITLE", "TITULO"):
                current_field = "titulo"
                post["titulo"] = _strip_markdown(value)
            elif label == "URL":
                current_field = "url"
                # Sometimes Gemini wraps URLs in markdown — strip
                v = re.sub(r"^\[.*?\]\((.*)\)$", r"\1", value)
                v = v.strip("()<>[] ")
                post["url"] = v
            elif label in ("DATE", "DATA"):
                current_field = "data_pub"
                post["data_pub"] = value
            elif label in ("AUTOR", "AUTHOR"):
                current_field = "autor"
                post["autor"] = _strip_markdown(value)
            elif label == "TEMA":
                current_field = "tema"
                post["tema"] = _strip_markdown(value)
            elif label == "BULLETS":
                current_field = "bullets"
                # If bullets are inline on same line (rare), capture
                if value:
                    bullet_buffer.append(value)
            elif label == "RESUMO":
                current_field = "resumo"
                post["resumo"] = _strip_markdown(value)
            elif label == "TAGS":
                current_field = "tags"
                post["tags"] = [t.strip().lstrip("#") for t in value.split(",") if t.strip()]
            else:
                current_field = None  # unknown label
            continue

        # Continuation lines for current_field
        stripped = line.strip()
        if current_field == "bullets":
            # Bullet lines start with -, *, •, or number.
            bullet_text = re.sub(r"^[\-\*•\d\.\)]+\s*", "", stripped).strip()
            if bullet_text:
                bullet_buffer.append(bullet_text)
        elif current_field == "resumo":
            post["resumo"] = (post["resumo"] + " " + stripped).strip()
        elif current_field == "titulo":
            post["titulo"] = (post["titulo"] + " " + stripped).strip()

    if bullet_buffer:
        post["bullets"] = [_strip_markdown(b) for b in bullet_buffer[:6]]

    # URL must look like one
    if not post["url"].startswith("http"):
        return None
    if not post["titulo"]:
        return None

    return post


def _strip_markdown(s: str) -> str:
    """Remove common markdown artifacts from Gemini output."""
    if not s:
        return s
    # Bold/italic **text** or *text*
    s = re.sub(r"\*+([^*]+)\*+", r"\1", s)
    # Backticks
    s = s.replace("`", "")
    # Citation markers like [1], [2] that Gemini sometimes adds
    s = re.sub(r"\[\d+\]", "", s)
    return s.strip()


# ──────────────────────────────────────────────────────────────────────
# PROMPT BUILDER
# ──────────────────────────────────────────────────────────────────────

def _build_substack_prompt(
    publication_name: str,
    publication_url: str,
    days_back: int = DEFAULT_DAYS_BACK,
    max_items: int = DEFAULT_MAX_ITEMS,
) -> str:
    return f"""Use Google Search to find the {max_items} most recent cardiology posts published on the Substack "{publication_name}" ({publication_url}).

For each post, respond using EXACTLY this format. Separate posts with a line containing only '---'.

TITLE: <full post title>
URL: <complete post URL on substack.com>
DATE: <publication date as YYYY-MM-DD>
AUTOR: <author name>
TEMA: <main topic in 2 to 5 words, English or Portuguese>
BULLETS:
- <key takeaway 1, one short sentence>
- <key takeaway 2>
- <key takeaway 3>
RESUMO: <2-3 sentences in Brazilian Portuguese summarizing the post's clinical message>
TAGS: <3 to 5 short keywords separated by commas>

Plain text only. No JSON. No markdown formatting like ** or ##. If no posts found in the window: respond with the single word NONE."""


# ──────────────────────────────────────────────────────────────────────
# 12 SUBSTACK FETCHERS
# ──────────────────────────────────────────────────────────────────────

def _make_fetcher(name: str, slug: str, url: str, categoria: str, default_autor: str = ""):
    """Factory: returns a fetcher function for a single Substack."""
    def fetch(client):
        prompt = _build_substack_prompt(name, url)
        text = _grounded_call(client, prompt, slug)
        posts = _parse_substack_blocks(text)
        for p in posts:
            p["publicacao"] = name
            p["fonte_origem"] = slug
            p["categoria"] = categoria
            if not p.get("autor") and default_autor:
                p["autor"] = default_autor
        logger.info(f"Gemini Substack [{slug}]: {len(posts)} posts")
        return posts
    fetch.__name__ = f"fetch_{slug}"
    return fetch


# Definitions: (name, slug, url, categoria, default_autor)
SUBSTACKS_INT = [
    ("Ground Truths",                 "topol",         "erictopol.substack.com",            "tech-policy",         "Eric Topol"),
    ("Sensible Medicine",             "sensible_med",  "sensiblemed.substack.com",          "trials-critique",     ""),
    ("The Skeptical Cardiologist",    "skeptical",     "theskepticalcardiologist.substack.com", "consumer-tech",   "Anthony Pearson"),
    ("Cardiology Trial's Substack",   "cardio_trials", "cardiologytrials.substack.com",     "trials-summary",      ""),
    ("500 Rules of Cardiology",       "thompson",      "pauldthompsonmd.substack.com",      "clinical-pearls",     "Paul D. Thompson"),
    ("Numerical Heart",               "numerical",     "numericalheart.substack.com",       "ai-genomics",         "Venk Murthy"),
    ("Dr Paddy Barrett",              "barrett",       "drpaddybarrett.substack.com",       "prevention-philosophy", "Paddy Barrett"),
    ("Gregory Katz's Substack",       "gkatz",         "gregorykatz.substack.com",          "education",           "Gregory Katz"),
    ("CardioNerds Substack",          "cardionerds",   "cardionerds.substack.com",          "education",           ""),
]

SUBSTACKS_BR = [
    ("DozeNews / Doze por Oito",      "dozenews",      "dozenews.com.br",                   "br-clinical",         ""),
    ("Jornal do Clube da Cardio",     "clubedacardio", "clubedacardio.substack.com",        "br-congress",         ""),
    ("Cardio DF",                     "cardiodf",      "cardiodf.substack.com",             "br-clinical",         ""),
]

ALL_SUBSTACKS = SUBSTACKS_INT + SUBSTACKS_BR


# ──────────────────────────────────────────────────────────────────────
# ORCHESTRATOR
# ──────────────────────────────────────────────────────────────────────

def fetch_all_substacks() -> list[dict[str, Any]]:
    """Run all 12 Substack fetchers in parallel.

    Returns:
        List of substack post dicts (flat). Empty if API key missing or all fail.
    """
    client = _get_client()
    if not client:
        logger.warning("GOOGLE_API_KEY not set — Substack fetcher skipped")
        return []

    fetchers = [
        (slug, _make_fetcher(name, slug, url, cat, autor))
        for (name, slug, url, cat, autor) in ALL_SUBSTACKS
    ]

    posts: list[dict] = []
    seen_urls: set[str] = set()

    # 3 workers respects Flash rate limits with safety margin
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(fn, client): slug for slug, fn in fetchers}
        for future in as_completed(futures):
            slug = futures[future]
            try:
                result = future.result(timeout=GEMINI_CALL_TIMEOUT)
                for p in result:
                    url = p.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        posts.append(p)
            except Exception as e:
                logger.error(f"Substack fetcher [{slug}] failed: {e}")

    # Assign sequential IDs
    for i, p in enumerate(posts, 1):
        p["id"] = f"sub_{i:03d}"

    logger.info(f"Gemini Substacks TOTAL: {len(posts)} unique posts from {len(ALL_SUBSTACKS)} sources")
    return posts


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.INFO)

    result = fetch_all_substacks()
    print(f"\n{'=' * 60}")
    print(f"Total Substack posts: {len(result)}")
    print(f"{'=' * 60}\n")
    for item in result[:5]:
        print(f"[{item['fonte_origem']}] {item['publicacao']} — {item['autor']}")
        print(f"  📄 {item['titulo']}")
        print(f"  🔖 Tema: {item.get('tema', '')}")
        print(f"  📝 {item.get('resumo', '')[:150]}")
        print(f"  🔗 {item['url']}")
        print()
