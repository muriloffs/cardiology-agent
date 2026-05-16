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
GROK_MODEL_PRIMARY = os.environ.get("GROK_MODEL", "grok-4")
# NOTE: grok-3 is NOT supported with server-side tools (x_search). Discovered
# via production logs: 400 "the model grok-3 is not supported when using
# server-side tools, only the grok-4 family of models are supported".
# Removed model-swap fallback. Resilience now relies on:
#   - Level 1: 3 retries with exponential backoff (60/120/240s)
#   - Level 3: cache fallback to yesterday's discussoes_x
# (Level 2 model swap removed until xAI exposes a tool-compatible alternative.)
# Separate retry budgets:
#   ERROR_RETRIES: ConnectionError, Timeout, 5xx — boosted from 1→3 with exponential backoff
#   LOWCOUNT_RETRIES: valid response but < TRIGGER posts (Grok was lazy)
GROK_MAX_ERROR_RETRIES = 3       # 3 retries on infrastructure errors (was 1)
GROK_MAX_LOWCOUNT_RETRIES = 1    # 1 retry on low-count with aggressive feedback
GROK_MAX_TOTAL_ATTEMPTS = 5      # hard cap (1 initial + up to 4 retries of either type) (was 3)
# Exponential backoff schedule (in seconds): 60, 120, 240
# After error attempt N (1-indexed), wait GROK_BACKOFF_SCHEDULE[N-1] before next retry
GROK_BACKOFF_SCHEDULE = [60, 120, 240]
# Target system (calibrated for reduced-complexity request):
GROK_MIN_POSTS_TRIGGER = int(os.environ.get("GROK_MIN_POSTS", "12"))   # was 20 — adjusted for lower max_tool_calls
GROK_TARGET_POSTS = int(os.environ.get("GROK_TARGET_POSTS", "25"))     # was 40 — realistic with 2 tool calls


def _get_backoff_seconds(retry_number: int) -> int:
    """Exponential backoff schedule: 60s, 120s, 240s. Caps at 240."""
    if retry_number <= 0:
        return 60
    idx = min(retry_number - 1, len(GROK_BACKOFF_SCHEDULE) - 1)
    return GROK_BACKOFF_SCHEDULE[idx]


