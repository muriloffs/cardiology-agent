"""Fetch real cardiology articles from PubMed API (last 24 hours)."""

import time
import logging
import requests
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

PUBMED_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# Cardiology search query covering the major topics
CARDIOLOGY_QUERY = (
    "(cardiology[MeSH Terms] OR "
    '"heart failure"[MeSH Terms] OR '
    '"coronary artery disease"[MeSH Terms] OR '
    '"atrial fibrillation"[MeSH Terms] OR '
    '"myocardial infarction"[MeSH Terms] OR '
    '"hypertension"[MeSH Terms] OR '
    '"arrhythmia"[MeSH Terms] OR '
    '"cardiac surgery"[MeSH Terms] OR '
    '"atherosclerosis"[MeSH Terms] OR '
    '"stroke"[MeSH Terms])'
)


def search_pubmed(days_back: int = 1, max_results: int = 40) -> list[str]:
    """Search PubMed for recent cardiology articles. Returns list of PMIDs."""
    params = {
        "db": "pubmed",
        "term": CARDIOLOGY_QUERY,
        "datetype": "pdat",
        "reldate": days_back,
        "retmax": max_results,
        "retmode": "json",
        "sort": "relevance",
    }

    try:
        response = requests.get(f"{PUBMED_BASE}/esearch.fcgi", params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        pmids = data.get("esearchresult", {}).get("idlist", [])
        logger.info(f"PubMed search returned {len(pmids)} articles")
        return pmids
    except Exception as e:
        logger.error(f"PubMed search failed: {e}")
        return []


def fetch_summaries(pmids: list[str]) -> list[dict[str, Any]]:
    """Fetch article summaries (title, journal, authors, abstract) for given PMIDs."""
    if not pmids:
        return []

    # Fetch summaries in one call
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "json",
    }

    try:
        response = requests.get(f"{PUBMED_BASE}/esummary.fcgi", params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        results = data.get("result", {})
    except Exception as e:
        logger.error(f"PubMed summary fetch failed: {e}")
        return []

    # Fetch abstracts separately (efetch returns plain text)
    time.sleep(0.4)  # Respect PubMed rate limit (3 req/s)
    abstracts = _fetch_abstracts(pmids)

    articles = []
    for pmid in pmids:
        item = results.get(pmid)
        if not item or item.get("uid") != pmid:
            continue

        authors = [
            a.get("name", "") for a in item.get("authors", [])[:4]
        ]

        # Build DOI link if available
        doi = next(
            (id_obj.get("value") for id_obj in item.get("articleids", [])
             if id_obj.get("idtype") == "doi"),
            None,
        )

        articles.append({
            "pmid": pmid,
            "titulo": item.get("title", "").rstrip("."),
            "publicacao": item.get("fulljournalname") or item.get("source", ""),
            "autores": authors,
            "data_publicacao": item.get("pubdate", ""),
            "abstract": abstracts.get(pmid, ""),
            "doi": doi,
            "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "doi_url": f"https://doi.org/{doi}" if doi else None,
        })

    logger.info(f"Fetched details for {len(articles)} articles")
    return articles


def _fetch_abstracts(pmids: list[str]) -> dict[str, str]:
    """Fetch abstracts for a list of PMIDs. Returns dict of pmid -> abstract."""
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "rettype": "abstract",
        "retmode": "text",
    }

    try:
        response = requests.get(f"{PUBMED_BASE}/efetch.fcgi", params=params, timeout=20)
        response.raise_for_status()
        raw = response.text
    except Exception as e:
        logger.warning(f"Abstract fetch failed: {e}")
        return {}

    # Parse plain-text abstract blocks — each block starts with "PMID: XXXXX"
    abstracts: dict[str, str] = {}
    current_pmid = None
    current_lines: list[str] = []

    for line in raw.splitlines():
        if line.startswith("PMID-"):
            if current_pmid and current_lines:
                abstracts[current_pmid] = " ".join(current_lines).strip()
            current_pmid = line.replace("PMID-", "").strip()
            current_lines = []
        elif line.startswith("AB  -") and current_pmid:
            current_lines.append(line[6:].strip())
        elif line.startswith("      ") and current_lines:
            current_lines.append(line.strip())

    if current_pmid and current_lines:
        abstracts[current_pmid] = " ".join(current_lines).strip()

    return abstracts


def fetch_recent_cardiology_articles(days_back: int = 1) -> list[dict[str, Any]]:
    """
    Main entry point. Fetch real cardiology articles from the last N days.
    Returns list of article dicts ready to pass to Claude for classification.
    """
    logger.info(f"Fetching cardiology articles from last {days_back} day(s)...")
    pmids = search_pubmed(days_back=days_back, max_results=40)

    if not pmids:
        logger.warning("No PMIDs returned. Falling back to 2-day window.")
        pmids = search_pubmed(days_back=2, max_results=40)

    if not pmids:
        logger.error("PubMed returned no results.")
        return []

    time.sleep(0.4)
    articles = fetch_summaries(pmids)
    return articles


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    articles = fetch_recent_cardiology_articles()
    print(f"\nFetched {len(articles)} articles:\n")
    for a in articles[:5]:
        print(f"  - {a['titulo'][:80]}...")
        print(f"    {a['publicacao']} | PMID:{a['pmid']}")
        print()
