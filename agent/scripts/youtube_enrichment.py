"""Enrich YouTube video metadata with Gemini-generated PT-BR summaries.

Why: raw YouTube RSS gives us only title + channel + description preview.
Phase 6 adds tema, bullets, resumo PT-BR via Gemini Flash + Google Search
grounding (same pattern as fetch_gemini_substacks.py).

Cost control via cache: each video is enriched once and cached by video_url.
Cache persists in data/youtube_enrichment_cache.json (committed to git like
daily reports). Most videos in the 3-day window appeared in yesterday's
report too, so cache hit rate is typically ~70-80% — keeps cost ~$0.002/day.

Cache schema:
{
    "<video_url>": {
        "tema": str, "resumo_pt": str, "bullets_pt": [str],
        "tags": [str], "enriched_at": "YYYY-MM-DD"
    }
}
"""

import json
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-2.5-pro"
GEMINI_CALL_TIMEOUT = 120  # Pro reads transcripts deeply — more time needed
CACHE_FILE = Path(__file__).parent.parent.parent / "data" / "youtube_enrichment_cache.json"
CACHE_TTL_DAYS = 90  # drop entries older than this on save


def _get_client():
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return None
    try:
        from google import genai
        return genai.Client(api_key=api_key)
    except ImportError:
        logger.error("google-genai SDK not installed")
        return None


def _extract_text(response) -> str:
    if hasattr(response, "text") and response.text:
        return response.text.strip()
    if hasattr(response, "candidates") and response.candidates:
        parts = []
        for cand in response.candidates:
            if hasattr(cand, "content") and cand.content and hasattr(cand.content, "parts"):
                for part in cand.content.parts or []:
                    if hasattr(part, "text") and part.text:
                        parts.append(part.text)
        return "\n".join(parts).strip()
    return ""


def _grounded_call(client, prompt: str, label: str, _is_retry: bool = False) -> str:
    """Same retry-on-empty pattern used in other Gemini fetchers."""
    try:
        from google.genai import types
        config = types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.4 if _is_retry else 0.1,
        )
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=config,
        )
        text = _extract_text(response)
        if not text and not _is_retry:
            logger.info(f"[{label}] Empty — retrying once")
            return _grounded_call(client, prompt + "\n\nProceed and respond now.", label, _is_retry=True)
        return text
    except Exception as e:
        logger.warning(f"[{label}] Gemini call failed: {type(e).__name__}: {e}")
        return ""


def _build_ytt_api():
    """Build YouTubeTranscriptApi instance, with Webshare residential proxy
    when env vars are set.

    Two configuration paths:
    1. WEBSHARE_PROXY_URL — full URL override (recommended for plans where
       'username-rotate' doesn't exist; e.g., entry-tier Rotating Residential
       only has country-suffixed users like 'gomeecwk-gb-1').
    2. WEBSHARE_PROXY_USERNAME + WEBSHARE_PROXY_PASSWORD — library appends
       '-rotate' to username (only works if account has that user provisioned).

    Returns (api_instance, uses_proxy_bool, mode_label).
    """
    from youtube_transcript_api import YouTubeTranscriptApi

    # Path 1: full URL override (bypasses library's auto-rotate suffix)
    proxy_url = os.environ.get("WEBSHARE_PROXY_URL")
    if proxy_url:
        try:
            from youtube_transcript_api.proxies import GenericProxyConfig
            api = YouTubeTranscriptApi(proxy_config=GenericProxyConfig(
                http_url=proxy_url,
                https_url=proxy_url,
            ))
            return api, True, "generic_url"
        except (ImportError, AttributeError) as e:
            logger.warning(f"GenericProxyConfig unavailable ({e}); trying Webshare config")

    # Path 2: username/password with auto-rotate (library default)
    proxy_user = os.environ.get("WEBSHARE_PROXY_USERNAME")
    proxy_pass = os.environ.get("WEBSHARE_PROXY_PASSWORD")
    if proxy_user and proxy_pass:
        try:
            from youtube_transcript_api.proxies import WebshareProxyConfig
            api = YouTubeTranscriptApi(proxy_config=WebshareProxyConfig(
                proxy_username=proxy_user,
                proxy_password=proxy_pass,
            ))
            return api, True, "webshare_rotate"
        except (ImportError, AttributeError) as e:
            logger.warning(f"WebshareProxyConfig unavailable ({e}); falling back to direct")
    return YouTubeTranscriptApi(), False, "direct"


