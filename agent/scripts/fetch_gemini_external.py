"""Fetch external cardiology sources via Gemini API with Google Search grounding.

Fills gaps that PubMed/RSS can't cover:
- Journal articles published TODAY (online-first, before PubMed indexing lag)
- Medscape cardiology news (paywalled, no public RSS)
- ESC/ACC press releases (sociedade websites)
- Bluesky cardio posts (cardiologists migrated post-Twitter)

Uses gemini-2.5-flash with Google Search grounding (free tier, validated
empirically). Each fetcher uses a SIMPLE plain-text prompt format (Flash
struggles with complex JSON-output + grounding combined).

Pattern: grounded query → plain text response (TITLE | URL | DATE | DOI) →
regex parse → structured items.

Returns dict with two arrays for injection into report:
- noticias_external: journal articles + news (merged into report["noticias"])
- discussoes_bluesky: Bluesky posts (separate array, parallel to discussoes_x)
"""

import os
import re
import logging
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_CALL_TIMEOUT = 90  # per call (grounded calls take ~30s typically)

# Cardio keyword filter — broad enough to catch most cardio content
# Reused from fetch_articles.py / fetch_youtube.py
CARDIO_KEYWORDS = [
    "cardio", "heart", "cardiac", "coronary", "myocard", "ekg", "ecg",
    "afib", "atrial fibrillation", "atrial", "ventricular",
    "lipid", "cholesterol", "ldl", "hdl", "statin",
    "hypertension", "blood pressure",
    "anticoag", "warfarin", "doac", "noac",
    "ischem", "infarct", "stemi", "nstemi", "acute coronary",
    "valve", "valvular", "mitral", "aortic",
    "failure", "hfref", "hfpef", "hfmref",
    "arrhyth", "syncope", "tachy", "brady",
    "stent", "pci", "tavr", "cabg", "ablation",
    "echo", "echocardio", "imaging",
    "sglt2", "glp-1", "arni", "sacubitril",
    # PT-BR variants
    "coraç", "infart", "arritm", "valv", "isquêm",
    "pressão", "press arterial", "colester", "hipertens",
]


# ──────────────────────────────────────────────────────────────────────
# CLIENT + GROUNDED CALL HELPER
# ──────────────────────────────────────────────────────────────────────

def _get_client():
    """Returns Gemini client or None if API key not set."""
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
    """Robust extraction handling both response.text and parts-based structure."""
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


def _grounded_call(client, prompt: str, label: str = "gemini") -> str:
    """Make 1 grounded Gemini Flash call. Returns text or empty on failure."""
    try:
        from google.genai import types
        config = types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.0,
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
# TEXT PARSER (TITLE | URL | DATE | DOI lines)
# ──────────────────────────────────────────────────────────────────────

def _parse_pipe_format(text: str) -> list[dict]:
    """Parse 'TITLE: <t> | URL: <u> | DATE: <d> | DOI: <doi>' lines.

    Robust to variations:
    - With or without LABEL: prefixes
    - Lines starting with #, -, *, numbers (1.)
    - 'NONE' or empty responses → []
    """
    if not text or text.strip().upper() == "NONE":
        return []

    items = []
    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        # Skip headers, comments, list bullets
        line = re.sub(r"^\s*[\-\*\d\.\)]+\s*", "", line)  # remove bullets/numbers
        if line.upper() in ("NONE", "NO RESULTS", "NOT FOUND"):
            continue
        if "|" not in line:
            continue

        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 2:
            continue

        # Strip "LABEL:" prefixes (TITLE:, URL:, DATE:, DOI:)
        def strip_label(s: str) -> str:
            return re.sub(r"^[A-Z]+\s*:?\s*", "", s).strip()

        title = strip_label(parts[0])
        url = strip_label(parts[1]) if len(parts) > 1 else ""
        date_raw = strip_label(parts[2]) if len(parts) > 2 else ""
        doi_raw = strip_label(parts[3]) if len(parts) > 3 else ""

        # Validate URL looks like one
        if not url.startswith("http"):
            continue
        if not title:
            continue

        # Normalize DOI
        doi = doi_raw if doi_raw and doi_raw.lower() not in ("null", "none", "n/a", "") else None

        items.append({
            "titulo": title,
            "url": url,
            "data_publicacao_raw": date_raw,
            "doi": doi,
        })

    return items


