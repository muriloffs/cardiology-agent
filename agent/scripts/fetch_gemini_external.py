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

GEMINI_MODEL = "gemini-2.5-pro"
GEMINI_CALL_TIMEOUT = 120  # Pro is 2-3x slower than Flash; grounded calls ~60s

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


def _grounded_call(client, prompt: str, label: str = "gemini", _is_retry: bool = False) -> str:
    """Make 1 grounded Gemini Flash call. Retries once on empty text.

    Empty-text is a known Flash+grounding pathology — model returns no text
    even with grounding succeeded. Retry with bumped temp + small prompt nudge
    typically unsticks it. Same pattern used in fetch_gemini_substacks.py.
    """
    try:
        from google.genai import types
        config = types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.4 if _is_retry else 0.0,
        )
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=config,
        )
        text = _extract_text(response)
        if not text and not _is_retry:
            logger.info(f"[{label}] Empty response — retrying once with temp=0.4")
            retry_prompt = prompt + "\n\nProceed and respond with the requested format now."
            return _grounded_call(client, retry_prompt, label, _is_retry=True)
        if not text:
            logger.warning(f"[{label}] Gemini returned empty text (after retry)")
        elif _is_retry:
            logger.info(f"[{label}] Retry succeeded")
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

def _build_journal_prompt(target_label: str, target_url: str, max_items: int = 5) -> str:
    """Simple grounded prompt — proven pattern from TEST 2B.

    Key principles (validated empirically):
    - Single target (or very similar sites) — Flash struggles with multi-site
    - "Most recent" instead of strict date window — Flash rejects strict dates
    - Plain text format — Flash can't do JSON + grounding combined
    - Short, no rule lists — long prompts trigger empty responses
    """
    return f"""Use Google Search to find the {max_items} most recent cardiology articles published this week on {target_label} ({target_url}).

For each article, respond with ONE line:
TITLE: <article title> | URL: <full URL> | DATE: <publication date> | DOI: <DOI or null>

Plain text only. No JSON. No markdown. If you cannot find any: NONE"""


# ──────────────────────────────────────────────────────────────────────
# JOURNAL FETCHERS — one focused fetcher per major journal/group
# Pattern: 1 target site, "most recent", simple format. Validated.
# ──────────────────────────────────────────────────────────────────────

def fetch_circulation(client) -> list[dict]:
    """Circulation (AHA Journals)."""
    prompt = _build_journal_prompt(
        "Circulation journal", "ahajournals.org/journal/circ", max_items=5
    )
    text = _grounded_call(client, prompt, "Circulation")
    items = _parse_pipe_format(text)
    for item in items:
        item["publicacao"] = "Circulation"
        item["fonte_origem"] = "circulation"
    logger.info(f"Gemini Circulation: {len(items)} items")
    return items


def fetch_aha_secondary(client) -> list[dict]:
    """JAHA + Hypertension + Stroke (AHA secondary journals, similar style)."""
    prompt = _build_journal_prompt(
        "JAHA, Hypertension, Stroke (AHA Journals secondary)",
        "ahajournals.org",
        max_items=5,
    )
    text = _grounded_call(client, prompt, "AHA-2nd")
    items = _parse_pipe_format(text)
    for item in items:
        item["publicacao"] = "JAHA / Hypertension / Stroke"
        item["fonte_origem"] = "aha_secondary"
    logger.info(f"Gemini AHA Secondary: {len(items)} items")
    return items


def fetch_jacc_main(client) -> list[dict]:
    """JACC main journal."""
    prompt = _build_journal_prompt(
        "JACC main journal", "jacc.org", max_items=5
    )
    text = _grounded_call(client, prompt, "JACC-main")
    items = _parse_pipe_format(text)
    for item in items:
        item["publicacao"] = "JACC"
        item["fonte_origem"] = "jacc_main"
    logger.info(f"Gemini JACC main: {len(items)} items")
    return items


def fetch_jacc_subs(client) -> list[dict]:
    """JACC sub-journals (Heart Failure, Interventions, Imaging)."""
    prompt = _build_journal_prompt(
        "JACC sub-journals (Heart Failure, Interventions, Imaging, Clinical Electrophysiology)",
        "jacc.org",
        max_items=5,
    )
    text = _grounded_call(client, prompt, "JACC-subs")
    items = _parse_pipe_format(text)
    for item in items:
        item["publicacao"] = "JACC Subjournals"
        item["fonte_origem"] = "jacc_subs"
    logger.info(f"Gemini JACC subs: {len(items)} items")
    return items


def fetch_ehj(client) -> list[dict]:
    """European Heart Journal."""
    prompt = _build_journal_prompt(
        "European Heart Journal", "academic.oup.com/eurheartj", max_items=5
    )
    text = _grounded_call(client, prompt, "EHJ")
    items = _parse_pipe_format(text)
    for item in items:
        item["publicacao"] = "European Heart Journal"
        item["fonte_origem"] = "ehj"
    logger.info(f"Gemini EHJ: {len(items)} items")
    return items


def fetch_ejhf(client) -> list[dict]:
    """European Journal of Heart Failure."""
    prompt = _build_journal_prompt(
        "European Journal of Heart Failure", "onlinelibrary.wiley.com/journal/eurjhf", max_items=5
    )
    text = _grounded_call(client, prompt, "EJHF")
    items = _parse_pipe_format(text)
    for item in items:
        item["publicacao"] = "European Journal of Heart Failure"
        item["fonte_origem"] = "ejhf"
    logger.info(f"Gemini EJHF: {len(items)} items")
    return items


