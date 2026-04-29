"""Fetch cardiology content from RSS feeds — news, newsletters, and Substacks."""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

import feedparser
import requests

logger = logging.getLogger(__name__)

# Working RSS feeds verified to be publicly accessible
RSS_FEEDS = [
    {
        "url": "https://erictopol.substack.com/feed",
        "source": "Ground Truths (Eric Topol)",
        "categoria": "substack",
        "emoji": "📝",
    },
    {
        "url": "https://www.tctmd.com/feed",
        "source": "TCTMD",
        "categoria": "revista",
        "emoji": "💉",
    },
    {
        "url": "https://www.healio.com/rss/cardiology",
        "source": "Healio Cardiology",
        "categoria": "revista",
        "emoji": "📰",
    },
    {
        "url": "https://drsingh.substack.com/feed",
        "source": "Dr. Singh (Preventive Cardiology)",
        "categoria": "substack",
        "emoji": "📝",
    },
    {
        "url": "https://preventivecardiology.substack.com/feed",
        "source": "Preventive Cardiology Newsletter",
        "categoria": "substack",
        "emoji": "📝",
    },
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def _parse_published_date(entry) -> datetime | None:
    """Extract published datetime from a feedparser entry."""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        return datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
    return None


def fetch_feed(feed_config: dict, days_back: int = 2) -> list[dict[str, Any]]:
    """Fetch and filter entries from a single RSS feed."""
    url = feed_config["url"]
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return []

    articles = []
    for entry in feed.entries:
        pub_date = _parse_published_date(entry)

        # Skip if older than cutoff (allow None dates — include them)
        if pub_date and pub_date < cutoff:
            continue

        title = entry.get("title", "").strip()
        link = entry.get("link", "")
        summary = entry.get("summary", "") or entry.get("content", [{}])[0].get("value", "")

        # Strip basic HTML tags from summary
        import re
        summary = re.sub(r"<[^>]+>", " ", summary).strip()
        summary = re.sub(r"\s+", " ", summary)[:600]

        if not title or not link:
            continue

        articles.append({
            "pmid": None,
            "titulo": title,
            "publicacao": feed_config["source"],
            "autores": [],
            "data_publicacao": pub_date.strftime("%Y %b %d") if pub_date else "recent",
            "abstract": summary,
            "doi": None,
            "pubmed_url": link,
            "doi_url": None,
            "categoria_fonte": feed_config["categoria"],
            "emoji": feed_config["emoji"],
        })

    logger.info(f"{feed_config['source']}: {len(articles)} recent items")
    return articles


def fetch_all_rss(days_back: int = 2) -> list[dict[str, Any]]:
    """Fetch recent cardiology content from all configured RSS feeds."""
    all_articles = []

    for feed_config in RSS_FEEDS:
        articles = fetch_feed(feed_config, days_back=days_back)
        all_articles.extend(articles)

    logger.info(f"RSS total: {len(all_articles)} items from {len(RSS_FEEDS)} feeds")
    return all_articles


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    articles = fetch_all_rss(days_back=3)
    print(f"\n{len(articles)} items from RSS feeds:\n")
    for a in articles:
        print(f"  [{a['publicacao']}] {a['titulo'][:75]}")
        print(f"    {a['data_publicacao']} | {a['pubmed_url'][:60]}")
        print()