def _matches_cardio(title: str, extra_text: str = "") -> bool:
    """Cardio relevance keyword filter."""
    text = f"{title} {extra_text}".lower()
    return any(kw in text for kw in CARDIO_KEYWORDS)


# ──────────────────────────────────────────────────────────────────────
# FETCHERS — one per source group
# ──────────────────────────────────────────────────────────────────────

def _build_journal_prompt(sites_label: str, sites_list: list[str], days_back: int) -> str:
    """Build a simple grounded prompt for journal article discovery."""
    brasilia_tz = timezone(timedelta(hours=-3))
    today = datetime.now(brasilia_tz).strftime("%Y-%m-%d")
    cutoff = (datetime.now(brasilia_tz) - timedelta(days=days_back)).strftime("%Y-%m-%d")

    sites_text = "\n".join(f"- {s}" for s in sites_list)

    return f"""Use Google Search to find cardiology articles published between {cutoff} and {today} on these {sites_label} sites:

{sites_text}

For EACH cardiology article found in this date window, return ONE line in this exact format:
TITLE: <exact article title> | URL: <full article URL> | DATE: <YYYY-MM-DD> | DOI: <DOI if shown, else null>

Rules:
- Maximum 10 items
- Only cardiology articles (heart, cardiovascular, hypertension, lipids, valve, arrhythmia, etc.)
- Only articles with publication date IN the window {cutoff} to {today}
- Use the article's "Originally Published" or "Published Online" date, NOT the indexing date
- DO NOT invent — if date unclear, skip the article
- If you find nothing, respond with just: NONE

Output: plain text only. No JSON. No markdown. No explanations. Just the lines."""


def fetch_aha_journals(client, days_back: int = 2) -> list[dict]:
    """Circulation, JAHA, Stroke, Hypertension, AHA family."""
    prompt = _build_journal_prompt(
        "AHA Journal family",
        [
            "ahajournals.org/journal/circ (Circulation)",
            "ahajournals.org/journal/circaha (Circulation HF/Interventions/Imaging/Arrhythmia)",
            "ahajournals.org/journal/jaha (JAHA)",
            "ahajournals.org/journal/hyp (Hypertension)",
            "ahajournals.org/journal/str (Stroke)",
        ],
        days_back,
    )
    text = _grounded_call(client, prompt, "AHA")
    items = _parse_pipe_format(text)
    for item in items:
        item["publicacao"] = "AHA Journals (Circulation/JAHA/Hypertension)"
        item["fonte_origem"] = "aha"
    logger.info(f"Gemini AHA Journals: {len(items)} items")
    return items


def fetch_jacc_family(client, days_back: int = 2) -> list[dict]:
    """JACC main + subjournals."""
    prompt = _build_journal_prompt(
        "JACC family",
        [
            "jacc.org (JACC main)",
            "jacc.org/journal/heart-failure",
            "jacc.org/journal/intv (Interventions)",
            "jacc.org/journal/img (Imaging)",
            "jacc.org/journal/jacc-clinical-electrophysiology",
        ],
        days_back,
    )
    text = _grounded_call(client, prompt, "JACC")
    items = _parse_pipe_format(text)
    for item in items:
        item["publicacao"] = "JACC Family"
        item["fonte_origem"] = "jacc"
    logger.info(f"Gemini JACC Family: {len(items)} items")
    return items


def fetch_esc_european(client, days_back: int = 2) -> list[dict]:
    """ESC family — EHJ, Eur J Heart Fail, EuroIntervention, etc."""
    prompt = _build_journal_prompt(
        "ESC European journals",
        [
            "academic.oup.com/eurheartj (European Heart Journal)",
            "onlinelibrary.wiley.com/journal/eurjhf (European Journal of Heart Failure)",
            "academic.oup.com/europace",
        ],
        days_back,
    )
    text = _grounded_call(client, prompt, "ESC-EUR")
    items = _parse_pipe_format(text)
    for item in items:
        item["publicacao"] = "ESC European Journals"
        item["fonte_origem"] = "esc_eur"
    logger.info(f"Gemini ESC European: {len(items)} items")
    return items