def fetch_jama_cardio(client) -> list[dict]:
    """JAMA Cardiology."""
    prompt = _build_journal_prompt(
        "JAMA Cardiology", "jamanetwork.com/journals/jamacardiology", max_items=5
    )
    text = _grounded_call(client, prompt, "JAMA-Cardio")
    items = _parse_pipe_format(text)
    for item in items:
        item["publicacao"] = "JAMA Cardiology"
        item["fonte_origem"] = "jama_cardio"
    logger.info(f"Gemini JAMA Cardio: {len(items)} items")
    return items


def fetch_lancet_bmj(client) -> list[dict]:
    """Lancet cardio + BMJ Heart (similar UK journals)."""
    prompt = _build_journal_prompt(
        "Lancet cardiology + BMJ Heart", "thelancet.com OR heart.bmj.com", max_items=5
    )
    text = _grounded_call(client, prompt, "Lancet-BMJ")
    items = _parse_pipe_format(text)
    for item in items:
        item["publicacao"] = "Lancet / BMJ Heart"
        item["fonte_origem"] = "lancet_bmj"
    logger.info(f"Gemini Lancet/BMJ: {len(items)} items")
    return items


def fetch_medscape_cardio(client) -> list[dict]:
    """Medscape cardiology — paywalled, only Gemini accesses."""
    prompt = """Use Google Search to find the 5 most recent cardiology news articles published this week on Medscape (medscape.com/cardiology or medscape.com/heart-disease).

For each article, respond with ONE line:
TITLE: <article title> | URL: <full URL> | DATE: <publication date> | DOI: null

Plain text only. No JSON. No markdown. If you cannot find any: NONE"""
    text = _grounded_call(client, prompt, "Medscape")
    items = _parse_pipe_format(text)
    for item in items:
        item["publicacao"] = "Medscape Cardiology"
        item["fonte_origem"] = "medscape"
    logger.info(f"Gemini Medscape: {len(items)} items")
    return items


def fetch_society_intl(client) -> list[dict]:
    """ESC + ACC + AHA international society news."""
    prompt = """Use Google Search to find the 5 most recent cardiology press releases or news from cardiology societies this week (escardio.org/news, acc.org/latest-in-cardiology, newsroom.heart.org).

For each, respond with ONE line:
TITLE: <title> | URL: <full URL> | DATE: <publication date> | DOI: null

Plain text only. No JSON. No markdown. If none found: NONE"""
    text = _grounded_call(client, prompt, "Sociedades-Intl")
    items = _parse_pipe_format(text)
    for item in items:
        item["publicacao"] = "Sociedades Internacionais (ESC/ACC/AHA)"
        item["fonte_origem"] = "sociedades_intl"
    logger.info(f"Gemini Sociedades Intl: {len(items)} items")
    return items


def fetch_sbc_brasil(client) -> list[dict]:
    """Sociedade Brasileira de Cardiologia."""
    prompt = """Use Google Search to find the 5 most recent cardiology news or articles published this week on Sociedade Brasileira de Cardiologia (portal.cardiol.br) or Brazilian cardiology journals (Arquivos Brasileiros de Cardiologia on scielo.br).

For each, respond with ONE line:
TITLE: <título do artigo> | URL: <URL completo> | DATE: <data> | DOI: <DOI ou null>

Plain text only. No JSON. No markdown. If none found: NONE"""
    text = _grounded_call(client, prompt, "SBC-Brasil")
    items = _parse_pipe_format(text)
    for item in items:
        item["publicacao"] = "SBC Brasil / SciELO"
        item["fonte_origem"] = "sbc_brasil"
    logger.info(f"Gemini SBC Brasil: {len(items)} items")
    return items


def fetch_bluesky_cardio(client) -> list[dict]:
    """Bluesky cardio handles posts. Returns discussoes_bluesky-shaped items."""
    prompt = """Use Google Search to find the 5 most recent cardiology-related posts on Bluesky (bsky.app) this week from cardiology specialists like John Mandrola, Eric Topol, CardioNerds, or any cardiology topic discussion.

For each post, respond with ONE line:
TITLE: <topic in 1 line> | URL: <bsky.app post URL> | DATE: <publication date> | DOI: null

Plain text only. No JSON. No markdown. If none found: NONE"""

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

    # Journal/news fetchers — 11 focused single/dual-site queries
    # Pattern: each query targets 1-2 closely related sites (validated in TEST 2B)
    # Parallel: 3 workers (respects Flash 10 RPM with safety margin)
    journal_fetchers = [
        ("circulation",     fetch_circulation),
        ("aha_secondary",   fetch_aha_secondary),
        ("jacc_main",       fetch_jacc_main),
        ("jacc_subs",       fetch_jacc_subs),
        ("ehj",             fetch_ehj),
        ("ejhf",            fetch_ejhf),
        ("jama_cardio",     fetch_jama_cardio),
        ("lancet_bmj",      fetch_lancet_bmj),
        ("medscape",        fetch_medscape_cardio),
        ("sociedades_intl", fetch_society_intl),
        ("sbc_brasil",      fetch_sbc_brasil),
    ]

    noticias_external = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(fn, client): name for name, fn in journal_fetchers}
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
        bluesky = fetch_bluesky_cardio(client)
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