def _load_cached_discussoes_x() -> list[dict[str, Any]]:
    """Final fallback: load yesterday's discussoes_x from the most recent committed report.

    Items are tagged with `_cache_fallback: True` so frontend can show staleness warning.
    Returns empty list if no cache available.
    """
    try:
        data_dir = Path(__file__).parent.parent.parent / "data"
        if not data_dir.exists():
            return []
        report_files = sorted(data_dir.glob("relatorio-*.json"), reverse=True)
        if not report_files:
            return []
        with open(report_files[0], "r", encoding="utf-8") as f:
            cached_report = json.load(f)
        cached_discussoes = cached_report.get("discussoes_x", [])
        if not cached_discussoes:
            return []
        # Mark each item as cache-fallback for frontend awareness
        for item in cached_discussoes:
            item["_cache_fallback"] = True
            item["_cache_source_date"] = cached_report.get("relatorio_data", "anterior")
        logger.warning(
            f"Grok unavailable — fallback to cached discussoes_x from "
            f"{cached_report.get('relatorio_data', 'anterior')} "
            f"({len(cached_discussoes)} items marked _cache_fallback)"
        )
        return cached_discussoes
    except Exception as e:
        logger.error(f"Failed to load cached discussoes_x: {e}")
        return []


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

    request_headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    def _build_payload(model: str, retry_feedback: str = "") -> dict:
        """Build Grok request payload, optionally with retry feedback appended.

        x_search tool config tunings (2026-05-14, baseado em docs.x.ai/developers/tools/x-search):
        - from_date: limita a janela de busca para 4 dias atrás (target_date - 3 days).
          Ajustado de 2d→3d em 2026-05-16 após observar quedas consistentes para 8-10 posts
          (vs 30-46 históricos). A janela de 3 dias era apertada demais para fins de semana
          quietos no X cardio. 4 dias dá mais espaço sem comprometer relevância.
        - enable_image_understanding: permite Grok ler gráficos/figuras de papers que
          cardiologistas postam em screenshots no X. Custo marginal por imagem lida.
        max_tool_calls 2→8: gargalo identificado nos primeiros runs com grok-4.3 (rendia
        ~10 posts em vez dos 30-46 históricos). Com 8 calls internas o Grok faz mais
        passes de busca cobrindo handles diferentes. Trade-off: +$0.10/run, +30s.
        """
        content = prompt + retry_feedback if retry_feedback else prompt
        # from_date = target_date - 3 dias, em formato ISO (YYYY-MM-DD)
        # Janela de 4 dias: cobre fim de semana sem perder foco temporal.
        from_date_dt = datetime.strptime(target_date, "%Y-%m-%d") - timedelta(days=3)
        from_date = from_date_dt.strftime("%Y-%m-%d")
        return {
            "model": model,
            "input": [{"role": "user", "content": content}],
            "tools": [{
                "type": "x_search",
                "from_date": from_date,
                "enable_image_understanding": True,
            }],
            "temperature": 0.1,
            "max_output_tokens": 8000,
            "max_tool_calls": 8,
            "parallel_tool_calls": True,
        }

    # SEPARATE retry budgets:
    #   ERROR_RETRIES (3):   ConnectionError/Timeout/5xx with exponential backoff
    #   LOWCOUNT_RETRIES (1): valid response but < TRIGGER posts
    # If all retries fail, _load_cached_discussoes_x() provides yesterday's data.
    best_articles: list[dict[str, Any]] = []
    previous_count: int | None = None
    last_error = None
    error_retries_remaining = GROK_MAX_ERROR_RETRIES
    lowcount_retries_remaining = GROK_MAX_LOWCOUNT_RETRIES
    error_retry_count = 0  # for exponential backoff tracking
    current_model = GROK_MODEL_PRIMARY
    attempt = 0

    while attempt < GROK_MAX_TOTAL_ATTEMPTS:
        attempt += 1
        response = None
        data = None

        # Build payload — inject aggressive feedback if last attempt was low-count
        retry_feedback = ""
        if attempt > 1 and previous_count is not None and previous_count < GROK_MIN_POSTS_TRIGGER:
            retry_feedback = (
                f"\n\n---\n"
                f"⚠️ **RETRY ATTEMPT** — Sua tentativa anterior retornou apenas **{previous_count} posts**. "
                f"Isso está abaixo do alvo. Há claramente conteúdo cardiológico relevante no X "
                f"que você não capturou ou rejeitou em excesso.\n\n"
                f"NESTE RETRY:\n"
                f"- Use suas tool calls disponíveis (até 2) com queries DIFERENTES da tentativa anterior\n"
                f"- Aceite posts marginais que rejeitou antes (qualidade média também conta)\n"
                f"- Busque em handles individuais variados (não só institucionais)\n"
                f"- **ALVO MÍNIMO: {GROK_TARGET_POSTS} posts.** Não pare antes."
            )
            logger.info(f"Building retry payload with aggressive feedback (previous attempt: {previous_count} posts)")

        request_payload = _build_payload(current_model, retry_feedback)

        try:
            logger.info(
                f"Calling Grok API (attempt {attempt}/{GROK_MAX_TOTAL_ATTEMPTS}; "
                f"err_retries={error_retries_remaining}, low_retries={lowcount_retries_remaining}): "
                f"model={current_model}, url={GROK_API_URL}, date={target_date}"
            )
            response = req.post(
                GROK_API_URL,
                headers=request_headers,
                json=request_payload,
                timeout=360,
            )
            response.raise_for_status()
            data = response.json()
        except (req.exceptions.ConnectionError, req.exceptions.Timeout) as e:
            last_error = e
            logger.warning(f"Grok attempt {attempt} failed (transient: {type(e).__name__}): {e}")
            if error_retries_remaining > 0:
                error_retries_remaining -= 1
                error_retry_count += 1
                backoff = _get_backoff_seconds(error_retry_count)
                logger.info(f"Consuming error retry. Backoff {backoff}s (exp: 60→120→240). Retrying...")
                time.sleep(backoff)
                continue
            else:
                logger.warning("No error retries remaining. Giving up on errors.")
                break
        except req.exceptions.HTTPError as e:
            last_error = e
            status_code = e.response.status_code if e.response is not None else 0
            response_body = ""
            try:
                response_body = response.text[:500]
            except Exception:
                pass
            logger.error(f"Grok HTTP error {status_code} (attempt {attempt}, model={current_model}): {e}")
            if response_body:
                logger.error(f"Grok response body: {response_body}")

            # 4xx → don't retry (persistent, our fault)
            if status_code < 500:
                break

            # 5xx → retry if error budget remains
            if error_retries_remaining > 0:
                error_retries_remaining -= 1
                error_retry_count += 1
                backoff = _get_backoff_seconds(error_retry_count)
                logger.info(f"5xx transient. Consuming error retry. Backoff {backoff}s. Retrying...")
                time.sleep(backoff)
                continue
            else:
                logger.warning("No error retries remaining for 5xx. Giving up.")
                break

        # Got valid data — process and check quality
        try:
            logger.info(f"Grok API response keys: {list(data.keys())}")

            # === DIAGNOSTIC LOGGING ===
            for diag_key in ("status", "error", "incomplete_details"):
                val = data.get(diag_key)
                if val:
                    logger.warning(f"Grok response.{diag_key}: {json.dumps(val)[:500]}")

            echoed_max_tools = data.get("max_tool_calls")
            echoed_parallel = data.get("parallel_tool_calls")
            logger.info(f"Grok server-echoed params: max_tool_calls={echoed_max_tools}, parallel_tool_calls={echoed_parallel}")

            usage = data.get("usage", {})
            if usage:
                logger.info(f"Grok usage: {json.dumps(usage)[:300]}")

            tool_calls_count = sum(
                1 for item in data.get("output", []) if item.get("type") in ("server_tool_call", "tool_use", "function_call")
            )
            logger.info(f"Grok actual tool calls observed in output: {tool_calls_count}")

            # Extract text
            raw = ""
            for item in data.get("output", []):
                if item.get("type") == "message":
                    for block in item.get("content", []):
                        if block.get("type") == "output_text":
                            raw = block.get("text", "") or ""
                            break
                if raw:
                    break

            if raw:
                logger.info(f"Grok output preview (first 400 chars): {raw[:400]}")
            else:
                logger.warning("No text output in Grok Responses API response")
                logger.warning(f"Raw response (first 1000 chars): {json.dumps(data)[:1000]}")
                # Empty response treated as error — consume error budget
                if error_retries_remaining > 0:
                    error_retries_remaining -= 1
                    error_retry_count += 1
                    backoff = _get_backoff_seconds(error_retry_count)
                    logger.info(f"Empty output. Consuming error retry. Backoff {backoff}s. Retrying...")
                    time.sleep(backoff)
                    continue
                else:
                    break

            # Parse and track best
            articles = _parse_grok_response(raw, target_date)
            previous_count = len(articles)
            if len(articles) > len(best_articles):
                best_articles = articles
                logger.info(f"New best result: {len(best_articles)} posts (attempt {attempt})")

            # If meets trigger, accept immediately
            if len(articles) >= GROK_MIN_POSTS_TRIGGER:
                logger.info(f"Grok threshold met ({len(articles)} >= {GROK_MIN_POSTS_TRIGGER}) — accepting")
                return articles

            # Below trigger — retry with feedback if low-count budget remains
            if lowcount_retries_remaining > 0:
                lowcount_retries_remaining -= 1
                logger.warning(
                    f"Grok returned {len(articles)} posts (trigger: {GROK_MIN_POSTS_TRIGGER}, target: {GROK_TARGET_POSTS}+). "
                    f"Consuming lowcount retry. Retrying with aggressive feedback in 90s..."
                )
                time.sleep(90)
                continue
            else:
                logger.warning(
                    f"No lowcount retries remaining. Final yield: {len(articles)} posts. "
                    f"Returning best across {attempt} attempts: {len(best_articles)} posts."
                )
                break

        except Exception as e:
            logger.error(f"Grok response processing failed (attempt {attempt}): {e}")
            if error_retries_remaining > 0:
                error_retries_remaining -= 1
                error_retry_count += 1
                backoff = _get_backoff_seconds(error_retry_count)
                time.sleep(backoff)
                continue
            else:
                break

    if not best_articles and last_error:
        logger.error(f"Grok API call failed after {attempt} attempt(s): {last_error}")

    # LEVEL 3 FALLBACK: if all live attempts failed, try yesterday's cached discussoes_x.
    # Items are tagged with `_cache_fallback: True` for frontend awareness.
    # NOTE: cached items already in discussoes_x schema (transformed yesterday).
    # We return them in the GROK schema and let transform_to_discussoes_x handle below.
    if not best_articles:
        cached = _load_cached_discussoes_x()
        if cached:
            # Mark as a special "already-transformed" payload for downstream handling
            for item in cached:
                item["_already_transformed"] = True
            return cached

    return best_articles


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

    SPECIAL CASE: cache fallback items already have discussoes_x schema (loaded
    from yesterday's report). They have `_already_transformed: True` flag and
    `_cache_fallback: True`. Pass through unchanged.
    """
    # Detect cache fallback: if items have _already_transformed flag, return as-is
    if grok_articles and grok_articles[0].get("_already_transformed"):
        logger.info(
            f"transform_to_discussoes_x: pass-through {len(grok_articles)} cached items "
            f"(Grok unavailable today, using yesterday's data)"
        )
        # Strip internal flags but keep _cache_fallback for frontend
        cleaned = []
        for item in grok_articles:
            item_copy = {k: v for k, v in item.items() if k != "_already_transformed"}
            cleaned.append(item_copy)
        return cleaned

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
