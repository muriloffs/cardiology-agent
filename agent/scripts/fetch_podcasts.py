"""Fetch recent cardiology podcast episodes from RSS feeds."""

import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Any

import feedparser
import requests

logger = logging.getLogger(__name__)

PODCAST_FEEDS = [
    {
        "name": "This Week in Cardiology (Mandrola)",
        "url": "https://rss.libsyn.com/shows/116734/destinations/668006.xml",
        "host": "Medscape / John Mandrola",
        "filter_cardio": False,
    },
    {
        "name": "Circulation on the Run",
        "url": "https://rss.libsyn.com/shows/81214/destinations/376443.xml",
        "host": "AHA / Circulation",
        "filter_cardio": False,
    },
    {
        "name": "JACC This Week",
        "url": "https://jaccaudio.libsyn.com/feed2",
        "host": "JACC Journals",
        "filter_cardio": False,
    },
    {
        "name": "ESC Cardio Talk",
        "url": "https://escardio.libsyn.com/rss",
        "host": "European Society of Cardiology",
        "filter_cardio": False,
    },
    {
        "name": "Eagle's Eye View",
        "url": "https://rss.libsyn.com/shows/104966/destinations/563201.xml",
        "host": "American College of Cardiology",
        "filter_cardio": False,
    },
    {
        "name": "European Heart Journal Podcast",
        "url": "https://feeds.blubrry.com/feeds/eurheartj.xml",
        "host": "Oxford / EHJ",
        "filter_cardio": False,
    },
    {
        "name": "CardioNerds",
        "url": "https://www.cardionerds.com/feed/podcast/",
        "host": "CardioNerds",
        "filter_cardio": False,
    },
    {
        "name": "Heart Sounds",
        "url": "https://anchor.fm/s/1118e15f4/podcast/rss",
        "host": "TCTMD",
        "filter_cardio": False,
    },
    {
        "name": "Curbsiders",
        "url": "https://audioboom.com/channels/5034728.rss",
        "host": "Curbsiders Internal Medicine",
        "filter_cardio": True,  # General IM podcast — keep only cardio episodes
    },
]

CARDIO_KEYWORDS = [
    "cardio", "heart", "ekg", "ecg", "afib", "atrial", "ventricular",
    "lipid", "cholesterol", "hypertension", "blood pressure", "statin",
    "anticoag", "warfarin", "doac", "ischem", "infarct", "valve",
    "failure", "arrhyth", "syncope", "tachy", "brady", "stent",
    "pci", "tavr", "cabg", "cad", "hf", "hfref", "hfpef",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def _parse_published_date(entry) -> datetime | None:
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        return datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
    return None


def _extract_audio_url(entry) -> str | None:
    """Find the .mp3/.m4a enclosure URL for the episode."""
    for enc in entry.get("enclosures", []) or []:
        url = enc.get("href") or enc.get("url")
        if url and (url.endswith(".mp3") or url.endswith(".m4a") or "audio" in enc.get("type", "")):
            return url
    return None


def _matches_cardio(title: str, summary: str) -> bool:
    text = f"{title} {summary}".lower()
    return any(kw in text for kw in CARDIO_KEYWORDS)


def fetch_podcast_feed(feed_config: dict, days_back: int = 7) -> list[dict[str, Any]]:
    """Fetch latest cardiology episode(s) from one podcast feed within window."""
    url = feed_config["url"]
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
    except Exception as e:
        logger.warning(f"Failed to fetch podcast {feed_config['name']}: {e}")
        return []

    episodes = []
    for entry in feed.entries[:5]:  # Only inspect 5 most recent per feed
        pub_date = _parse_published_date(entry)
        if pub_date and pub_date < cutoff:
            continue

        title = entry.get("title", "").strip()
        link = entry.get("link", "")
        summary = entry.get("summary", "") or entry.get("content", [{}])[0].get("value", "")
        summary = re.sub(r"<[^>]+>", " ", summary)
        summary = re.sub(r"\s+", " ", summary).strip()

        if not title or not link:
            continue

        if feed_config.get("filter_cardio") and not _matches_cardio(title, summary):
            continue

        audio_url = _extract_audio_url(entry)

        episodes.append({
            "titulo": title,
            "publicacao": feed_config["name"],
            "host": feed_config["host"],
            "data_publicacao": pub_date.strftime("%Y-%m-%d") if pub_date else "recent",
            "abstract": summary[:1500],
            "episode_url": link,
            "audio_url": audio_url,
            "categoria_fonte": "podcast",
            "emoji": "🎙️",
        })

    logger.info(f"{feed_config['name']}: {len(episodes)} recent episode(s)")
    return episodes[:1]  # Only the latest qualifying episode per show


def fetch_all_podcasts(days_back: int = 7) -> list[dict[str, Any]]:
    """Fetch latest episodes from all configured podcasts (one per show, last N days)."""
    all_episodes = []
    for feed_config in PODCAST_FEEDS:
        all_episodes.extend(fetch_podcast_feed(feed_config, days_back=days_back))
    logger.info(f"Podcasts total: {len(all_episodes)} episodes from {len(PODCAST_FEEDS)} shows")
    return all_episodes


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    eps = fetch_all_podcasts(days_back=7)
    print(f"\n{len(eps)} episodes found:\n")
    for e in eps:
        print(f"  🎙️ [{e['publicacao']}] {e['titulo'][:75]}")
        print(f"     {e['data_publicacao']} | {e['episode_url'][:60]}")
        print(f"     Audio: {(e['audio_url'] or 'N/A')[:60]}")
        print()
