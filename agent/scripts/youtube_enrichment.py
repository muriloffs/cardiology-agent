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


def _fetch_transcript(video_url: str, max_chars: int = 12000) -> str:
    """Fetch auto-generated transcript from YouTube. Returns empty if unavailable.

    Tries PT first, then EN, then any available language. Truncates to max_chars
    to keep prompt size manageable (Gemini Pro happily takes 12k tokens of input).
    """
    video_id = _video_id_from_url(video_url)
    if not video_id:
        return ""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        from youtube_transcript_api._errors import (
            TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
        )
    except ImportError:
        logger.warning("youtube-transcript-api not installed — skipping transcript fetch")
        return ""

    for langs in (["pt", "pt-BR"], ["en", "en-US"], None):
        try:
            if langs:
                entries = YouTubeTranscriptApi.get_transcript(video_id, languages=langs)
            else:
                entries = YouTubeTranscriptApi.get_transcript(video_id)
            text = " ".join(e.get("text", "") for e in entries).strip()
            if text:
                return text[:max_chars]
        except (NoTranscriptFound, TranscriptsDisabled, VideoUnavailable):
            if langs is None:
                return ""
            continue
        except Exception as e:
            logger.debug(f"Transcript fetch error for {video_id}: {type(e).__name__}: {e}")
            return ""
    return ""


def _video_id_from_url(url: str) -> str:
    """Extract video_id from a YouTube URL (handles ?v= and youtu.be/ shapes)."""
    m = re.search(r"(?:v=|youtu\.be/|watch\?v=|embed/|shorts/)([A-Za-z0-9_-]{11})", url)
    return m.group(1) if m else ""


def _build_video_prompt(video: dict, transcript: str = "") -> str:
    """Build enrichment prompt. If transcript provided, prefer it over description.

    Nível 1 (richer schema): 5-7 bullets, 5-7 sentence resumo, +3 new fields
    (quem_se_aplica, evidencia_chave, contraponto).
    Nível 2 (transcript): pass actual subtitle text when available — Gemini reads
    the real content vs. guessing from RSS description.
    """
    titulo = video.get("titulo", "")
    canal = video.get("canal", "")
    url = video.get("video_url", "")
    desc = (video.get("descricao_preview") or "")[:500]

    if transcript:
        content_block = (
            f"TRANSCRIPT (auto-generated subtitles, may have typos):\n"
            f"{transcript}\n\n"
            f"Base sua análise PRIMARIAMENTE no transcript acima — é o conteúdo real do vídeo."
        )
    else:
        content_block = (
            f"Description (RSS metadata):\n{desc}\n\n"
            f"Sem transcript disponível. Use Google Search se necessário para entender o tema."
        )

    return f"""Você é um cardiologista revisor analisando um vídeo do YouTube para um dashboard clínico brasileiro.

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
        # Step 1: fetch transcripts in parallel (cheap, no API key needed).
        # Step 2: call Gemini Pro with transcript when available, fallback to desc.
        # We do step 1 sequentially with shorter timeout — YouTube rate limits are
        # generous for transcript reads. Step 2 in pool because Gemini Pro is slow.
        transcripts: dict[str, str] = {}
        for idx, v in to_enrich:
            url = v.get("video_url", "")
            if not url:
                continue
            t = _fetch_transcript(url)
            if t:
                transcripts[url] = t
        with_transcript = len([1 for u in transcripts if transcripts[u]])
        logger.info(f"YouTube transcripts: {with_transcript}/{len(to_enrich)} videos have transcript")

        # 3 workers for parallel Gemini calls
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {
                pool.submit(
                    _grounded_call, client,
                    _build_video_prompt(v, transcripts.get(v.get("video_url", ""), "")),
                    f"yt:{v.get('video_url','?')[-20:]}"
                ): (idx, v)
                for idx, v in to_enrich
            }
            for future in as_completed(futures):
                idx, video = futures[future]
                url = video.get("video_url", "")
                try:
                    text = future.result(timeout=GEMINI_CALL_TIMEOUT)
                    parsed = _parse_video_response(text)
                    if parsed:
                        had_transcript = bool(transcripts.get(url))
                        video.update(parsed)
                        video["_enriched"] = True
                        video["_enriched_at"] = today_iso
                        video["_transcript_used"] = had_transcript
                        cache[url] = {**parsed, "enriched_at": today_iso, "_transcript_used": had_transcript}
                        new_enrichments += 1
                    else:
                        video["_enriched"] = False
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
