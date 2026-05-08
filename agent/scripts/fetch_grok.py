"""Fetch cardiology highlights from X/Twitter via Grok API (real-time X search)."""

import json
import logging
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

GROK_API_URL = "https://api.x.ai/v1/responses"
GROK_MODEL = os.environ.get("GROK_MODEL", "grok-4")
GROK_MAX_ATTEMPTS = 3          # 2 retries on connection drops / 5xx / timeouts
GROK_RETRY_BACKOFF_SECONDS = 60  # 1min between attempts (covers most capacity windows)


def _load_prompt(date: str) -> str:
    prompt_path = Path(__file__).parent.parent / "prompts" / "grok_x_prompt.txt"
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read().replace("{date}", date)


def fetch_x_cardiology_posts(days_back: int = 1) -> list[dict[str, Any]]:
    """
    Query Grok for cardiology X/Twitter posts using Responses API (Agent Tools) with x_search tool.

    Uses real-time X search (grok-4 + x_search) to return verifiable post URLs.
    Gracefully returns [] if XAI_API_KEY is not set.
    """
    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        logger.warning("XAI_API_KEY not set — skipping Grok/X fetch")
        return []

    brasilia_tz = timezone(timedelta(hours=-3))
    target_date = (datetime.now(brasilia_tz) - timedelta(days=days_back)).strftime("%Y-%m-%d")

    try:
        prompt = _load_prompt(target_date)
    except FileNotFoundError:
        logger.error("grok_x_prompt.txt not found in agent/prompts/")
        return []

    import requests as req

    request_payload = {
        "model": GROK_MODEL,
        "input": [{"role": "user", "content": prompt}],
        "tools": [{"type": "x_search"}],
        "temperature": 0.1,
        "max_output_tokens": 14000,         # headroom for 25+ posts
        "max_tool_calls": 4,                # conservative — model can do up to 4 x_search invocations
        "parallel_tool_calls": True,        # allow concurrent searches (lower latency)
    }
    request_headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Retry loop: xAI server occasionally drops connections OR returns 5xx during high load.
    # Both are transient — second attempt typically succeeds.
    response = None
    data = None
    last_error = None
    actual_attempts = 0
    for attempt in range(1, GROK_MAX_ATTEMPTS + 1):
        actual_attempts = attempt
        try:
            logger.info(f"Calling Grok API (attempt {attempt}/{GROK_MAX_ATTEMPTS}): model={GROK_MODEL}, url={GROK_API_URL}, date={target_date}")
            response = req.post(
                GROK_API_URL,
                headers=request_headers,
                json=request_payload,
                timeout=360,                # 6min per attempt
            )
            response.raise_for_status()
            data = response.json()
            break  # success — exit retry loop
        except (req.exceptions.ConnectionError, req.exceptions.Timeout) as e:
            last_error = e
            logger.warning(f"Grok attempt {attempt} failed (transient: {type(e).__name__}): {e}")
            if attempt < GROK_MAX_ATTEMPTS:
                logger.info(f"Retrying Grok in {GROK_RETRY_BACKOFF_SECONDS}s...")
                time.sleep(GROK_RETRY_BACKOFF_SECONDS)
        except req.exceptions.HTTPError as e:
            last_error = e
            status_code = e.response.status_code if e.response is not None else 0
            logger.error(f"Grok HTTP error {status_code} (attempt {attempt}): {e}")
            try:
                logger.error(f"Grok response body: {response.text[:500]}")
            except Exception:
                pass
            # Retry on 5xx (server-side, transient: capacity, deploy, etc.)
            # Do NOT retry on 4xx (client-side, persistent: bad params, auth)
            if 500 <= status_code < 600 and attempt < GROK_MAX_ATTEMPTS:
                logger.info(f"5xx is transient — retrying Grok in {GROK_RETRY_BACKOFF_SECONDS}s...")
                time.sleep(GROK_RETRY_BACKOFF_SECONDS)
            else:
                break  # 4xx or final attempt — give up

    if data is None:
        logger.error(f"Grok API call failed after {actual_attempts} attempt(s): {last_error}")
        return []

    try:
        logger.info(f"Grok API response keys: {list(data.keys())}")

        # === DIAGNOSTIC LOGGING ===
        # 1. Error/status fields populated only when API rejects something silently
        for diag_key in ("status", "error", "incomplete_details"):
            val = data.get(diag_key)
            if val:
                logger.warning(f"Grok response.{diag_key}: {json.dumps(val)[:500]}")

        # 2. Echo of accepted params (confirms server didn't drop them)
        echoed_max_tools = data.get("max_tool_calls")
        echoed_parallel = data.get("parallel_tool_calls")
        logger.info(f"Grok server-echoed params: max_tool_calls={echoed_max_tools}, parallel_tool_calls={echoed_parallel}")

        # 3. Usage tells us if real work happened (zero usage = rejected)
        usage = data.get("usage", {})
        if usage:
            logger.info(f"Grok usage: {json.dumps(usage)[:300]}")

        # 4. Count actual tool invocations from output array
        tool_calls_count = sum(
            1 for item in data.get("output", []) if item.get("type") in ("server_tool_call", "tool_use", "function_call")
        )
        logger.info(f"Grok actual tool calls observed in output: {tool_calls_count}")

        # Responses API: extract text from output[].content[].text
        raw = ""
        for item in data.get("output", []):
            if item.get("type") == "message":
                for block in item.get("content", []):
                    if block.get("type") == "output_text":
                        raw = block.get("text", "") or ""
                        break
            if raw:
                break

        # 5. Preview do output (visualização manual do que Grok produziu)
        if raw:
            logger.info(f"Grok output preview (first 400 chars): {raw[:400]}")

        if not raw:
            logger.warning("No text output in Grok Responses API response")
            logger.warning(f"Raw response (first 1000 chars): {json.dumps(data)[:1000]}")
            return []

    except Exception as e:
        logger.error(f"Grok response processing failed: {e}")
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

        resumo = post.get("resumo", "")
        impacto = post.get("impacto_clinico", "")
        classe = post.get("classe_sugerida", "")

        abstract_parts = [resumo]
        if impacto:
            abstract_parts.append(f"Impacto clínico: {impacto}")
        if classe:
            abstract_parts.append(f"[Classe sugerida pelo Grok: {classe}]")

        # Author handling: support both new schema (autor: string) and legacy (autores: list)
        autores = post.get("autores")
        if not autores:
            autor = post.get("autor", "").strip()
            autores = [autor] if autor else []

        # Publicacao defaults to first handle if not provided
        publicacao = post.get("publicacao") or (autores[0] if autores else "X/Twitter")

        # Normalize classe_sugerida
        norm_classe = (classe or "").strip().upper()
        if norm_classe not in ("A", "B", "C"):
            norm_classe = "C"  # default to C if missing/invalid

        articles.append({
            "titulo": titulo,
            "publicacao": publicacao,
            "autores": autores,
            "data_publicacao": date,
            "abstract": " | ".join(abstract_parts),
            "pubmed_url": post_url or article_url or "",
            "doi": doi,
            "doi_url": f"https://doi.org/{doi}" if doi else None,
            "pmid": pubmed_id,
            "_post_url": post_url,
            "_article_url": article_url,
            # Raw Grok fields preserved for direct-bypass transformation
            "_grok_classe": norm_classe,
            "_grok_resumo": resumo.strip() if resumo else "",
            "_grok_impacto": impacto.strip() if impacto else "",
        })

    logger.info(f"Grok/X: {len(articles)} posts parsed")
    return articles


