"""One-shot validator: resolves YouTube channel_ids and tests RSS feeds.

Usage:
    python agent/scripts/validate_youtube_channels.py

Reads CANDIDATE_CHANNELS below, prints which work and outputs a Python
list ready to paste into fetch_youtube.py.
"""

import re
import sys
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import feedparser
import requests

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Cookie": "CONSENT=YES+cb.20210328-17-p0.en+FX+999",
}

# Format: (lookup_url_or_handle, display_name, tier, filter_cardio)
# Tier 0 = pinned (CardioPapers, DozeCast — never filtered, never capped hard)
# Tier 1 = core sociedades/journals/eco
# Tier 2 = hospitals/subspecialty
CANDIDATE_CHANNELS = [
    # Tier 0 — Pinned BR (always shown, never filtered, never capped)
    ("https://www.youtube.com/user/Cardiopapers", "Afya CardioPapers", 0, False),
    # NOTE: DozeCast is in the podcasts feed (audio-only), not on YouTube as video — skip here
    # Tier 1 — Sociedades core
    ("https://www.youtube.com/@escardio", "European Society of Cardiology", 1, False),
    ("https://www.youtube.com/@AmericanCollegeofCardiology", "American College of Cardiology", 1, False),
    ("https://www.youtube.com/@american_heart", "American Heart Association", 1, True),
    ("https://www.youtube.com/@CardiolBr", "TV SBC", 1, False),
    ("https://www.youtube.com/@ASE360", "American Society of Echocardiography", 1, False),
    ("https://www.youtube.com/@bsechocardiography", "British Society of Echocardiography", 1, False),
    # Tier 1 — Journals
    ("https://www.youtube.com/@JACC", "JACC Journals", 1, False),
    ("https://www.youtube.com/@circulationaha", "Circulation (AHA)", 1, False),
    ("https://www.youtube.com/@NEJM", "NEJM Group", 1, True),
    # Tier 1 — Discussion/News
    ("https://www.youtube.com/@RadcliffeCardiology", "Radcliffe Cardiology", 1, False),
    ("https://www.youtube.com/@TCTMD", "TCTMD", 1, False),
    ("https://www.youtube.com/@CardioNerds", "CardioNerds", 1, False),
    ("https://www.youtube.com/@medscape", "Medscape", 1, True),
    ("https://www.youtube.com/@CardioSmart", "CardioSmart (ACC patient-ed; mantém para alertas)", 1, True),
    # Tier 1 — BR institutions
    ("https://www.youtube.com/@incorhcfmusp", "InCor HC-FMUSP", 1, True),
    ("https://www.youtube.com/@InstitutoDantePazzanese", "Instituto Dante Pazzanese", 1, True),
    ("https://www.youtube.com/@socesp", "SOCESP", 1, False),
    # Tier 2 — Hospitals (US)
    ("https://www.youtube.com/@MayoClinic", "Mayo Clinic", 2, True),
    ("https://www.youtube.com/@ClevelandClinic", "Cleveland Clinic", 2, True),
    ("https://www.youtube.com/@HoustonMethodistHospital", "Houston Methodist", 2, True),
    ("https://www.youtube.com/@MountSinaiNYC", "Mount Sinai", 2, True),
    # Tier 2 — Subspecialty societies
    ("https://www.youtube.com/@HRSonline", "Heart Rhythm Society", 2, False),
    ("https://www.youtube.com/@HFSAmerica", "Heart Failure Society of America", 2, False),
    ("https://www.youtube.com/@theSCMR", "SCMR", 2, False),
    ("https://www.youtube.com/@SCCT", "SCCT", 2, False),
    ("https://www.youtube.com/@SCAItv", "SCAI", 2, False),
    ("https://www.youtube.com/@PCRonline", "PCR / EuroPCR", 2, False),
    # Tier 2 — BR hospitals
    ("https://www.youtube.com/@HospitalHcor", "HCor", 2, True),
    ("https://www.youtube.com/@SirioLibanes_oficial", "Hospital Sirio-Libanes", 2, True),
    ("https://www.youtube.com/@EinsteinSaude", "Hospital Albert Einstein", 2, True),
    # Tier 2 — University grand rounds
    ("https://www.youtube.com/@UCSFMedicine", "UCSF Medicine", 2, True),
    ("https://www.youtube.com/@YaleMedicine", "Yale Medicine", 2, True),
    ("https://www.youtube.com/@StanfordMedicine", "Stanford Medicine", 2, True),
    ("https://www.youtube.com/@JohnsHopkinsMedicine", "Johns Hopkins Medicine", 2, True),
    ("https://www.youtube.com/@DukeHealth", "Duke Health", 2, True),
]