def _fetch_transcript(video_url: str, max_chars: int = 12000, per_call_timeout: int = 15) -> tuple[str, str]:
    """Fetch auto-generated transcript from YouTube.

    Returns (transcript_text, failure_reason). transcript_text is empty when
    unavailable; failure_reason gives a one-word diagnostic for logging:
      ok               → transcript fetched successfully
      no_video_id      → URL didn't parse to a valid video_id
      no_library       → youtube-transcript-api not installed
      no_transcript    → video has no captions in requested or any language
      disabled         → channel disabled subtitles for this video
      unavailable      → video private/deleted/region-locked
      ip_blocked       → IP-blocked by YouTube (most likely on datacenter IPs)
      other            → unexpected error (raw type logged separately)

    Tries PT first, then EN, then any language. Truncates to max_chars to keep
    prompt size manageable. When WEBSHARE_PROXY_USERNAME/PASSWORD env vars are
    set, routes through Webshare residential proxies (bypasses GH Actions IP block).
    """
    video_id = _video_id_from_url(video_url)
    if not video_id:
        return "", "no_video_id"
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        from youtube_transcript_api._errors import (
            TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
        )
    except ImportError:
        return "", "no_library"

    # Build API once per call (cheap — just stores proxy config)
    ytt_api, _, _ = _build_ytt_api()

    # Library API changed in v1.0 — support both v1.x (instance.fetch) and v0.6.x
    # (class.get_transcript) for resilience to version drift. Proxy only works in v1.x.
    def _call_api(vid: str, lang_list: list[str] | None):
        # v1.x — instance + fetch() — supports proxy
        if hasattr(ytt_api, "fetch"):
            if lang_list:
                return ytt_api.fetch(vid, languages=lang_list).to_raw_data()
            return ytt_api.fetch(vid).to_raw_data()
        # v0.6.x — classmethod fallback (no proxy support)
        if lang_list:
            return YouTubeTranscriptApi.get_transcript(vid, languages=lang_list)
        return YouTubeTranscriptApi.get_transcript(vid)

    # Timeout-wrapped call: prevents hangs from proxy/network silent stalls.
    # Without this, a misconfigured proxy can hang for 5+ min per video (lib's
    # 10 internal retries × 30s timeout each), exceeding workflow time budget.
    # With 15s cap per language attempt, max is ~45s per video (3 langs × 15s).
    def _call_api_timeout_safe(vid: str, lang_list, timeout_s: int):
        import concurrent.futures as _cf
        with _cf.ThreadPoolExecutor(max_workers=1) as _ex:
            future = _ex.submit(_call_api, vid, lang_list)
            try:
                return future.result(timeout=timeout_s)
            except _cf.TimeoutError:
                raise TimeoutError(f"transcript fetch >{timeout_s}s")

    last_failure = "other"
    for langs in (["pt", "pt-BR"], ["en", "en-US"], None):
        try:
            entries = _call_api_timeout_safe(video_id, langs, per_call_timeout)
            text = " ".join(e.get("text", "") for e in entries).strip()
            if text:
                return text[:max_chars], "ok"
        except NoTranscriptFound:
            last_failure = "no_transcript"
            continue
        except TranscriptsDisabled:
            last_failure = "disabled"
            break  # disabled is per-video, no point trying other langs
        except VideoUnavailable:
            last_failure = "unavailable"
            break
        except TimeoutError:
            last_failure = "timeout"
            logger.debug(f"[transcript {video_id}] timed out after {per_call_timeout}s on lang={langs}")
            break  # if one lang times out, others will too (proxy issue, not lang issue)
        except Exception as e:
            # Distinguish IP block (most likely failure mode in CI) from other
            err_str = str(e).lower()
            if "ip" in err_str or "block" in err_str or "request" in err_str:
                last_failure = "ip_blocked"
            else:
                last_failure = "other"
            logger.debug(f"[transcript {video_id}] {type(e).__name__}: {str(e)[:200]}")
            break

    return "", last_failure


def _video_id_from_url(url: str) -> str:
    """Extract video_id from a YouTube URL (handles ?v= and youtu.be/ shapes)."""
    m = re.search(r"(?:v=|youtu\.be/|watch\?v=|embed/|shorts/)([A-Za-z0-9_-]{11})", url)
    return m.group(1) if m else ""


