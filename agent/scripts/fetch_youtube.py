"""Fetch recent cardiology YouTube videos via official RSS feeds (no API key)."""

import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Any

import feedparser
import requests

logger = logging.getLogger(__name__)

# Tier 0: pinned BR channels (always shown, never filtered, no per-channel cap)
# Tier 1: cardio-focused societies, journals, expert discussion
# Tier 2: hospitals + subspecialty (filter_cardio True for general-content hospitals)
#
# All channel_ids verified 2026-05-09 via direct RSS check.
# To re-validate or add channels, run agent/scripts/validate_youtube_channels.py
YOUTUBE_CHANNELS = [
    # Tier 0 — pinned BR
    {"channel_id": "UClNIx-dih_PN9C_noVw4zWA", "name": "Afya CardioPapers", "tier": 0, "filter_cardio": False},
    # Tier 1 — sociedades + journals + discussion
    {"channel_id": "UCQFROke6pM580dsxDpVPxpA", "name": "European Society of Cardiology", "tier": 1, "filter_cardio": False},
    {"channel_id": "UCg2IevGMLxUlNXop_B_ONSw", "name": "American College of Cardiology", "tier": 1, "filter_cardio": False},
    {"channel_id": "UCLiWQk8JzhNRcNiDKk4dpaw", "name": "American Heart Association", "tier": 1, "filter_cardio": True},
    {"channel_id": "UC4WoM9nQ9phjR7UcSWjmwYw", "name": "TV SBC", "tier": 1, "filter_cardio": False},
    {"channel_id": "UCPLfhDi2mxubwhBjPLMxpvA", "name": "American Society of Echocardiography", "tier": 1, "filter_cardio": False},
    {"channel_id": "UCqO3GxVYutcugyknCWdAcUA", "name": "NEJM Group", "tier": 1, "filter_cardio": True},
    {"channel_id": "UCmJZXhuw-rlWXhlP0s26TXA", "name": "Radcliffe Cardiology", "tier": 1, "filter_cardio": False},
    {"channel_id": "UCn9lTBhJJ92aHms20kGnQ7A", "name": "TCTMD", "tier": 1, "filter_cardio": False},
    {"channel_id": "UCyw9Y26bNNhQPkydxY93jyQ", "name": "Medscape", "tier": 1, "filter_cardio": True},
    {"channel_id": "UCHc-EqvlQpCfFYCONhpLk-A", "name": "InCor HC-FMUSP", "tier": 1, "filter_cardio": True},
    {"channel_id": "UCs-5YGSbudHWJ8tocivTSLQ", "name": "Instituto Dante Pazzanese", "tier": 1, "filter_cardio": True},
    {"channel_id": "UCOBWnSpfirz6OpK8xaIiwsw", "name": "Ensino InCor", "tier": 1, "filter_cardio": True},
    {"channel_id": "UCKf5uPfsrIOuH55id6JIG3Q", "name": "Doze por Oito Cardiologia", "tier": 1, "filter_cardio": False},
    {"channel_id": "UCR53umpvmSNLTtHVKSi9-Pg", "name": "Eco Descomplicado", "tier": 1, "filter_cardio": False},
    {"channel_id": "UCuu0ig2CLntBf4qNyIGM3-g", "name": "JACC Journals", "tier": 1, "filter_cardio": False},
    # Tier 2 — subspecialty societies (cardio-only, no filter)
    {"channel_id": "UCr8ae-VQRbjd110tbN6VW1A", "name": "Heart Rhythm Society", "tier": 2, "filter_cardio": False},
    {"channel_id": "UCpvyCp4WVmgEvlvui2aoEhA", "name": "SCAI", "tier": 2, "filter_cardio": False},
    {"channel_id": "UCjcct8jyA1s_c1MzhalEFEg", "name": "SCCT", "tier": 2, "filter_cardio": False},
    {"channel_id": "UCyzmqAh5YMTELU0NaYKWIPA", "name": "PCR / EuroPCR", "tier": 2, "filter_cardio": False},
    # Tier 2 — hospitals (mixed content, filter for cardio)
    {"channel_id": "UC8fQzKHIhSoZeSq3bwQx4mw", "name": "Mayo Clinic", "tier": 2, "filter_cardio": True},
    {"channel_id": "UCxyiSz4m161Z6frOsFxJpgw", "name": "Cleveland Clinic", "tier": 2, "filter_cardio": True},
    {"channel_id": "UC4ZyUot7ROY6H1kV8_J__kQ", "name": "Mount Sinai", "tier": 2, "filter_cardio": True},
    {"channel_id": "UCATNzbTbfeoMhNonZGZmrhA", "name": "Johns Hopkins Medicine", "tier": 2, "filter_cardio": True},
    {"channel_id": "UCDrQaGaHpOav5y7m1SCSJRg", "name": "Stanford Medicine", "tier": 2, "filter_cardio": True},
    {"channel_id": "UCQrgetn1CTBp3aa3xzbeXJw", "name": "Yale Medicine", "tier": 2, "filter_cardio": True},
    {"channel_id": "UCNhXTS_yLO9HgFuiQuhf2AA", "name": "Duke Health", "tier": 2, "filter_cardio": True},
    {"channel_id": "UC7tOeqLpmCejyymIyZlrWNQ", "name": "HCor", "tier": 2, "filter_cardio": True},
    {"channel_id": "UCYlaF2S8zWK7ntqw2vEP8qw", "name": "Hospital Sirio-Libanes", "tier": 2, "filter_cardio": True},
    {"channel_id": "UCFq5vPnNRNNNysLrktz4aSw", "name": "Strong Medicine", "tier": 2, "filter_cardio": True},
]

