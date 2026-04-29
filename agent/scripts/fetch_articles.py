"""Fetch real cardiology articles from PubMed — filtered by the curated journal list."""

import time
import logging
import requests
from typing import Any

logger = logging.getLogger(__name__)

PUBMED_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# Exact journals from the curated list, mapped to their PubMed standard names.
# Journals not indexed in PubMed (Medscape, CardioSource, ACC News) are omitted.
CARDIOLOGY_JOURNALS = [
    "Nat Rev Cardiol",                  # Nature Reviews Cardiology
    "Circulation",                      # Circulation
    "J Am Coll Cardiol",               # JACC
    "JACC Cardiovasc Interv",          # JACC: Cardiovascular Interventions
    "JACC Heart Fail",                 # JACC: Heart Failure
    "JACC Cardiovasc Imaging",         # JACC: Cardiovascular Imaging
    "Lancet Cardiol",                   # The Lancet Cardiology
    "Eur Heart J",                      # European Heart Journal
    "Cardiovasc Res",                   # Cardiovascular Research
    "Am Heart J",                       # American Heart Journal
    "Heart Fail Rev",                   # Heart Failure Reviews
    "J Card Surg",                      # Journal of Cardiac Surgery
    "Atherosclerosis",                  # Atherosclerosis
    "Hypertension",                     # Hypertension
    "Arterioscler Thromb Vasc Biol",   # ATVB
    "Stroke",                           # Stroke
    "Circ Arrhythm Electrophysiol",    # Circulation: Arrhythmia and Electrophysiology
    "Circ Heart Fail",                  # Circulation: Heart Failure
    "Circ Cardiovasc Qual Outcomes",   # Circulation: Cardiovascular Quality and Outcomes
    "Circ Genom Precis Med",           # Circulation: Genomic and Precision Medicine
    "Circ Res",                         # Circulation Research
    "Circ Cardiovasc Imaging",         # Circulation: Cardiovascular Imaging
    "Circ Cardiovasc Interv",          # Circulation: Cardiovascular Interventions
    "Am J Cardiol",                     # American Journal of Cardiology
    "Can J Cardiol",                    # Canadian Journal of Cardiology
    "Eur J Heart Fail",                # European Journal of Heart Failure
    "Int J Cardiol",                    # International Journal of Cardiology
    "J Cardiovasc Magn Reson",         # Journal of Cardiovascular Magnetic Resonance
    "J Am Soc Echocardiogr",           # Journal of the American Society of Echocardiography
    "Catheter Cardiovasc Interv",      # Catheterization and Cardiovascular Interventions
    "J Interv Cardiol",                # Journal of Interventional Cardiology
    "Pacing Clin Electrophysiol",      # Pacing and Clinical Electrophysiology
    "Heart Rhythm",                     # Heart Rhythm
    "Heart Rhythm O2",                  # Heart Rhythm O2
    "Hypertens Res",                    # Hypertension Research
    "J Hypertens",                      # Journal of Hypertension
    "Blood Press",                      # Blood Pressure
    "J Cardiovasc Pharmacol",          # Journal of Cardiovascular Pharmacology
    "Braz J Cardiovasc Surg",          # Brazilian Journal of Cardiovascular Surgery
    "Arq Bras Cardiol",                # Arquivos Brasileiros de Cardiologia
    "Rev Esp Cardiol",                  # Revista Española de Cardiología
    "ESC Heart Fail",                   # ESC Heart Failure
    "Congenit Heart Dis",              # Congenital Heart Disease
    "Pediatr Cardiol",                  # Pediatric Cardiology
    "Curr Cardiol Rev",                # Current Cardiology Reviews
    "Expert Rev Cardiovasc Ther",      # Expert Review of Cardiovascular Therapy
    "Future Cardiol",                   # Future Cardiology
    "Struct Heart",                     # Structural Heart
    "JAMA Cardiol",                     # JAMA Cardiology
]


def _build_journal_query() -> str:
    """Build PubMed OR query from the journal list."""
    parts = [f'"{j}"[Journal]' for j in CARDIOLOGY_JOURNALS]
    return "(" + " OR ".join(parts) + ")"


def search_pubmed(days_back: int = 1, max_results: int = 50) -> list[str]:
    """Search PubMed for recent articles from the curated journal list."""
    journal_query = _build_journal_query()

    params = {
        "db": "pubmed",
        "term": journal_query,
        "datetype": "pdat",
        "reldate": days_back,
        "retmax": max_results,
        "retmode": "json",
        "sort": "relevance",
    }

    try:
        response = requests.get(f"{PUBMED_BASE}/esearch.fcgi", params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
        pmids = data.get("esearchresult", {}).get("idlist", [])
        count = data.get("esearchresult", {}).get("count", "?")
        logger.info(f"PubMed: {count} total matches, fetching top {len(pmids)}")
        return pmids
    except Exception as e:
        logger.error(f"PubMed search failed: {e}")
        return []


def fetch_summaries(pmids: list[str]) -> list[dict[str, Any]]:
    """Fetch title, journal, authors, DOI for each PMID."""
    if not pmids:
        return []

    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "json",
    }

    try:
        response = requests.get(f"{PUBMED_BASE}/esummary.fcgi", params=params, timeout=20)
        response.raise_for_status()
        results = response.json().get("result", {})
    except Exception as e:
        logger.error(f"PubMed summary fetch failed: {e}")
        return []

    time.sleep(0.4)
    abstracts = _fetch_abstracts(pmids)

    articles = []
    for pmid in pmids:
        item = results.get(pmid)
        if not item or item.get("uid") != pmid:
            continue

        authors = [a.get("name", "") for a in item.get("authors", [])[:4]]

        doi = next(
            (x.get("value") for x in item.get("articleids", []) if x.get("idtype") == "doi"),
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

    logger.info(f"Details fetched for {len(articles)} articles")
    return articles


def _fetch_abstracts(pmids: list[str]) -> dict[str, str]:
    """Fetch plain-text abstracts for a list of PMIDs."""
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "rettype": "abstract",
        "retmode": "text",
    }

    try:
        response = requests.get(f"{PUBMED_BASE}/efetch.fcgi", params=params, timeout=25)
        response.raise_for_status()
        raw = response.text
    except Exception as e:
        logger.warning(f"Abstract fetch failed: {e}")
        return {}

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
    Main entry point. Returns real articles from the curated journal list,
    published in the last N days.
    Falls back to 2-day window if today has fewer than 30 results.
    """
    logger.info(f"Searching {len(CARDIOLOGY_JOURNALS)} curated journals — last {days_back} day(s)...")
    pmids = search_pubmed(days_back=days_back, max_results=80)

    if len(pmids) < 30:
        logger.warning(f"Only {len(pmids)} results for {days_back}d. Extending to 2 days.")
        pmids = search_pubmed(days_back=2, max_results=80)

    if not pmids:
        logger.error("No results from curated journals.")
        return []

    time.sleep(0.4)
    return fetch_summaries(pmids)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    articles = fetch_recent_cardiology_articles()
    print(f"\n{len(articles)} articles from curated journals:\n")
    for a in articles:
        print(f"  [{a['publicacao']}] {a['titulo'][:75]}...")
        print(f"    PMID:{a['pmid']} | {a['data_publicacao']}")
        print()