def _build_video_prompt(video: dict, transcript: str = "") -> tuple[str, str]:
    """Build enrichment prompt with 3-tier source-of-truth strategy.

    Returns (prompt, source_label) where source_label ∈ {transcript, description, search}.

    Tier 1 — transcript: literal spoken content. Best fidelity.
    Tier 2 — description (≥150 chars): real text from channel uploader. Real but summarized.
    Tier 3 — search-only: Gemini infers from title + Google grounding. Lowest fidelity.

    The 150-char threshold is empirical: descriptions ≥150 chars from major cardio
    channels (ESC TV ~500, Radcliffe ~500, ASE ~360, NEJM ~174) consistently carry
    real content. Shorter ones (≤150) tend to be promotional one-liners and fall
    back to search grounding.
    """
    titulo = video.get("titulo", "")
    canal = video.get("canal", "")
    url = video.get("video_url", "")
    desc = (video.get("descricao_preview") or "")[:2000]  # bumped 500→2000

    if transcript:
        content_block = (
            f"TRANSCRIPT (auto-generated subtitles, may have typos):\n"
            f"{transcript}\n\n"
            f"Base sua análise PRIMARIAMENTE no transcript acima — é o conteúdo real falado no vídeo.\n"
            f"Cite dados específicos (números, nomes de speakers, estudos) que aparecem no transcript."
        )
        source = "transcript"
    elif len(desc) >= 150:
        content_block = (
            f"DESCRIÇÃO DO CANAL (texto que o uploader escreveu sobre o vídeo):\n"
            f"{desc}\n\n"
            f"Base sua análise PRIMARIAMENTE na descrição acima — é texto REAL do canal sobre o vídeo,\n"
            f"escrito pelo próprio uploader. Geralmente contém speakers, estudos citados, key findings.\n"
            f"Você pode usar Google Search COMPLEMENTARMENTE para entender melhor um estudo/conceito\n"
            f"mencionado na descrição, mas NÃO invente conteúdo que não esteja insinuado na descrição.\n"
            f"Se a descrição cita 'Dr Smith discute trial XYZ', seus bullets devem refletir isso."
        )
        source = "description"
    else:
        # Description too thin (<150 chars). Fall back to aggressive search.
        content_block = (
            f"Description (RSS metadata, MUITO CURTA — só {len(desc)} chars):\n{desc}\n\n"
            f"⚠️ SEM CONTEÚDO REAL DISPONÍVEL. Use Google Search agressivamente para:\n"
            f"1. Pesquisar o título do vídeo + nome do canal\n"
            f"2. Identificar o trial/paper/guideline central provável (se inferível)\n"
            f"3. Buscar cobertura paralela em journals, news, X\n"
            f"4. Inferir conteúdo a partir do padrão do canal + tópico do título\n\n"
            f"Bullets devem citar dados/conceitos REAIS que apareceriam num vídeo desse tópico.\n"
            f"Se realmente não conseguir inferir, retorne TEMA='N/D' e RESUMO explicando."
        )
        source = "search"

    prompt = f"""Você é um cardiologista revisor analisando um vídeo do YouTube para um dashboard clínico brasileiro.

Metadata do vídeo:
- Channel: {canal}
- Title: {titulo}
- URL: {url}

{content_block}

Responda EXATAMENTE neste formato:

TEMA: <tema principal em 2 a 5 palavras em português brasileiro>
BULLETS:
- <takeaway clínico 1 em PT-BR — frase curta, específica (cite números/nomes/contexto quando estiverem no conteúdo)>
- <takeaway clínico 2>
- <takeaway clínico 3>
- <takeaway clínico 4>
- <takeaway clínico 5>
- <takeaway 6 se relevante>
- <takeaway 7 se relevante>
RESUMO: <resumo em 5-7 frases em português brasileiro. Inclua: (1) o argumento/conteúdo central, (2) contexto clínico, (3) evidência/dados citados, (4) conclusão prática. Densidade editorial, não feed-style.>
QUEM_SE_APLICA: <1-2 frases sobre perfil de paciente / contexto clínico em que o conteúdo importa>
EVIDENCIA_CHAVE: <1 frase com o datapoint mais relevante mencionado — número, trial, estudo. Se nenhum dado específico mencionado: "Conteúdo conceitual sem datapoint específico.">
CONTRAPONTO: <1-2 frases com caveat/limitação/crítica. Se não há contraponto óbvio: "Sem contraponto significativo neste vídeo.">
TAGS: <3-5 keywords curtas separadas por vírgulas, em PT-BR ou termos técnicos (TAVR, HFpEF, GLP-1) — sem '#'>

REGRAS:
- Idioma OBRIGATÓRIO português brasileiro
- Não invente números/citações que não estão no conteúdo
- Plain text only, sem JSON, sem markdown (** ou ##)"""
    return prompt, source


