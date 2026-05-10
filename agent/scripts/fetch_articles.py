"""Fetch real cardiology articles from PubMed — filtered by the curated journal list."""

import os
import time
import logging
import requests
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

PUBMED_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def _ncbi_params(params: dict) -> dict:
    """Add NCBI api_key/tool/email when available — bumps rate limit 3→10 req/s.

    Set NCBI_API_KEY in env (free at ncbi.nlm.nih.gov/account → API Key Management).
    Without the key, our 2nd parallel query hits 429 frequently.
    """
    api_key = os.environ.get("NCBI_API_KEY")
    if api_key:
        params["api_key"] = api_key
    params.setdefault("tool", os.environ.get("NCBI_TOOL", "cardiology-agent"))
    email = os.environ.get("NCBI_EMAIL")
    if email:
        params.setdefault("email", email)
    return params

# Exact journals from the curated list, mapped to their PubMed standard names.
# Journals not indexed in PubMed (Medscape, CardioSource, ACC News) are omitted.
# Publication types that signal high impact — keep regardless of journal
PRIORITY_PUBTYPES = frozenset([
    "Randomized Controlled Trial",
    "Clinical Trial",
    "Clinical Trial, Phase III",
    "Clinical Trial, Phase IV",
    "Practice Guideline",
    "Guideline",
    "Meta-Analysis",
    "Systematic Review",
    "Consensus Development Conference",
    "Multicenter Study",
])

# Publication types that signal low impact — drop unless top-tier journal
JUNK_PUBTYPES = frozenset([
    "Letter",
    "Comment",
    "Editorial",
    "News",
    "Newspaper Article",
    "Published Erratum",
    "Retraction of Publication",
    "Retracted Publication",
    "Biography",
    "Obituary",
])

# Top-tier cardiology journals — always keep, even letters/editorials are noteworthy here
TOP_TIER_JOURNALS = frozenset([
    "Nat Rev Cardiol",
    "Circulation",
    "Eur Heart J",
    "J Am Coll Cardiol",
    "JACC Cardiovasc Interv",
    "JACC Heart Fail",
    "JACC Cardiovasc Imaging",
    "Lancet Cardiol",
    "JAMA Cardiol",
    # Top general medical journals (highest impact factor — landmark trials live here)
    "N Engl J Med",     # NEJM (IF ~176)
    "Lancet",           # Lancet general (IF ~168)
    "JAMA",             # JAMA general (IF ~120)
    "BMJ",              # BMJ general (IF ~105)
    "Ann Intern Med",   # Annals (IF ~40)
    "NEJM Evid",        # NEJM Evidence (curated evidence synthesis)
    "JAMA Intern Med",  # JAMA Internal Medicine (IF ~25, IM clinical practice)
])

# Top general medical journals — fetched via secondary query filtered by cardio MeSH/title
# These don't appear in CARDIOLOGY_JOURNALS because they publish >90% non-cardio content;
# we use a topic filter to extract just their CV papers.
GENERAL_MEDICAL_JOURNALS = [
    "N Engl J Med",
    "JAMA",
    "Lancet",
    "BMJ",
    "Ann Intern Med",
    "NEJM Evid",       # NEJM Evidence (newer 2022, high-quality trials/systematic reviews)
    "JAMA Intern Med", # JAMA Internal Medicine (CV studies in IM context, e.g. TEE-guided CPR)
]

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
    # Added 2026-05: BMJ family + missing JACC sub-journals + EHJ family + prevention
    "Heart",                            # BMJ Heart (also covers former BMJ Heart RSS)
    "Open Heart",                       # Open Heart (BMJ open access)
    "JACC Clin Electrophysiol",         # JACC: Clinical Electrophysiology
    "JACC Basic Transl Sci",            # JACC: Basic to Translational Science
    "JACC Asia",                        # JACC: Asia
    "JACC Adv",                         # JACC: Advances
    "Eur Heart J Open",                 # EHJ Open
    "Eur Heart J Acute Cardiovasc Care",# EHJ Acute Cardiovascular Care
    "Eur Heart J Qual Care Clin Outcomes", # EHJ Quality of Care
    "Eur J Prev Cardiol",               # European Journal of Preventive Cardiology
    # Added 2026-05-07: hypertension + atherosclerosis/lipidology specialty coverage
    "Am J Hypertens",                   # American Journal of Hypertension
    "J Lipid Res",                      # Journal of Lipid Research
    "J Clin Lipidol",                   # Journal of Clinical Lipidology (clinical lipid)
    "Curr Atheroscler Rep",             # Current Atherosclerosis Reports (review-heavy)
    "Curr Hypertens Rep",               # Current Hypertension Reports (review-heavy)
    "J Atheroscler Thromb",             # Journal of Atherosclerosis and Thrombosis (Japan)
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
        response = requests.get(f"{PUBMED_BASE}/esearch.fcgi", params=_ncbi_params(params), timeout=20)
        response.raise_for_status()
        data = response.json()
        pmids = data.get("esearchresult", {}).get("idlist", [])
        count = data.get("esearchresult", {}).get("count", "?")
        logger.info(f"PubMed (cardio journals): {count} total matches, fetching top {len(pmids)}")
        return pmids
    except Exception as e:
        logger.error(f"PubMed search (cardio journals) failed: {e}")
        return []