def fetch_general_medical(client, days_back: int = 2) -> list[dict]:
    """General medical journals with cardiology sections."""
    prompt = _build_journal_prompt(
        "General medical journals (cardio sections)",
        [
            "nejm.org (cardiology section)",
            "thelancet.com (cardiology articles)",
            "jamanetwork.com/journals/jamacardiology (JAMA Cardiology)",
            "bmj.com/specialties/cardiology",
            "heart.bmj.com (BMJ Heart)",
        ],
        days_back,
    )
    text = _grounded_call(client, prompt, "GEN-MED")
    items = _parse_pipe_format(text)
    for item in items:
        item["publicacao"] = "General Medical (NEJM/Lancet/JAMA/BMJ)"
        item["fonte_origem"] = "gen_med"
    logger.info(f"Gemini General Medical: {len(items)} items")
    return items


def fetch_medscape_cardio(client, days_back: int = 2) -> list[dict]:
    """Medscape cardiology news — paywalled, no RSS, only Gemini accesses."""
    brasilia_tz = timezone(timedelta(hours=-3))
    today = datetime.now(brasilia_tz).strftime("%Y-%m-%d")
    cutoff = (datetime.now(brasilia_tz) - timedelta(days=days_back)).strftime("%Y-%m-%d")

    prompt = f"""Use Google Search to find cardiology news articles published between {cutoff} and {today} on:
- medscape.com/cardiology
- medscape.com/heart-disease

For EACH cardiology article found in this date window, return ONE line:
TITLE: <exact title> | URL: <full URL> | DATE: <YYYY-MM-DD> | DOI: null

Rules:
- Maximum 10 items
- Only cardiology news/commentary articles (not patient-facing health tips)
- Only articles in the window {cutoff} to {today}
- DO NOT invent
- If nothing found: NONE

Plain text only."""

    text = _grounded_call(client, prompt, "Medscape")
    items = _parse_pipe_format(text)
    for item in items:
        item["publicacao"] = "Medscape Cardiology"
        item["fonte_origem"] = "medscape"
    logger.info(f"Gemini Medscape: {len(items)} items")
    return items


def fetch_society_news(client, days_back: int = 2) -> list[dict]:
    """ESC/ACC/AHA society press releases and news."""
    brasilia_tz = timezone(timedelta(hours=-3))
    today = datetime.now(brasilia_tz).strftime("%Y-%m-%d")
    cutoff = (datetime.now(brasilia_tz) - timedelta(days=days_back)).strftime("%Y-%m-%d")

    prompt = f"""Use Google Search to find cardiology press releases or news published between {cutoff} and {today} on:
- escardio.org/news
- escardio.org/The-ESC/Press-Office
- acc.org/latest-in-cardiology
- newsroom.heart.org (AHA press)
- portal.cardiol.br (SBC Brasil)

For EACH news/press release found, return ONE line:
TITLE: <exact title> | URL: <full URL> | DATE: <YYYY-MM-DD> | DOI: null

Rules:
- Maximum 10 items
- Cardiology focus
- In the date window {cutoff} to {today}
- DO NOT invent
- If nothing found: NONE

Plain text only."""

    text = _grounded_call(client, prompt, "Sociedades")
    items = _parse_pipe_format(text)
    for item in items:
        item["publicacao"] = "Sociedades (ESC/ACC/AHA/SBC)"
        item["fonte_origem"] = "sociedades"
    logger.info(f"Gemini Sociedades: {len(items)} items")
    return items


def fetch_bluesky_cardio(client, days_back: int = 2) -> list[dict]:
    """Bluesky cardio handles posts. Returns discussoes_bluesky-shaped items."""
    brasilia_tz = timezone(timedelta(hours=-3))
    today = datetime.now(brasilia_tz).strftime("%Y-%m-%d")
    cutoff = (datetime.now(brasilia_tz) - timedelta(days=days_back)).strftime("%Y-%m-%d")

    prompt = f"""Use Google Search to find cardiology-related posts published on Bluesky (bsky.app) between {cutoff} and {today} from these handles or about cardiology topics:

- @drjohnm.bsky.social (John Mandrola)
- @erictopol.bsky.social (Eric Topol)
- @cardionerds.bsky.social
- Other cardiology specialists with #cardiotwitter or cardio topics

For EACH relevant post found in this window, return ONE line:
TITLE: <topic of the post in 1 line> | URL: <bsky.app post URL> | DATE: <YYYY-MM-DD> | DOI: null

Rules:
- Maximum 10 items
- Only posts that discuss research, trials, guidelines, or clinical practice
- Only posts in the window {cutoff} to {today}
- DO NOT invent posts that don't exist
- If nothing found: NONE

Plain text only."""

    text = _grounded_call(client, prompt, "Bluesky")
    items = _parse_pipe_format(text)

    # Transform to discussoes_bluesky schema (similar to discussoes_x)
    discussoes = []
    for i, item in enumerate(items, 1):
        discussoes.append({
            "id": f"bsky_{i:03d}",
            "titulo": item["titulo"][:200],
            "autor": "@bluesky",  # could parse from URL but keep simple for v1
            "categoria": "especialista",
            "emoji": "🦋",
            "classe": "C",  # default — Sonnet/Opus can re-classify if desired
            "score": 5.0,
            "resumo": "Discussão cardio no Bluesky.",
            "impacto_clinico": "Acompanhar para contexto clínico.",
            "links": {
                "post_url": item["url"],
                "url": None,
                "doi": item.get("doi"),
                "pubmed": None,
            },
            "data_publicacao": item.get("data_publicacao_raw", ""),
        })
    logger.info(f"Gemini Bluesky: {len(discussoes)} items")
    return discussoes