# ============================================================
# Direct-bypass transformation: Grok output → discussoes_x schema
# Used when we want to skip Claude curation and inject Grok's posts
# directly into the final report.
# ============================================================

# Map @handle → categoria. Lowercased for case-insensitive lookup.
HANDLE_CATEGORIES = {
    # Specialists / individual physicians
    **{h.lower(): "especialista" for h in [
        "@EricTopol", "@deepakbhatt1", "@drjohnm", "@ErinMichos",
        "@MarthaGulati", "@RoxanaMehran", "@hmkyale", "@FusterV",
        "@CarlosRochitte", "@SilvioBarberato", "@sciqst",
        "@CritCareReviews", "@CardiologyToday",
    ]},
    # Journals / publications
    **{h.lower(): "revista" for h in [
        "@NEJM", "@TheLancet", "@JACCJournals", "@CircAHA",
        "@JAMACardio", "@EuroHeartJ", "@bmj_latest", "@JACCCRJournals",
    ]},
    # Medical societies
    **{h.lower(): "sociedade" for h in [
        "@ACCinTouch", "@American_Heart", "@escardio", "@HRSonline",
        "@TCTMD", "@cardiol_br", "@SOCESP",
    ]},
}

CLASSE_TO_SCORE = {"A": 9.0, "B": 7.0, "C": 5.0}


def transform_to_discussoes_x(grok_articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Convert Grok's raw articles into discussoes_x schema items for direct injection
    into the final report (bypassing Claude curation).

    Schema produced (matches what Claude would output for discussoes_x):
        {id, titulo, autor, categoria, emoji, classe, score, resumo, impacto_clinico, links{}}
    """
    result = []
    for i, post in enumerate(grok_articles, 1):
        autor_list = post.get("autores") or []
        autor = autor_list[0] if autor_list else "@unknown"
        # Normalize handle: ensure @ prefix
        if autor and not autor.startswith("@"):
            autor = "@" + autor

        # Categoria: lookup or default to "especialista"
        categoria = HANDLE_CATEGORIES.get(autor.lower(), "especialista")

        classe = post.get("_grok_classe", "C") or "C"
        score = CLASSE_TO_SCORE.get(classe, 5.0)

        resumo = post.get("_grok_resumo") or "Discussão clínica relevante no X."
        impacto = post.get("_grok_impacto") or "Atualização para acompanhamento."

        result.append({
            "id": f"x_{i:03d}",
            "titulo": post.get("titulo", ""),
            "autor": autor,
            "categoria": categoria,
            "emoji": "🫀",
            "classe": classe,
            "score": score,
            "resumo": resumo,
            "impacto_clinico": impacto,
            "links": {
                "post_url": post.get("_post_url"),
                "url": post.get("_article_url"),
                "doi": post.get("doi"),
                "pubmed": post.get("pmid"),
            },
        })
    logger.info(f"transform_to_discussoes_x: {len(result)} items ready for direct injection")
    return result
