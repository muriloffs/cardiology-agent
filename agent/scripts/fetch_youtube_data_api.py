"""Fetch recent cardiology YouTube videos via YouTube Data API v3 (official).

Replaces fetch_youtube_gemini.py (Gemini Search grounding doesn't reliably list
channel uploads — validated empirically 2026-05-12: 1/30 channels returned a
video despite the videos existing).

Key efficiency win: uses `playlistItems.list` against each channel's "uploads"
playlist instead of `search.list`. Quota cost difference:
  - search.list: 100 units per call → 30 channels = 3000 units/day
  - playlistItems.list: 1 unit per call → 30 channels = 30 units/day (0.3% of 10k free quota)

The "uploads playlist" trick: every YouTube channel has an auto-generated
playlist with all videos. Its ID derives from the channel ID by replacing the
'UC' prefix with 'UU'. So `UClNIx-dih_PN9C_noVw4zWA` → `UUlNIx-dih_PN9C_noVw4zWA`.
No extra API call needed to discover it.

Output shape is identical to fetch_youtube_gemini.py so downstream code
(agent.py, frontend) works unchanged.
"""

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from agent.scripts.fetch_youtube import (
    YOUTUBE_CHANNELS,
    CARDIO_KEYWORDS,
    PER_CHANNEL_CAP,
    TIER0_CHANNEL_CAP,
    GLOBAL_CAP,
    _date_to_int,
)

logger = logging.getLogger(__name__)

API_BASE = "https://www.googleapis.com/youtube/v3/playlistItems"
API_TIMEOUT_S = 15


def _channel_id_to_uploads_playlist(channel_id: str) -> str:
    """Convert UC... channel ID to UU... uploads-playlist ID.

    YouTube guarantees this naming convention since 2013 — every UC channel
    has a corresponding UU uploads playlist with all public uploads.
    """
    if not channel_id or not channel_id.startswith("UC"):
        return channel_id  # don't transform if it doesn't look like a channel ID
    return "UU" + channel_id[2:]


def _parse_iso_datetime(iso_str: str) -> datetime | None:
    """Parse YouTube's ISO 8601 timestamp (always with Z or +00:00 suffix)."""
    if not iso_str:
        return None
    try:
        # YouTube uses Z suffix; fromisoformat needs +00:00 in older Pythons.
        return datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def fetch_channel_via_api(api_key: str, channel: dict, days_back: int = 3) -> list[dict[str, Any]]:
    """Fetch recent videos from ONE channel via YouTube Data API v3."""
    uploads_playlist_id = _channel_id_to_uploads_playlist(channel["channel_id"])
    params = {
        "key": api_key,
        "playlistId": uploads_playlist_id,
        "part": "snippet",
        "maxResults": 15,  # fetch enough to cover days_back window
    }

    try:
        response = requests.get(API_BASE, params=params, timeout=API_TIMEOUT_S)
        # Don't raise on non-200 — extract reason for logs
        if response.status_code != 200:
            try:
                err_body = response.json().get("error", {}).get("message", response.text[:200])
            except Exception:
                err_body = response.text[:200]
            logger.warning(
                f"YouTube/API [{channel['name']}] HTTP {response.status_code}: {err_body}"
            )
            return []
        data = response.json()
    except requests.RequestException as e:
        logger.warning(f"YouTube/API [{channel['name']}] request failed: {type(e).__name__}: {e}")
        return []
    except ValueError as e:  # JSON decode error
        logger.warning(f"YouTube/API [{channel['name']}] invalid JSON: {e}")
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    cap = TIER0_CHANNEL_CAP if channel["tier"] == 0 else PER_CHANNEL_CAP

    videos: list[dict[str, Any]] = []
    for item in data.get("items", []) or []:
        snippet = item.get("snippet") or {}
        pub_date = _parse_iso_datetime(snippet.get("publishedAt", ""))
        if pub_date and pub_date < cutoff:
            continue

        title = (snippet.get("title") or "").strip()
        if not title:
            continue

        description = snippet.get("description") or ""

        # Apply cardio filter for general-content channels (Tier 0 is always pinned/unfiltered)
        if channel["tier"] != 0 and channel.get("filter_cardio"):
            text_low = (title + " " + description).lower()
            if not any(kw in text_low for kw in CARDIO_KEYWORDS):
                continue

        resource = snippet.get("resourceId") or {}
        video_id = resource.get("videoId")
        if not video_id:
            continue

        # Use API-provided high-res thumbnail when available; fallback to our pattern
        thumbnails = snippet.get("thumbnails") or {}
        thumb_url = (
            (thumbnails.get("high") or {}).get("url")
            or (thumbnails.get("medium") or {}).get("url")
            or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
        )

        videos.append({
            "titulo": title,
            "canal": channel["name"],
            "tier": channel["tier"],
            "data_publicacao": pub_date.strftime("%Y-%m-%d") if pub_date else "recent",
            "thumbnail": thumb_url,
            "video_url": f"https://www.youtube.com/watch?v={video_id}",
            # 2500 chars covers full description for ESC/Radcliffe/Cleveland.
            # YouTube descriptions are authoritative (written by uploader) — this is
            # the only "real text" we use for the video cards (no LLM inference).
            "descricao_preview": description[:2500],
            "categoria_fonte": "youtube",
            "emoji": "📺",
        })

        if len(videos) >= cap:
            break

    logger.info(f"YouTube/API {channel['name']} (T{channel['tier']}): {len(videos)} video(s)")
    return videos


