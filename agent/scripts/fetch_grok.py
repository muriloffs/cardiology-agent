"""Fetch cardiology highlights from X/Twitter via Grok API (real-time X access)."""

import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Any

logger = logging.getLogger(__name__)

GROK_API_URL = "https://api.x.ai/v1/chat/completions"
GROK_MODEL = "grok-3-mini"

_SYSTEM_PROMPT = """You are a cardiology research assistant. Your job is to search X/Twitter
for today's most clinically relevant cardiology posts and return them as structured JSON.

Focus on posts from the last 24 hours that have:
- Links to actual studies, guidelines, preprints, or official sources
- Discussion from recognized cardiologists or scientific institutions
- Real clinical implications (not just opinions or promotional content)

Key accounts to monitor: Eric Topol, Deepak Bhatt, John Mandrola, Erin Michos, Martha Gulati,
Roxana Mehran, Harlan Krumholz, Valentin Fuster, Carlos Rochitte, Silvio Barberato,
ACC, AHA, ESC, Heart Rhythm Society, TCTMD, JACC Journals, Circulation, EHJ, NEJM, JAMA Cardiology.

Topics: heart failure, atrial fibrillation, hypertension, coronary disease, GLP-1, SGLT2,
prevention, imaging, PCI, TAVR, structural heart, arrhythmia, cardio-oncology, cardiometabolic.

Hashtags: #CardioTwitter #MedTwitter #HeartFailure #AtrialFibrillation #Cardiology

EXCLUSION: Skip pure opinions without references, promotional posts, viral posts without science,
content outside the 24h window."""

_USER_PROMPT_TEMPLATE = """Search X/Twitter for the most relevant cardiology posts from {date} (last 24 hours).

Return a JSON array of up to 15 posts. Each item must follow this exact schema:

{{
  "titulo": "descriptive title of the topic (not the tweet text)",
  "publicacao": "X/@handle or institution that posted",
  "autores": ["@handle"],
  "data_publicacao": "{date}",
  "abstract": "2-3 sentence summary of what was posted and why it matters clinically",
  "post_url": "https://x.com/... (exact URL or null if not found)",
  "article_url": "URL to the actual study/guideline (null if not found)",
  "doi": "10.xxxx/... (null if not found)",
  "pubmed_id": "PMID number only (null if not found)"
}}

Rules:
- Never invent DOI, PubMed IDs, or URLs — use null if not found
- Only include posts with real clinical content
- Return ONLY the JSON array, no markdown, no preamble

Start with ["""


def fetch_x_cardiology_posts(days_back: int = 1) -> list[dict[str, Any]]:
    """
    Query Grok for cardiology X/Twitter posts from the last N days.

    Returns articles in the same format as fetch_articles.py so they can
    be merged directly into the agent's article list.
    """
    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        logger.warning("XAI_API_KEY not set — skipping Grok/X fetch")
        return []

    brasilia_tz = timezone(timedelta(hours=-3))
    target_date = (datetime.now(brasilia_tz) - timedelta(days=days_back - 1)).strftime("%Y-%m-%d")

    try:
        import requests as req
        response = req.post(
            GROK_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROK_MODEL,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": _USER_PROMPT_TEMPLATE.format(date=target_date)},
                ],
                "temperature": 0.1,
                "max_tokens": 4000,
            },
            timeout=60,
        )
        response.raise_for_status()
        raw = response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Grok API call failed: {e}")
        return []

    return _parse_grok_response(raw, target_date)


def _parse_grok_response(raw: str, date: str) -> list[dict[str, Any]]:
    """Parse Grok's JSON response into the standard article format."""
    # Strip any markdown fences if Grok added them
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    if not text.startswith("["):
        idx = text.find("[")
        if idx == -1:
            logger.warning("Grok response did not contain a JSON array")
            return []
        text = text[idx:]

    try:
        posts = json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Grok JSON response: {e}")
        logger.debug(f"Raw response: {raw[:500]}")
        return []

    articles = []
    for post in posts:
        if not isinstance(post, dict):
            continue

        titulo = post.get("titulo", "").strip()
        if not titulo:
            continue

        # Build links dict — prefer article_url over post_url for the primary URL
        primary_url = post.get("article_url") or post.get("post_url")
        doi = post.get("doi") if post.get("doi") and post.get("doi") != "null" else None
        pubmed_id = post.get("pubmed_id") if post.get("pubmed_id") and post.get("pubmed_id") != "null" else None

        articles.append({
            "titulo": titulo,
            "publicacao": post.get("publicacao", "X/Twitter"),
            "autores": post.get("autores", []),
            "data_publicacao": post.get("data_publicacao", date),
            "abstract": post.get("abstract", ""),
            "pubmed_url": primary_url or "",
            "doi": doi,
            "doi_url": f"https://doi.org/{doi}" if doi else None,
            "pmid": pubmed_id,
            # Extra fields for context
            "_post_url": post.get("post_url"),
            "_article_url": post.get("article_url"),
        })

    logger.info(f"Grok/X: {len(articles)} posts parsed")
    return articles
