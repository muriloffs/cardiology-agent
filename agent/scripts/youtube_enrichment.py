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

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_CALL_TIMEOUT = 60
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


def _build_video_prompt(video: dict) -> str:
    titulo = video.get("titulo", "")
    canal = video.get("canal", "")
    url = video.get("video_url", "")
    desc = (video.get("descricao_preview") or "")[:500]
    return f"""You are enriching a YouTube cardiology video for a Brazilian cardiologist's daily dashboard.

Video metadata (RSS):
- Channel: {canal}
- Title: {titulo}
- URL: {url}
- Description: {desc}

Use Google Search if needed to understand context. Respond using EXACTLY this format:

TEMA: <main topic in 2-4 words em português brasileiro>
BULLETS:
- <takeaway clínico 1 em PT-BR, frase curta>
- <takeaway clínico 2 em PT-BR>
- <takeaway clínico 3 em PT-BR>
RESUMO: <2-3 sentence summary em PT-BR brasileiro about the clinical content>
TAGS: <3-5 keywords PT-BR or canonical English terms (TAVR, PCI, HFpEF), comma-separated, no '#'>

Idioma das saídas: português brasileiro obrigatório (TAVR, PCI, HFpEF e siglas técnicas podem ficar em inglês). Plain text only. No JSON. No markdown."""


def _parse_video_response(text: str) -> dict | None:
    """Extract enrichment fields from a single Gemini response."""
    if not text:
        return None
    out = {"tema": "", "bullets_pt": [], "resumo_pt": "", "tags": []}
    current = None
    for raw_line in text.split("\n"):
        line = raw_line.rstrip()
        if not line.strip():
            continue
        m = re.match(r"^\s*([A-Z]+)\s*:\s*(.*)$", line)
        if m:
            label = m.group(1).upper()
            value = m.group(2).strip()
            value = re.sub(r"\*+([^*]+)\*+", r"\1", value)
            if label == "TEMA":
                current = "tema"; out["tema"] = value
            elif label == "RESUMO":
                current = "resumo_pt"; out["resumo_pt"] = value
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
        # Continuation
        stripped = line.strip()
        if current == "bullets_pt":
            cleaned = re.sub(r"^[\-\*•\d\.\)]+\s*", "", stripped).strip()
            cleaned = re.sub(r"\*+([^*]+)\*+", r"\1", cleaned)
            if cleaned:
                out["bullets_pt"].append(cleaned)
        elif current == "resumo_pt":
            out["resumo_pt"] = (out["resumo_pt"] + " " + stripped).strip()

    if not (out["tema"] or out["resumo_pt"] or out["bullets_pt"]):
        return None
    out["bullets_pt"] = out["bullets_pt"][:5]
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
        # 3 workers for safety with Flash rate limits
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {
                pool.submit(_grounded_call, client, _build_video_prompt(v), f"yt:{v.get('video_url','?')[-20:]}"): (idx, v)
                for idx, v in to_enrich
            }
            for future in as_completed(futures):
                idx, video = futures[future]
                url = video.get("video_url", "")
                try:
                    text = future.result(timeout=GEMINI_CALL_TIMEOUT)
                    parsed = _parse_video_response(text)
                    if parsed:
                        video.update(parsed)
                        video["_enriched"] = True
                        video["_enriched_at"] = today_iso
                        cache[url] = {**parsed, "enriched_at": today_iso}
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