def _parse_video_response(text: str) -> dict | None:
    """Extract enrichment fields from one Gemini response (Nível-1: includes 3 new fields)."""
    if not text:
        return None
    out = {
        "tema": "", "bullets_pt": [], "resumo_pt": "", "tags": [],
        "quem_se_aplica": "", "evidencia_chave": "", "contraponto": "",
    }
    LABEL_MAP = {
        "TEMA": "tema",
        "RESUMO": "resumo_pt",
        "QUEM_SE_APLICA": "quem_se_aplica", "QUEMSEAPLICA": "quem_se_aplica",
        "EVIDENCIA_CHAVE": "evidencia_chave", "EVIDENCIACHAVE": "evidencia_chave",
        "CONTRAPONTO": "contraponto",
    }
    MULTILINE_FIELDS = {"resumo_pt", "quem_se_aplica", "evidencia_chave", "contraponto"}

    current = None
    for raw_line in text.split("\n"):
        line = raw_line.rstrip()
        if not line.strip():
            continue
        m = re.match(r"^\s*([A-Z_]+)\s*:\s*(.*)$", line)
        if m:
            label = m.group(1).upper().replace(" ", "_")
            value = m.group(2).strip()
            value = re.sub(r"\*+([^*]+)\*+", r"\1", value)
            if label in LABEL_MAP:
                field = LABEL_MAP[label]
                current = field
                out[field] = value
            elif label == "TAGS":
                current = "tags"
                out["tags"] = [t.strip().lstrip("#") for t in value.split(",") if t.strip()][:6]
            elif label == "BULLETS":
                current = "bullets_pt"
                if value:
                    out["bullets_pt"].append(value)
            else:
                current = None
            continue
        # Continuation lines
        stripped = line.strip()
        if current == "bullets_pt":
            cleaned = re.sub(r"^[\-\*•\d\.\)]+\s*", "", stripped).strip()
            cleaned = re.sub(r"\*+([^*]+)\*+", r"\1", cleaned)
            if cleaned:
                out["bullets_pt"].append(cleaned)
        elif current in MULTILINE_FIELDS:
            out[current] = (out[current] + " " + stripped).strip()

    if not (out["tema"] or out["resumo_pt"] or out["bullets_pt"]):
        return None
    out["bullets_pt"] = out["bullets_pt"][:7]
    return out


# ──────────────────────────────────────────────────────────────────────
# Cache I/O
# ──────────────────────────────────────────────────────────────────────

