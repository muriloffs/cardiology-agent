"""Fetch recent cardiology YouTube videos via YouTube Data API v3 (official).

History of this module (lessons learned):
  - First attempt used playlistItems.list (1 unit/call, 30 units/day total).
  - 2026-05-14: YouTube started returning HTTP 403 "Requests to this API method
    are blocked" on playlistItems.list for ALL 30 channels from GitHub Actions
    runner IPs. The API was enabled correctly — YouTube just has a stricter
    anti-bot policy for that specific endpoint when called from datacenter IPs.
  - Migrated to search.list (100 units/call). Higher cost but works from
    datacenter IPs. 30 channels × 100 = 3000 units/day = 30% of 10k free quota
    (still comfortable).

search.list response shape differs slightly from playlistItems.list:
  - videoId is at `item.id.videoId` (vs `item.snippet.resourceId.videoId`)
  - description in snippet is truncated (~200 chars) — full description needs
    extra videos.list call (1 unit each). For now we accept the truncation —
    200 chars is enough for the card preview, and we're not enriching via LLM.

Output shape stays identical to upstream consumers (titulo, canal, tier, etc.).
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

API_BASE = "https://www.googleapis.com/youtube/v3/search"
API_TIMEOUT_S = 15


def _channel_id_to_uploads_playlist(channel_id: str) -> str:
    """Legacy helper from when we used playlistItems.list. Kept for backwards
    compat but not used in current search.list flow.

    Converts UC... channel ID to UU... uploads-playlist ID.
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
    """Fetch recent videos from ONE channel via YouTube Data API v3 (search.list).

    Uses search.list (100 units/call) instead of playlistItems.list (1 unit/call)
    because the latter is blocked from datacenter IPs as of 2026-05-14. Quota
    cost: 30 channels × 100 = 3000 units/day (30% of 10k free tier).

    search.list response shape:
      item.id.videoId  ← video ID (vs item.snippet.resourceId.videoId in playlistItems)
      item.snippet.title / description / publishedAt / thumbnails

    NOTE: description from search.list is TRUNCATED to ~200 chars. For the
    full description we'd need an extra videos.list call per video (1 unit each).
    Acceptable for now — card preview only needs the first sentences anyway.
    """
    # ISO 8601 cutoff for the publishedAfter filter — API does the filtering
    # server-side, so we don't waste quota on old videos.
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    cutoff_iso = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

    params = {
        "key": api_key,
        "channelId": channel["channel_id"],
        "part": "snippet",
        "type": "video",            # search.list also matches channels/playlists by default
        "order": "date",            # newest first
        "publishedAfter": cutoff_iso,
        "maxResults": 15,
    }

    try:
        response = requests.get(API_BASE, params=params, timeout=API_TIMEOUT_S)
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
    except ValueError as e:
        logger.warning(f"YouTube/API [{channel['name']}] invalid JSON: {e}")
        return []

    cap = TIER0_CHANNEL_CAP if channel["tier"] == 0 else PER_CHANNEL_CAP

    videos: list[dict[str, Any]] = []
    for item in data.get("items", []) or []:
        snippet = item.get("snippet") or {}
        pub_date = _parse_iso_datetime(snippet.get("publishedAt", ""))
        # Already filtered server-side via publishedAfter, but double-check for safety
        if pub_date and pub_date < cutoff:
            continue

        title = (snippet.get("title") or "").strip()
        if not title:
            continue

        description = snippet.get("description") or ""

        # Apply cardio filter for general-content channels (Tier 0 always unfiltered)
        if channel["tier"] != 0 and channel.get("filter_cardio"):
            text_low = (title + " " + description).lower()
            if not any(kw in text_low for kw in CARDIO_KEYWORDS):
                continue

        # search.list nests videoId differently than playlistItems.list:
        # item.id = {"kind": "youtube#video", "videoId": "..."}
        item_id_obj = item.get("id") or {}
        video_id = item_id_obj.get("videoId") if isinstance(item_id_obj, dict) else None
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

    Quota usage per run: ~3000 units (one search.list call per channel × 100 units).
    Free tier daily limit: 10000 units. We use ~30% — comfortable headroom.
    (Originally used playlistItems.list at 1 unit/call but it gets blocked from
    datacenter IPs as of 2026-05-14. search.list works but costs 100× more.)
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