def fetch_all_youtube_data_api(days_back: int = 3) -> list[dict[str, Any]]:
    """Fetch recent cardiology videos from all configured channels via YouTube Data API v3.

    Drop-in replacement for fetch_all_youtube() / fetch_all_youtube_gemini().
    Returns empty list if YOUTUBE_API_KEY/GOOGLE_API_KEY not configured.

    Quota usage per run: ~30 units (one playlistItems.list call per channel).
    Free tier daily limit: 10000 units. We use ~0.3% — practically unlimited.
    """
    # Prefer YOUTUBE_API_KEY if set; fall back to GOOGLE_API_KEY (same key after
    # enabling YouTube Data API v3 on the Gemini project — common setup).
    api_key = os.environ.get("YOUTUBE_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        logger.warning("No YOUTUBE_API_KEY or GOOGLE_API_KEY — YouTube fetcher returning empty")
        return []

    all_videos: list[dict[str, Any]] = []
    # 10 parallel workers is safe for YouTube API (10k quota daily, ample headroom).
    # Each call is ~200-400ms, so 30 channels finish in 2-3 batches = ~1 second total.
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {
            pool.submit(fetch_channel_via_api, api_key, ch, days_back): ch
            for ch in YOUTUBE_CHANNELS
        }
        for future in as_completed(futures):
            ch = futures[future]
            try:
                videos = future.result(timeout=30)
                all_videos.extend(videos)
            except Exception as e:
                logger.warning(f"YouTube/API [{ch['name']}] error: {type(e).__name__}: {e}")

    # Same sort/cap logic as fetch_all_youtube
    all_videos.sort(key=lambda v: (v["tier"], -_date_to_int(v["data_publicacao"])))
    capped = all_videos[:GLOBAL_CAP]
    logger.info(
        f"YouTube/API total: {len(capped)} videos "
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
    vids = fetch_all_youtube_data_api(days_back=3)
    print(f"\n{len(vids)} videos found via YouTube Data API v3:\n")
    for v in vids[:20]:
        print(f"  [API T{v['tier']}] [{v['canal']}] {v['titulo'][:60]}")
        print(f"     {v['data_publicacao']} | {v['video_url']}")
        if v["descricao_preview"]:
            print(f"     {v['descricao_preview'][:100]}")
        print()