def _load_cache() -> dict[str, dict]:
    if not CACHE_FILE.exists():
        return {}
    try:
        with open(CACHE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Could not read enrichment cache ({e}) — starting fresh")
        return {}


def _save_cache(cache: dict[str, dict]) -> None:
    """Drop entries older than CACHE_TTL_DAYS, then persist."""
    today = datetime.now(timezone.utc).date()
    fresh = {}
    for url, entry in cache.items():
        enriched_at = entry.get("enriched_at", "")
        try:
            d = datetime.strptime(enriched_at[:10], "%Y-%m-%d").date()
            if (today - d).days > CACHE_TTL_DAYS:
                continue
        except (ValueError, TypeError):
            pass
        fresh[url] = entry
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(fresh, f, ensure_ascii=False, indent=2)
        logger.info(f"YouTube enrichment cache saved: {len(fresh)} entries")
    except OSError as e:
        logger.warning(f"Could not save enrichment cache: {e}")


# ──────────────────────────────────────────────────────────────────────
# Orchestrator
# ──────────────────────────────────────────────────────────────────────

def enrich_videos(videos: list[dict]) -> list[dict]:
    """Enrich videos with Gemini-generated PT-BR fields, using cache when possible.

    Adds keys to each video: tema, bullets_pt, resumo_pt, tags, _enriched.
    On any failure (no API key, Gemini error), returns videos unchanged.
    """
    if not videos:
        return videos

    client = _get_client()
    if not client:
        logger.warning("GOOGLE_API_KEY not set — skipping YouTube enrichment")
        return videos

    cache = _load_cache()
    today_iso = datetime.now(timezone.utc).date().isoformat()

    cache_hits = 0
    new_enrichments = 0
    failures = 0

    # Identify which need enrichment (uncached)
    to_enrich: list[tuple[int, dict]] = []
    for idx, video in enumerate(videos):
        url = video.get("video_url", "")
        if not url:
            continue
        if url in cache:
            entry = cache[url]
            video.update({
                "tema": entry.get("tema", ""),
                "bullets_pt": entry.get("bullets_pt", []),
                "resumo_pt": entry.get("resumo_pt", ""),
                "tags": entry.get("tags", []),
                "_enriched": True,
                "_enriched_at": entry.get("enriched_at", ""),
            })
            cache_hits += 1
        else:
            to_enrich.append((idx, video))

    logger.info(f"YouTube enrichment: {cache_hits} cache hits, {len(to_enrich)} new videos to enrich")

    if to_enrich:
        # Diagnostic: log proxy mode for this run
        _, _, proxy_mode = _build_ytt_api()
        mode_msg = {
            "generic_url":     "WEBSHARE active (via WEBSHARE_PROXY_URL override)",
            "webshare_rotate": "WEBSHARE active (via auto-rotate suffix — only works if account has -rotate user)",
            "direct":          "direct (likely IP-blocked in CI)",
        }.get(proxy_mode, proxy_mode)
        logger.info(f"YouTube transcript proxy: {mode_msg}")

        # Step 1: fetch transcripts in parallel (cheap, no API key needed).
        # Step 2: call Gemini Pro with transcript when available, fallback to desc.
        # We do step 1 sequentially — YouTube rate limits transcript reads on
        # datacenter IPs aggressively. Step 2 in pool because Gemini Pro is slow.
        transcripts: dict[str, str] = {}
        failure_counts: dict[str, int] = {}
        for idx, v in to_enrich:
            url = v.get("video_url", "")
            if not url:
                continue
            t, reason = _fetch_transcript(url)
            if t:
                transcripts[url] = t
            else:
                failure_counts[reason] = failure_counts.get(reason, 0) + 1
        with_transcript = len(transcripts)
        if failure_counts:
            breakdown = ", ".join(f"{k}={v}" for k, v in sorted(failure_counts.items()))
            logger.info(f"YouTube transcripts: {with_transcript}/{len(to_enrich)} fetched — failures: {breakdown}")
        else:
            logger.info(f"YouTube transcripts: {with_transcript}/{len(to_enrich)} fetched")

        # Pre-build prompts so we know each video's source-of-truth tier.
        prompts_and_sources: dict[str, tuple[str, str]] = {}
        for idx, v in to_enrich:
            url = v.get("video_url", "")
            if not url:
                continue
            prompt, source = _build_video_prompt(v, transcripts.get(url, ""))
            prompts_and_sources[url] = (prompt, source)

        source_counts: dict[str, int] = {}
        for _, s in prompts_and_sources.values():
            source_counts[s] = source_counts.get(s, 0) + 1
        logger.info(f"YouTube enrichment source mix: {source_counts}")

        # 3 workers for parallel Gemini calls
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {
                pool.submit(
                    _grounded_call, client,
                    prompts_and_sources[v.get("video_url", "")][0],
                    f"yt:{v.get('video_url','?')[-20:]}"
                ): (idx, v)
                for idx, v in to_enrich
                if v.get("video_url", "") in prompts_and_sources
            }
            for future in as_completed(futures):
                idx, video = futures[future]
                url = video.get("video_url", "")
                source = prompts_and_sources[url][1]
                try:
                    text = future.result(timeout=GEMINI_CALL_TIMEOUT)
                    parsed = _parse_video_response(text)
                    if parsed:
                        video.update(parsed)
                        video["_enriched"] = True
                        video["_enriched_at"] = today_iso
                        # Backwards-compat: keep _transcript_used flag, plus new _source field
                        video["_transcript_used"] = (source == "transcript")
                        video["_source"] = source  # 'transcript' | 'description' | 'search'
                        cache[url] = {
                            **parsed,
                            "enriched_at": today_iso,
                            "_transcript_used": (source == "transcript"),
                            "_source": source,
                        }
                        new_enrichments += 1
                    else:
                        video["_enriched"] = False
                        video["_source"] = source
                        failures += 1
                except Exception as e:
                    logger.warning(f"Enrich failed for {url}: {e}")
                    video["_enriched"] = False
                    failures += 1

    if new_enrichments > 0:
        _save_cache(cache)

    logger.info(f"YouTube enrichment done: {cache_hits} cached + {new_enrichments} new, {failures} failures")
    return videos


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.INFO)

    sample = [
        {
            "video_url": "https://www.youtube.com/watch?v=test1",
            "titulo": "AFib Ablation: PFA vs RFA",
            "canal": "European Society of Cardiology",
            "descricao_preview": "Discussion of pulsed field ablation for atrial fibrillation."
        }
    ]
    enriched = enrich_videos(sample)
    print(json.dumps(enriched, ensure_ascii=False, indent=2))