def search_general_journals_for_cardio(days_back: int = 1, max_results: int = 50) -> list[str]:
    """
    Secondary query: cardiology content published in top general medical journals
    (NEJM, JAMA, Lancet, BMJ, Annals). Catches landmark trials that often appear
    in general journals rather than cardio sub-publications.

    Strategy: filter by journal AND (cardiovascular MeSH OR cardio keywords in title)
    """
    journals_clause = " OR ".join(f'"{j}"[Journal]' for j in GENERAL_MEDICAL_JOURNALS)
    cardio_clause = (
        '"Cardiovascular Diseases"[MeSH] OR '
        'cardiac[Title] OR cardiovascular[Title] OR heart[Title] OR coronary[Title] OR '
        'atrial[Title] OR ventricular[Title] OR myocardial[Title] OR aortic[Title]'
    )
    query = f"({journals_clause}) AND ({cardio_clause})"

    params = {
        "db": "pubmed",
        "term": query,
        "datetype": "pdat",
        "reldate": days_back,
        "retmax": max_results,
        "retmode": "json",
        "sort": "relevance",
    }

    try:
        response = requests.get(f"{PUBMED_BASE}/esearch.fcgi", params=_ncbi_params(params), timeout=20)
        response.raise_for_status()
        data = response.json()
        pmids = data.get("esearchresult", {}).get("idlist", [])
        count = data.get("esearchresult", {}).get("count", "?")
        logger.info(f"PubMed (general+cardio): {count} total matches, fetching top {len(pmids)}")
        return pmids
    except Exception as e:
        logger.error(f"PubMed search (general+cardio) failed: {e}")
        return []


def _fetch_esummary_with_retry(params: dict, n_pmids: int, max_attempts: int = 3) -> dict:
    """Call esummary.fcgi with retries when NCBI returns empty result.

    Strategy:
    - Attempt 1: GET with api_key
    - Attempt 2: POST (NCBI's recommended method for larger id lists)
    - Attempt 3: GET again after longer delay
    Returns the 'result' dict from NCBI, or {} if all attempts fail.
    """
    url = f"{PUBMED_BASE}/esummary.fcgi"
    full_params = _ncbi_params(params.copy())

    for attempt in range(1, max_attempts + 1):
        try:
            if attempt == 2:
                # POST is NCBI's recommended method for large id lists
                response = requests.post(url, data=full_params, timeout=25)
            else:
                response = requests.get(url, params=full_params, timeout=25)
            response.raise_for_status()
            data = response.json()
            results = data.get("result", {})
            uids = results.get("uids", [])
            if uids:
                if attempt > 1:
                    logger.info(f"esummary recovered on attempt {attempt} ({len(uids)}/{n_pmids} PMIDs)")
                return results
            # 200 OK but empty — log diagnostic and retry
            error_msg = data.get("error") or data.get("esummaryresult", "no error key")
            logger.warning(
                f"esummary attempt {attempt}/{max_attempts}: empty result for {n_pmids} PMIDs "
                f"(server response had keys={list(data.keys())[:5]}, error='{error_msg}')"
            )
        except Exception as e:
            logger.warning(f"esummary attempt {attempt}/{max_attempts} failed: {type(e).__name__}: {e}")
        if attempt < max_attempts:
            time.sleep(1.5 * attempt)  # 1.5s, 3s

    logger.error(f"esummary exhausted {max_attempts} attempts — returning empty (will degrade gracefully)")
    return {}


def fetch_summaries(pmids: list[str]) -> list[dict[str, Any]]:
    """Fetch title, journal, authors, DOI for each PMID.

    NCBI esummary endpoint occasionally returns HTTP 200 with empty `result`
    even for valid PMIDs (server-side flakiness, intermittent). Retry once
    after a short delay; switch to POST on retry (NCBI's recommendation for
    larger PMID lists, less likely to hit transient GET issues).
    """
    if not pmids:
        return []

    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "json",
    }

    results = _fetch_esummary_with_retry(params, n_pmids=len(pmids))

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
            "_journal_short": item.get("source", ""),  # internal: for quality filter
            "_pubtype": list(item.get("pubtype", [])),  # internal: for quality filter
        })

    # Filter out articles older than 60 days (exclude truly stale entries)
    filtered = _filter_by_date(articles, max_days=60)
    logger.info(f"Details fetched for {len(filtered)} articles (filtered {len(articles) - len(filtered)} older than 60 days)")
    return filtered


def _fetch_abstracts(pmids: list[str]) -> dict[str, str]:
    """Fetch plain-text abstracts for a list of PMIDs."""
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "rettype": "abstract",
        "retmode": "text",
    }

    try:
        response = requests.get(f"{PUBMED_BASE}/efetch.fcgi", params=_ncbi_params(params), timeout=25)
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


