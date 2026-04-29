"""Fetch cardiology highlights from X/Twitter via Grok API (real-time X access)."""

import json
import logging
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

GROK_API_URL = "https://api.x.ai/v1/chat/completions"
GROK_MODEL = "grok-3-mini"


def _load_prompt(date: str) -> str:
    prompt_path = Path(__file__).parent.parent / "prompts" / "grok_x_prompt.txt"
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read().replace("{date}", date)


def fetch_x_cardiology_posts(days_back: int = 1) -> list[dict[str, Any]]:
    """
    Query Grok for cardiology X/Twitter posts using the full curated prompt.

    Returns articles in the same format as fetch_articles.py so they can
    be merged directly into the agent's article list.
    Gracefully returns [] if XAI_API_KEY is not set.
    """
    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        logger.warning("XAI_API_KEY not set — skipping Grok/X fetch")
        return []

    brasilia_tz = timezone(timedelta(hours=-3))
    target_date = (datetime.now(brasilia_tz) - timedelta(days=days_back - 1)).strftime("%Y-%m-%d")

    try:
        prompt = _load_prompt(target_date)
    except FileNotFoundError:
        logger.error("grok_x_prompt.txt not found in agent/prompts/")
        return []

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
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
                "max_tokens": 6000,
            },
            timeout=90,
        )
        response.raise_for_status()
        raw = response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Grok API call failed: {e}")
        return []

    return _parse_grok_response(raw, target_date)


def _parse_grok_response(raw: str, date: str) -> list[dict[str, Any]]:
    """Parse Grok's JSON response into the standard article format."""
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
        logger.debug(f"Raw response snippet: {raw[:500]}")
        return []

    articles = []
    for post in posts:
        if not isinstance(post, dict):
            continue
        titulo = post.get("titulo", "").strip()
        if not titulo:
            continue

        doi = post.get("doi") if post.get("doi") not in (None, "null", "") else None
        pubmed_id = post.get("pubmed_id") if post.get("pubmed_id") not in (None, "null", "") else None
        article_url = post.get("article_url") if post.get("article_url") not in (None, "null", "") else None
        post_url = post.get("post_url") if post.get("post_url") not in (None, "null", "") else None

        # Build abstract with extra context fields for Claude to use
        resumo = post.get("resumo", "")
        impacto = post.get("impacto_clinico", "")
        brasil = post.get("aplicabilidade_brasil", "")
        classe = post.get("classe_sugerida", "")

        abstract_parts = [resumo]
        if impacto:
            abstract_parts.append(f"Impacto clínico: {impacto}")
        if brasil:
            abstract_parts.append(f"Brasil: {brasil}")
        if classe:
            abstract_parts.append(f"[Classe sugerida pelo Grok: {classe}]")

        articles.append({
            "titulo": titulo,
            "publicacao": post.get("publicacao", "X/Twitter"),
            "autores": post.get("autores", []),
            "data_publicacao": date,
            "abstract": " | ".join(abstract_parts),
            "pubmed_url": article_url or post_url or "",
            "doi": doi,
            "doi_url": f"https://doi.org/{doi}" if doi else None,
            "pmid": pubmed_id,
            "_post_url": post_url,
            "_article_url": article_url,
        })

    logger.info(f"Grok/X: {len(articles)} posts parsed")
    return articles
