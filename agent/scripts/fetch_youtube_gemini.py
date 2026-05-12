"""Fetch recent cardiology YouTube videos via Gemini with Google Search grounding.

Replaces fetch_youtube.py (RSS scraping) when GitHub Actions runner IPs are
blocked by YouTube (all channel feeds return 404/500 to datacenter IPs).
Gemini uses Google's internal infrastructure — same approach already works
for Substacks (paywalled), Medscape (login-walled), Healio (Cloudflare).

Channel list and tier metadata are reused from fetch_youtube.YOUTUBE_CHANNELS.
Output shape is identical so downstream code (agent.py, frontend) works unchanged.
"""

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from agent.scripts.fetch_youtube import (
    YOUTUBE_CHANNELS,
    CARDIO_KEYWORDS,
    PER_CHANNEL_CAP,
    TIER0_CHANNEL_CAP,
    GLOBAL_CAP,
    _date_to_int,
)
from agent.scripts.fetch_gemini_external import _get_client, _grounded_call

logger = logging.getLogger(__name__)

GEMINI_PER_CHANNEL_TIMEOUT = 60   # per-channel Gemini call timeout (s)


# ──────────────────────────────────────────────────────────────────────
# Per-channel prompt + parser
# ──────────────────────────────────────────────────────────────────────

def _build_channel_prompt(channel_name: str, channel_id: str, days_back: int) -> str:
    """Single-target grounded prompt — proven pattern from fetch_gemini_external."""
    return (
        f"Use Google Search to find the {TIER0_CHANNEL_CAP} most recent videos uploaded "
        f"to the YouTube channel \"{channel_name}\" "
        f"(URL: https://www.youtube.com/channel/{channel_id}) in the last {days_back} days.\n\n"
        f"For each video, respond with ONE line in this EXACT format:\n"
        f"TITLE: <video title> | URL: <full youtube.com/watch?v=... URL> | "
        f"DATE: <publication date YYYY-MM-DD> | DESC: <first 200 chars of video description>\n\n"
        f"Plain text only. No JSON. No markdown. Do NOT invent URLs — only return "
        f"real videos you found via Google Search. If none found in this window: NONE"
    )


_VIDEO_ID_RE = re.compile(r"(?:youtube\.com/watch\?v=|youtu\.be/)([A-Za-z0-9_-]{11})")


def _extract_video_id(url: str) -> str | None:
    """Extract 11-char YouTube video ID from any video URL variant."""
    m = _VIDEO_ID_RE.search(url or "")
    return m.group(1) if m else None


def _parse_channel_response(text: str, channel: dict) -> list[dict[str, Any]]:
    """Parse pipe-format Gemini response into video items.

    Drops any line where:
    - URL doesn't have a parseable YouTube video ID
    - Title is empty
    - (For cardio-filter channels) title + desc has zero cardio keywords
    """
    if not text or text.strip().upper() == "NONE":
        return []

    cap = TIER0_CHANNEL_CAP if channel["tier"] == 0 else PER_CHANNEL_CAP
    videos: list[dict[str, Any]] = []

    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line or "|" not in line:
            continue
        # Skip headers, bullets, comments
        line = re.sub(r"^\s*[\-\*\d\.\)]+\s*", "", line)
        if line.upper() in ("NONE", "NO RESULTS", "NOT FOUND"):
            continue

        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 2:
            continue

        # Strip LABEL: prefixes
        def _strip_label(s: str) -> str:
            return re.sub(r"^[A-Z]+\s*:?\s*", "", s).strip()

        title = _strip_label(parts[0])
        url   = _strip_label(parts[1]) if len(parts) > 1 else ""
        date  = _strip_label(parts[2]) if len(parts) > 2 else ""
        desc  = _strip_label(parts[3]) if len(parts) > 3 else ""

        if not title or not url.startswith("http"):
            continue
        video_id = _extract_video_id(url)
        if not video_id:
            # Gemini may have hallucinated a URL — drop silently
            continue

        # Apply cardio keyword filter for general-content channels (skip Tier 0)
        if channel["tier"] != 0 and channel.get("filter_cardio"):
            text_low = (title + " " + desc).lower()
            if not any(kw in text_low for kw in CARDIO_KEYWORDS):
                continue

        # Normalize date — accept ISO-like, fall back to "recent"
        date_clean = "recent"
        m = re.search(r"\d{4}-\d{2}-\d{2}", date)
        if m:
            date_clean = m.group(0)

        videos.append({
            "titulo": title,
            "canal": channel["name"],
            "tier": channel["tier"],
            "data_publicacao": date_clean,
            "thumbnail": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
            "video_url": f"https://www.youtube.com/watch?v={video_id}",
            "descricao_preview": desc[:2500],
            "categoria_fonte": "youtube",
            "emoji": "📺",
        })
        if len(videos) >= cap:
            break

    return videos