CARDIO_KEYWORDS = [
    "cardio", "heart", "ekg", "ecg", "afib", "atrial", "ventricular",
    "lipid", "cholesterol", "hypertension", "blood pressure", "statin",
    "anticoag", "warfarin", "doac", "ischem", "infarct", "valve",
    "failure", "arrhyth", "syncope", "tachy", "brady", "stent",
    "pci", "tavr", "cabg", "cad", "hf", "hfref", "hfpef",
    # PT-BR variants for Brazilian channels
    "coraç", "infart", "arritm", "valv", "isquêm", "press", "colester",
    "hipertens", "vascul", "tromb", "embol", "estenose",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

PER_CHANNEL_CAP = 3       # Standard channels: max 3 videos per pull
TIER0_CHANNEL_CAP = 5     # Pinned channels (CardioPapers): up to 5
GLOBAL_CAP = 50           # Final cap across all channels


def _parse_published_date(entry) -> datetime | None:
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        return datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
    return None


def _matches_cardio(title: str, summary: str) -> bool:
    text = f"{title} {summary}".lower()
    return any(kw in text for kw in CARDIO_KEYWORDS)


def _video_id_from_entry(entry) -> str | None:
    """YouTube RSS entries have id like 'yt:video:VIDEO_ID'."""
    raw_id = entry.get("yt_videoid") or entry.get("id", "")
    if raw_id.startswith("yt:video:"):
        return raw_id.split(":")[-1]
    return raw_id or None


def fetch_channel_videos(channel: dict, days_back: int = 2) -> list[dict[str, Any]]:
    """Fetch recent videos from one YouTube channel via RSS."""
    cid = channel["channel_id"]
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}"
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    cap = TIER0_CHANNEL_CAP if channel["tier"] == 0 else PER_CHANNEL_CAP

    try:
        response = requests.get(rss_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
    except Exception as e:
        logger.warning(f"Failed to fetch YouTube {channel['name']}: {e}")
        return []

    videos = []
    for entry in feed.entries[:15]:
        pub_date = _parse_published_date(entry)
        if pub_date and pub_date < cutoff:
            continue

        title = entry.get("title", "").strip()
        summary = entry.get("summary", "") or ""
        summary = re.sub(r"<[^>]+>", " ", summary)
        summary = re.sub(r"\s+", " ", summary).strip()

        if not title:
            continue

        # Apply cardio filter for general-content channels (skip Tier 0 — pinned, never filtered)
        if channel["tier"] != 0 and channel.get("filter_cardio") and not _matches_cardio(title, summary):
            continue

        video_id = _video_id_from_entry(entry)
        if not video_id:
            continue

        videos.append({
            "titulo": title,
            "canal": channel["name"],
            "tier": channel["tier"],
            "data_publicacao": pub_date.strftime("%Y-%m-%d") if pub_date else "recent",
            "thumbnail": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
            "video_url": f"https://www.youtube.com/watch?v={video_id}",
            "descricao_preview": summary[:500],
            "categoria_fonte": "youtube",
            "emoji": "📺",
        })

        if len(videos) >= cap:
            break

    logger.info(f"YouTube {channel['name']} (T{channel['tier']}): {len(videos)} video(s)")
    return videos


def fetch_all_youtube(days_back: int = 2) -> list[dict[str, Any]]:
    """Fetch recent videos from all configured YouTube channels."""
    all_videos = []
    for channel in YOUTUBE_CHANNELS:
        all_videos.extend(fetch_channel_videos(channel, days_back=days_back))

    # Sort: tier ASC (Tier 0 pinned at top), then date DESC
    all_videos.sort(key=lambda v: (v["tier"], v["data_publicacao"]), reverse=False)
    # Re-sort within tier by date desc — secondary sort done by reversing date string
    all_videos.sort(key=lambda v: (v["tier"], -_date_to_int(v["data_publicacao"])))

    capped = all_videos[:GLOBAL_CAP]
    logger.info(f"YouTube total: {len(capped)} videos (from {len(all_videos)} pre-cap, "
                f"{len(YOUTUBE_CHANNELS)} channels)")
    return capped


def _date_to_int(date_str: str) -> int:
    """Convert YYYY-MM-DD to int for sort comparison; 'recent' goes last."""
    if date_str == "recent":
        return 0
    try:
        return int(date_str.replace("-", ""))
    except ValueError:
        return 0


def transform_to_videos_youtube(videos: list[dict]) -> list[dict]:
    """Pass-through formatter to keep parity with discussoes_x bypass pattern."""
    return videos


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    # Reconfigure stdout for UTF-8 on Windows so emojis print
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    vids = fetch_all_youtube(days_back=3)
    print(f"\n{len(vids)} videos found:\n")
    for v in vids[:30]:
        print(f"  [YT T{v['tier']}] [{v['canal']}] {v['titulo'][:70]}")
        print(f"     {v['data_publicacao']} | {v['video_url']}")
        if v['descricao_preview']:
            print(f"     {v['descricao_preview'][:100]}")
        print()