# ──────────────────────────────────────────────────────────────────────
# ORCHESTRATOR
# ──────────────────────────────────────────────────────────────────────

def fetch_all_external(days_back: int = 2) -> dict:
    """Run all Gemini fetchers in parallel.

    Returns:
        {
            "noticias_external": [list of journal/news items for noticias[]],
            "discussoes_bluesky": [list of Bluesky discussions]
        }

    Returns empty arrays if GOOGLE_API_KEY not set or all fetchers fail.
    Pipeline continues normally on failure (graceful degrade).
    """
    client = _get_client()
    if not client:
        logger.warning("GOOGLE_API_KEY not set — Gemini external fetcher skipped")
        return {"noticias_external": [], "discussoes_bluesky": []}

    # Journal/news fetchers — run in parallel (4 workers respecting Flash 10 RPM)
    journal_fetchers = [
        ("aha", fetch_aha_journals),
        ("jacc", fetch_jacc_family),
        ("esc_eur", fetch_esc_european),
        ("gen_med", fetch_general_medical),
        ("medscape", fetch_medscape_cardio),
        ("sociedades", fetch_society_news),
    ]

    noticias_external = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(fn, client, days_back): name for name, fn in journal_fetchers}
        for future in as_completed(futures):
            name = futures[future]
            try:
                result = future.result(timeout=GEMINI_CALL_TIMEOUT)
                # Convert to noticias-compatible schema
                for item in result:
                    if not _matches_cardio(item.get("titulo", "")):
                        continue
                    noticias_external.append({
                        "pmid": None,
                        "titulo": item["titulo"],
                        "publicacao": item.get("publicacao", "External"),
                        "autores": [],
                        "data_publicacao": item.get("data_publicacao_raw", "recent"),
                        "abstract": "",  # Gemini fetcher doesn't pull abstracts
                        "doi": item.get("doi"),
                        "pubmed_url": item["url"],
                        "doi_url": f"https://doi.org/{item['doi']}" if item.get("doi") else None,
                        "categoria_fonte": "noticias",
                        "emoji": "🌐",
                        "_fonte_origem": item.get("fonte_origem"),
                    })
            except Exception as e:
                logger.error(f"External fetcher [{name}] failed: {e}")

    # Bluesky separately (single call, separate schema)
    bluesky = []
    try:
        bluesky = fetch_bluesky_cardio(client, days_back)
    except Exception as e:
        logger.error(f"Bluesky fetcher failed: {e}")

    logger.info(f"Gemini external TOTAL: {len(noticias_external)} noticias + {len(bluesky)} Bluesky")
    return {
        "noticias_external": noticias_external,
        "discussoes_bluesky": bluesky,
    }


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.INFO)

    result = fetch_all_external(days_back=2)
    print(f"\n{'='*60}")
    print(f"Noticias external: {len(result['noticias_external'])}")
    print(f"{'='*60}")
    for item in result["noticias_external"][:10]:
        print(f"  [{item['_fonte_origem']}] {item['publicacao']}")
        print(f"    {item['titulo'][:80]}")
        print(f"    {item['pubmed_url'][:80]}")
        print()

    print(f"\n{'='*60}")
    print(f"Bluesky: {len(result['discussoes_bluesky'])}")
    print(f"{'='*60}")
    for d in result["discussoes_bluesky"][:5]:
        print(f"  [{d['id']}] {d['titulo'][:80]}")
        print(f"    {d['links']['post_url']}")
        print()