def fetch_channel_via_gemini(client, channel: dict, days_back: int = 3) -> list[dict[str, Any]]:
    """Fetch recent videos from ONE channel via Gemini grounded search."""
    prompt = _build_channel_prompt(channel["name"], channel["channel_id"], days_back)
    label = f"yt:{channel['name'][:24]}"
    try:
        text = _grounded_call(client, prompt, label)
    except Exception as e:
        logger.warning(f"YouTube Gemini fetch [{channel['name']}] failed: {type(e).__name__}: {e}")
        return []
    videos = _parse_channel_response(text, channel)
    logger.info(f"YouTube/Gemini {channel['name']} (T{channel['tier']}): {len(videos)} video(s)")
    return videos


# ──────────────────────────────────────────────────────────────────────
# Orchestrator (drop-in replacement for fetch_all_youtube)
# ──────────────────────────────────────────────────────────────────────

def fetch_all_youtube_gemini(days_back: int = 3) -> list[dict[str, Any]]:
    """Fetch recent cardiology videos from all configured channels via Gemini.

    Drop-in replacement for fetch_all_youtube() — same return shape, same caps,
    same sort order. Works from GitHub Actions runners (RSS scraping is blocked).
    """
    client = _get_client()
    if not client:
        logger.warning("GOOGLE_API_KEY not set — YouTube/Gemini fetcher returning empty")
        return []

    all_videos: list[dict[str, Any]] = []
    # 3 workers respects Gemini Pro free-tier rate limits (2 RPM) with safety margin.
    # 30 channels / 3 workers = ~10 sequential batches. Each call ~10-30s → ~3-5 min total.
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(fetch_channel_via_gemini, client, ch, days_back): ch
            for ch in YOUTUBE_CHANNELS
        }
        for future in as_completed(futures):
            ch = futures[future]
            try:
                videos = future.result(timeout=GEMINI_PER_CHANNEL_TIMEOUT)
                all_videos.extend(videos)
            except Exception as e:
                logger.warning(f"YouTube/Gemini [{ch['name']}] timeout/error: {type(e).__name__}")

    # Same sort/cap logic as fetch_all_youtube
    all_videos.sort(key=lambda v: (v["tier"], -_date_to_int(v["data_publicacao"])))
    capped = all_videos[:GLOBAL_CAP]
    logger.info(
        f"YouTube/Gemini total: {len(capped)} videos "
        f"(from {len(all_videos)} pre-cap, {len(YOUTUBE_CHANNELS)} channels)"
    )
    return capped


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    vids = fetch_all_youtube_gemini(days_back=3)
    print(f"\n{len(vids)} videos found via Gemini:\n")
    for v in vids[:20]:
        print(f"  [YT/G T{v['tier']}] [{v['canal']}] {v['titulo'][:60]}")
        print(f"     {v['data_publicacao']} | {v['video_url']}")
        if v["descricao_preview"]:
            print(f"     {v['descricao_preview'][:100]}")
        print()