CHANNEL_ID_REGEXES = [
    # Most reliable: canonical link
    re.compile(r'<link rel="canonical" href="https?://www\.youtube\.com/channel/(UC[A-Za-z0-9_-]{20,24})"'),
    # browseId in ytInitialData payload
    re.compile(r'browseId["\\:]+\s*"(UC[A-Za-z0-9_-]{20,24})"'),
    # Inline JSON channelId
    re.compile(r'"channelId":"(UC[A-Za-z0-9_-]{20,24})"'),
    re.compile(r'"externalId":"(UC[A-Za-z0-9_-]{20,24})"'),
    # Meta tag fallback
    re.compile(r'<meta itemprop="(?:identifier|channelId)" content="(UC[A-Za-z0-9_-]{20,24})"'),
]


def resolve_channel_id(url_or_handle: str) -> Optional[str]:
    """Fetch the channel page and extract the channelId (UCxxx) from HTML."""
    try:
        r = requests.get(url_or_handle, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return None
        for rx in CHANNEL_ID_REGEXES:
            m = rx.search(r.text)
            if m:
                return m.group(1)
        return None
    except Exception as e:
        logger.warning(f"  resolve failed for {url_or_handle}: {e}")
        return None


def test_rss(channel_id: str) -> tuple[bool, int, Optional[str]]:
    """Returns (works, entry_count, latest_title)."""
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        r = requests.get(rss_url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return (False, 0, None)
        feed = feedparser.parse(r.content)
        if not feed.entries:
            return (False, 0, None)
        return (True, len(feed.entries), feed.entries[0].get("title", "")[:60])
    except Exception:
        return (False, 0, None)


def validate_one(candidate):
    url, name, tier, filter_cardio = candidate
    cid = resolve_channel_id(url)
    if not cid:
        return {"name": name, "url": url, "tier": tier, "filter_cardio": filter_cardio,
                "channel_id": None, "status": "RESOLVE_FAIL"}
    works, count, latest = test_rss(cid)
    if not works:
        return {"name": name, "url": url, "tier": tier, "filter_cardio": filter_cardio,
                "channel_id": cid, "status": "RSS_FAIL"}
    return {"name": name, "url": url, "tier": tier, "filter_cardio": filter_cardio,
            "channel_id": cid, "status": "OK", "count": count, "latest": latest}


def main():
    logger.info(f"Validating {len(CANDIDATE_CHANNELS)} candidate channels...\n")
    results = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(validate_one, c): c for c in CANDIDATE_CHANNELS}
        for fut in as_completed(futures):
            res = fut.result()
            results.append(res)
            status = res["status"]
            if status == "OK":
                logger.info(f"  OK   T{res['tier']} {res['name']:<40} ({res['count']} videos) | {res['latest']}")
            elif status == "RSS_FAIL":
                logger.info(f"  FAIL T{res['tier']} {res['name']:<40} channel_id={res['channel_id']} but RSS dead")
            else:
                logger.info(f"  MISS T{res['tier']} {res['name']:<40} could not resolve channel_id")

    ok = [r for r in results if r["status"] == "OK"]
    failed = [r for r in results if r["status"] != "OK"]
    logger.info(f"\n--- Summary: {len(ok)} working / {len(failed)} failed (of {len(results)}) ---")

    # Sort by tier then name for clean output
    ok.sort(key=lambda r: (r["tier"], r["name"].lower()))

    logger.info("\n# === Paste this into fetch_youtube.py ===\n")
    print("YOUTUBE_CHANNELS = [")
    for r in ok:
        flag = "True" if r["filter_cardio"] else "False"
        print(f'    {{"channel_id": "{r["channel_id"]}", "name": "{r["name"]}", "tier": {r["tier"]}, "filter_cardio": {flag}}},')
    print("]")

    if failed:
        print("\n# Failed (need manual lookup or skip):")
        for r in failed:
            print(f"#   {r['name']} ({r['url']}) -> {r['status']}")


if __name__ == "__main__":
    main()