def _filter_by_date(articles: list, max_days: int = 14) -> list:
    """Remove articles whose publication date is older than max_days."""
    cutoff = datetime.now() - timedelta(days=max_days)
    result = []
    for a in articles:
        pub = a.get("data_publicacao", "")
        parsed = None
        for fmt in ("%Y %b %d", "%Y %b", "%Y"):
            try:
                parsed = datetime.strptime(pub.strip()[:len(fmt) + 2], fmt)
                break
            except ValueError:
                continue
        if parsed is None or parsed >= cutoff:
            result.append(a)
        else:
            logger.debug(f"Skipped old article ({pub}): {a['titulo'][:50]}")
    return result


def _is_high_quality(article: dict) -> bool:
    """
    Apply heuristic filter to keep likely Class A/B candidates and drop low-impact content.

    Rules (in priority order):
    1. Top-tier journal → always keep (even letters can be impactful here)
    2. Has priority pubtype (RCT, Guideline, Meta-Analysis, etc.) → always keep
    3. Has only junk pubtypes (Letter, Editorial, Comment) without priority signal → drop
    4. Otherwise → keep (let Claude decide)
    """
    pubtypes = set(article.get("_pubtype", []))
    journal = article.get("_journal_short", "")

    # Always keep top-tier journals
    if journal in TOP_TIER_JOURNALS:
        return True

    # Always keep articles with priority publication type signals
    if pubtypes & PRIORITY_PUBTYPES:
        return True

    # Drop letters/editorials/comments from non-top-tier journals
    if pubtypes & JUNK_PUBTYPES:
        return False

    # Default: keep — let Claude decide
    return True


def _merge_pmid_lists(*lists: list[str]) -> list[str]:
    """Merge multiple PMID lists, preserving order, deduplicating."""
    seen = set()
    out = []
    for lst in lists:
        for pmid in lst:
            if pmid not in seen:
                seen.add(pmid)
                out.append(pmid)
    return out


def fetch_recent_cardiology_articles(days_back: int = 1) -> list[dict[str, Any]]:
    """
    Main entry point. Combines TWO PubMed queries:
    (a) Curated cardiology journals (47+ specialty journals — most volume)
    (b) Top general medical journals filtered by cardio MeSH/title (NEJM, JAMA,
        Lancet, BMJ, Annals — landmark trials live here, often missed otherwise)

    Strategy:
    1. Fetch from both queries, dedupe PMIDs
    2. Filter aggressively (drop letters/editorials from non-top-tier journals)
    3. Cap final result at 100 to keep Claude prompt reasonable
    Falls back to 2-day window if today has fewer than 30 unique results.
    """
    logger.info(
        f"Searching {len(CARDIOLOGY_JOURNALS)} curated cardio journals "
        f"+ {len(GENERAL_MEDICAL_JOURNALS)} general journals (cardio-filtered) "
        f"— last {days_back} day(s)..."
    )

    pmids_curated = search_pubmed(days_back=days_back, max_results=200)
    pmids_general = search_general_journals_for_cardio(days_back=days_back, max_results=50)
    pmids = _merge_pmid_lists(pmids_curated, pmids_general)
    logger.info(f"PubMed merged: {len(pmids_curated)} curated + {len(pmids_general)} general = {len(pmids)} unique")

    if len(pmids) < 30:
        logger.warning(f"Only {len(pmids)} unique results for {days_back}d. Extending to 2 days.")
        pmids_curated = search_pubmed(days_back=2, max_results=200)
        pmids_general = search_general_journals_for_cardio(days_back=2, max_results=50)
        pmids = _merge_pmid_lists(pmids_curated, pmids_general)
        logger.info(f"PubMed merged (2-day): {len(pmids_curated)} curated + {len(pmids_general)} general = {len(pmids)} unique")

    if not pmids:
        logger.error("No results from any PubMed query.")
        return []

    time.sleep(0.4)
    raw_articles = fetch_summaries(pmids)

    # Quality filter: drop letters/editorials/comments unless from top-tier journal
    filtered = [a for a in raw_articles if _is_high_quality(a)]
    dropped = len(raw_articles) - len(filtered)
    logger.info(f"Quality filter: kept {len(filtered)}, dropped {dropped} (low-impact pubtypes)")

    # Cap at 100 to bound Claude input tokens (relevance-sorted by PubMed)
    if len(filtered) > 100:
        logger.info(f"Capping at top 100 of {len(filtered)} (PubMed relevance order)")
        filtered = filtered[:100]

    return filtered


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    articles = fetch_recent_cardiology_articles()
    print(f"\n{len(articles)} articles from curated journals:\n")
    for a in articles:
        print(f"  [{a['publicacao']}] {a['titulo'][:75]}...")
        print(f"    PMID:{a['pmid']} | {a['data_publicacao']}")
        print()
