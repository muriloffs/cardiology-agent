"""CardologyAgent: Autonomous daily cardiology research agent with Claude API integration."""

import json
import logging
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from anthropic import Anthropic, APIError
from agent.parser import parse_report, ParsingError
from agent.scripts.fetch_articles import fetch_recent_cardiology_articles
from agent.scripts.fetch_rss import fetch_all_rss
from agent.scripts.fetch_grok import fetch_x_cardiology_posts, transform_to_discussoes_x
from agent.scripts.fetch_podcasts import fetch_all_podcasts
from agent.scripts.fetch_youtube import fetch_all_youtube, transform_to_videos_youtube
from agent.scripts.fetch_youtube_gemini import fetch_all_youtube_gemini
from agent.scripts.fetch_youtube_data_api import fetch_all_youtube_data_api
from agent.scripts.fetch_gemini_external import fetch_all_external, enrich_news_batch
from agent.scripts.fetch_gemini_substacks import fetch_all_substacks
from agent.scripts.youtube_enrichment import enrich_videos
from agent.scripts.generate_post_ideas import generate_post_ideas
from agent.scripts.generate_pulso import generate_pulso


# Configure logging for GitHub Actions diagnostics
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _select_youtube_fetcher():
    """Pick the YouTube fetcher based on env vars + key availability.

    Priority:
      1. YouTube Data API v3 (default) — requires YOUTUBE_API_KEY or GOOGLE_API_KEY
         with YouTube Data API v3 enabled. Most reliable.
      2. Gemini Search grounding (USE_YT_GEMINI=1 overrides default).
      3. RSS scraping (USE_YT_RSS=1) — only useful in local testing.
    """
    use_rss = os.environ.get("USE_YT_RSS", "").lower() in ("1", "true", "yes")
    if use_rss:
        logger.info("YouTube fetcher: RSS (USE_YT_RSS=1)")
        return fetch_all_youtube

    use_gemini = os.environ.get("USE_YT_GEMINI", "").lower() in ("1", "true", "yes")
    if use_gemini:
        logger.info("YouTube fetcher: Gemini Search (USE_YT_GEMINI=1)")
        return fetch_all_youtube_gemini

    use_data_api = os.environ.get("USE_YT_DATA_API", "1").lower() in ("1", "true", "yes")
    if use_data_api:
        logger.info("YouTube fetcher: Data API v3 (default)")
        return fetch_all_youtube_data_api

    logger.info("YouTube fetcher: RSS fallback (no env flag set)")
    return fetch_all_youtube


class CardologyAgent:
    """Autonomous agent for daily cardiology research with Claude API integration."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        """
        Initialize CardologyAgent with Anthropic client.

        Args:
            api_key: Anthropic API key. If None, uses ANTHROPIC_API_KEY environment variable.

        Raises:
            ValueError: If API key is not provided and not set in environment.
        """
        if api_key is None:
            api_key = os.environ.get('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not set")

        # max_retries=3 covers 429 rate-limits, 5xx server errors, and 529 overloaded
        # with exponential backoff (Anthropic SDK default behavior).
        self.client = Anthropic(api_key=api_key, max_retries=3)
        logger.info("CardologyAgent initialized successfully")

    def research_daily(self, report_date: str) -> Dict[str, Any]:
        """
        Fetch real articles from PubMed, then use Claude to classify and curate them.

        Args:
            report_date: Date string in YYYY-MM-DD format for the report.

        Returns:
            Validated report dictionary with articles, featured items, and metadata.

        Raises:
            ParsingError: If Claude response cannot be parsed or validated.
            APIError: If Claude API call fails.
            FileNotFoundError: If prompt.txt is not found.
        """
        # Fetch all 7 sources in parallel — independent I/O, capped by slowest.
        # Each fetcher is internally fault-tolerant and returns [] / {} on failure.
        # Gemini-based fetchers graceful-degrade if GOOGLE_API_KEY not set.
        logger.info("Fetching from all sources in parallel (PubMed, RSS, Grok, Podcasts, YouTube, GeminiNews, GeminiSubstacks)...")
        with ThreadPoolExecutor(max_workers=7) as executor:
            futures = {
                "PubMed": executor.submit(fetch_recent_cardiology_articles, days_back=1),
                # RSS/Gemini news feeds podem publicar em ritmo lento — janela de 3 dias
                # cobre items publicados late-night antes do cutoff. Dedup por URL evita repetição.
                "RSS": executor.submit(fetch_all_rss, days_back=3),
                "Grok/X": executor.submit(fetch_x_cardiology_posts, days_back=1),
                "Podcasts": executor.submit(fetch_all_podcasts, days_back=7),
                # YouTube fetcher selection (priority order):
                #   1. YouTube Data API v3 (official, default since 2026-05-12) —
                #      most reliable, $0 within quota, structured metadata.
                #      Set USE_YT_DATA_API=0 to disable and fall through.
                #   2. Gemini Search grounding (USE_YT_GEMINI=1) — fallback if
                #      Data API unavailable. Note: empirically poor recall
                #      (~3% in 2026-05-12 test) — Search doesn't list channel uploads well.
                #   3. RSS direct (fetch_all_youtube) — blocked on GitHub Actions IPs.
                "YouTube": executor.submit(
                    _select_youtube_fetcher(),
                    days_back=3,
                ),
                "GeminiExternal": executor.submit(fetch_all_external, days_back=3),
                "GeminiSubstacks": executor.submit(fetch_all_substacks),
            }
            results = {}
            for name, future in futures.items():
                try:
                    results[name] = future.result()
                except Exception as e:
                    logger.error(f"{name} fetcher raised unexpectedly: {e}")
                    # Use sensible empty defaults per type
                    results[name] = {} if name == "GeminiExternal" else []

        pubmed_articles = results["PubMed"]
        rss_articles = results["RSS"]
        grok_articles = results["Grok/X"]
        podcast_episodes = results["Podcasts"]
        youtube_videos = results["YouTube"]

        # Gemini external returns dict {noticias_external, discussoes_bluesky}
        gemini_external = results["GeminiExternal"] or {}
        gemini_noticias = gemini_external.get("noticias_external", [])
        gemini_bluesky = gemini_external.get("discussoes_bluesky", [])

        # Gemini Substacks returns flat list of substack post dicts
        gemini_substacks = results.get("GeminiSubstacks") or []

        # Merge Gemini-discovered articles into RSS articles (deduped by URL)
        existing_urls = {a.get("pubmed_url", "") for a in rss_articles if a.get("pubmed_url")}
        for item in gemini_noticias:
            if item.get("pubmed_url") not in existing_urls:
                rss_articles.append(item)
                existing_urls.add(item.get("pubmed_url", ""))

        logger.info(f"PubMed: {len(pubmed_articles)} articles")
        logger.info(f"RSS (incl. Gemini external): {len(rss_articles)} items "
                    f"({len(gemini_noticias)} from Gemini fetcher)")
        logger.info(f"Grok/X: {len(grok_articles)} posts")
        logger.info(f"Bluesky (Gemini): {len(gemini_bluesky)} posts")
        logger.info(f"Substacks (Gemini): {len(gemini_substacks)} posts")
        logger.info(f"Podcasts: {len(podcast_episodes)} episodes")
        logger.info(f"YouTube: {len(youtube_videos)} videos")

        for a in pubmed_articles:
            a["source_type"] = "pubmed"
        for a in rss_articles:
            a["source_type"] = "rss"
        for a in podcast_episodes:
            a["source_type"] = "podcast"

        # X discussions BYPASS Claude — Grok output is transformed directly into
        # discussoes_x schema and injected into final report. Trades Claude's
        # semantic curation for ~2x more posts and lower API cost.
        direct_discussoes_x = transform_to_discussoes_x(grok_articles)
        logger.info(f"X discussions (direct from Grok, no Claude curation): {len(direct_discussoes_x)} items")

        # YouTube videos also BYPASS Claude — channel descriptions are already
        # curated by source organizations (ESC, ACC, Radcliffe, etc.), so we keep
        # the per-channel ranking intact and inject directly into the final report.
        # Phase 6 enriches with Gemini-generated PT-BR resumo/bullets/tema before injection.
        direct_videos_youtube = transform_to_videos_youtube(youtube_videos)
        if os.environ.get("DISABLE_YT_ENRICHMENT", "").lower() not in ("1", "true", "yes"):
            direct_videos_youtube = enrich_videos(direct_videos_youtube)
        logger.info(f"YouTube videos (direct from RSS, no Claude curation): {len(direct_videos_youtube)} items")

        # Claude only sees PubMed + RSS + Podcasts now
        articles = pubmed_articles + rss_articles + podcast_episodes

        if not articles:
            raise RuntimeError("No articles fetched from any source. Cannot generate report.")

        logger.info(f"Total to Claude (excluding X): {len(articles)} articles from PubMed/RSS/Podcasts")

        # Step 2: Format articles for Claude
        articles_text = self._format_articles_for_claude(articles)

        # Step 3: Load classification prompt
        try:
            prompt_path = Path(__file__).parent / "prompt.txt"
            with open(prompt_path, 'r', encoding='utf-8') as f:
                system_prompt = f.read()
        except FileNotFoundError:
            logger.error(f"Prompt file not found at {prompt_path}")
            raise

        # Step 4: Call Claude to classify (STREAMING to avoid 5-min proxy idle timeout)
        # With ~135 candidates input and 25k+ output tokens, opus-4-7 can take 5-6 min thinking.
        # Non-streaming connections get killed by proxies (RemoteProtocolError observed).
        # Streaming keeps connection active by sending chunks continuously.
        try:
            logger.info(f"Calling Claude API (streaming) to classify {len(articles)} articles for {report_date}")
            user_message = (
                f"Date: {report_date}\n\n"
                f"Here are {len(articles)} real cardiology candidates fetched from PubMed, "
                f"RSS feeds, X/Twitter, and podcast RSS in the last 24-48 hours. "
                f"Classify according to the Priority Rules in the system prompt — "
                f"Classe A items in `artigos` are unconditional:\n\n"
                f"{articles_text}"
            )
            with self.client.messages.stream(
                model="claude-opus-4-7",
                max_tokens=56000,  # 40 artigos com framework 8 seções (~700-900 tok/artigo) + 15 noticias + 10 podcasts
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            ) as stream:
                response = stream.get_final_message()
            usage_str = f"{getattr(response.usage, 'output_tokens', '?')} output tokens" if response.usage else "?"
            logger.info(f"Claude streaming completed: {usage_str}")
        except APIError as e:
            logger.error(f"Claude API error: {e}")
            raise

        # Step 5: Parse response
        try:
            if isinstance(response, dict):
                raw_response = response['content'][0]['text']
            else:
                raw_response = response.content[0].text

            logger.debug(f"Raw response length: {len(raw_response)} characters")
            report = parse_report(raw_response)
            logger.info(f"Report successfully parsed and validated for {report_date}")

            # Inject Grok-direct X discussions (bypass Claude curation)
            if direct_discussoes_x:
                report["discussoes_x"] = direct_discussoes_x
                logger.info(f"Injected {len(direct_discussoes_x)} X discussions directly from Grok (bypass)")

            # Inject YouTube videos (bypass Claude curation — already pre-ranked by tier)
            if direct_videos_youtube:
                report["videos_youtube"] = direct_videos_youtube
                logger.info(f"Injected {len(direct_videos_youtube)} YouTube videos directly (bypass)")

            # Inject Bluesky discussions (bypass — Gemini already extracted)
            if gemini_bluesky:
                report["discussoes_bluesky"] = gemini_bluesky
                logger.info(f"Injected {len(gemini_bluesky)} Bluesky discussions (bypass)")

            # Inject Substack posts (bypass — Gemini already extracted rich content).
            # Pulso/post_ideas can reference these; frontend renders dedicated tab.
            if gemini_substacks:
                report["substacks"] = gemini_substacks
                logger.info(f"Injected {len(gemini_substacks)} Substack posts (bypass)")

            # 2-pass rich news enrichment — Gemini Pro reads each noticia's URL via
            # Google Search grounding and produces 5 Substack-style fields:
            # contexto, pontos_principais, falas, insights, por_que_importa.
            #
            # Runs on report["noticias"] AFTER Claude classified — covers ALL sources
            # (RSS direct: TCTMD/Healio/CardiovascularNews/DAIC/medRxiv AND
            # Gemini external: Medscape/Circulation/EHJ etc.). Previously only ran
            # on Gemini-discovered items, leaving RSS-direct noticias unenriched.
            #
            # Non-critical: graceful degrade on Gemini errors.
            if report.get("noticias") and os.environ.get("DISABLE_NEWS_ENRICHMENT", "").lower() not in ("1", "true", "yes"):
                try:
                    logger.info(f"Enriching {len(report['noticias'])} noticias via Gemini 2-pass (estilo Substack)...")
                    report["noticias"] = enrich_news_batch(report["noticias"])
                except Exception as e:
                    logger.warning(f"News enrichment pass failed: {type(e).__name__}: {e}")

            # Inject original RSS show notes (EN) into each podcast item for the
            # detail modal. Claude rewrites titulo so we match by `publicacao`
            # (show name) — each show has at most 1 episode per run.
            if podcast_episodes and report.get("podcasts"):
                show_notes_by_show = {ep["publicacao"]: ep.get("abstract", "") for ep in podcast_episodes}
                injected = 0
                for p in report["podcasts"]:
                    show_name = p.get("publicacao", "")
                    if show_name in show_notes_by_show and show_notes_by_show[show_name]:
                        p["show_notes_original"] = show_notes_by_show[show_name]
                        injected += 1
                logger.info(f"Injected original RSS show notes into {injected}/{len(report['podcasts'])} podcasts")

            # Generate Pulso do Dia (Sonnet) — 5-10 highlights with multi-source
            # interpretation. Includes Destaque do Dia (Big One) as 1st item.
            # Runs BEFORE post_ideas so post_ideas can leverage Pulso themes if needed.
            # Non-critical: failures degrade gracefully.
            if os.environ.get("DISABLE_PULSO", "").lower() not in ("1", "true", "yes"):
                logger.info("Generating Pulso do Dia (Sonnet 4.6, multi-source synthesis)...")
                pulso_items = generate_pulso(report, anthropic_client=self.client)
                if pulso_items:
                    report["pulso"] = pulso_items
                    logger.info(f"Injected {len(pulso_items)} Pulso highlights")
                else:
                    logger.warning("Pulso generation returned empty — skipping field injection")
            else:
                logger.info("Pulso generation disabled via DISABLE_PULSO env var")

            # Generate Instagram post ideas for lay-audience patients (Sonnet).
            # Non-critical: failures degrade gracefully, returning [] without breaking the report.
            if os.environ.get("DISABLE_POST_IDEAS", "").lower() not in ("1", "true", "yes"):
                logger.info("Generating post ideas (Sonnet 4.6, lay-audience)...")
                post_ideas = generate_post_ideas(report, anthropic_client=self.client)
                if post_ideas:
                    report["post_ideas"] = post_ideas
                    logger.info(f"Injected {len(post_ideas)} post ideas")
                else:
                    logger.warning("Post ideas generation returned empty — skipping field injection")
            else:
                logger.info("Post ideas generation disabled via DISABLE_POST_IDEAS env var")

            return report
        except ParsingError as e:
            logger.error(f"Failed to parse report: {e}")
            logger.debug(f"Raw response: {raw_response[:500]}...")
            raise

    def _format_articles_for_claude(self, articles: list) -> str:
        """Format fetched articles as structured text for Claude classification."""
        lines = []
        for i, a in enumerate(articles, 1):
            source_type = a.get("source_type", "pubmed")
            lines.append(f"--- ARTICLE {i} [source: {source_type}] ---")
            if a.get("pmid"):
                lines.append(f"PMID: {a['pmid']}")
            lines.append(f"Title: {a['titulo']}")
            lines.append(f"Journal/Source: {a['publicacao']}")
            if a.get("autores"):
                lines.append(f"Authors: {', '.join(a['autores'][:4])}")
            if a.get("host"):
                lines.append(f"Host: {a['host']}")
            lines.append(f"Published: {a['data_publicacao']}")
            if a.get("abstract"):
                # PubMed: 1500 chars so Opus can extract pontos_chave (n, HR, IC, p)
                # from full abstract body. Podcasts: 1500 for rich show notes.
                # Other RSS: 800 (news items rarely have granular data beyond headline).
                if source_type == "pubmed":
                    abstract_limit = 1500
                elif source_type == "podcast":
                    abstract_limit = 1500
                else:
                    abstract_limit = 800
                lines.append(f"Show Notes/Abstract: {a['abstract'][:abstract_limit]}")
            url = a.get("pubmed_url") or a.get("episode_url") or ""
            if url:
                lines.append(f"URL: {url}")
            if a.get("audio_url"):
                lines.append(f"Audio URL: {a['audio_url']}")
            if a.get("doi_url"):
                lines.append(f"DOI: {a['doi']}")
                lines.append(f"DOI URL: {a['doi_url']}")
            if a.get("_post_url"):
                lines.append(f"X Post URL: {a['_post_url']}")
            if a.get("_article_url"):
                lines.append(f"Article URL: {a['_article_url']}")
            lines.append("")
        return "\n".join(lines)

    def save_report(self, report: Dict[str, Any], date: str) -> str:
        """
        Save validated report to JSON file.

        Args:
            report: Validated report dictionary.
            date: Date string in YYYY-MM-DD format.

        Returns:
            Full path to the saved file.

        Raises:
            IOError: If file cannot be written.
        """
        try:
            # Create data directory
            data_dir = Path(__file__).parent.parent / "data"
            data_dir.mkdir(exist_ok=True, parents=True)
            logger.debug(f"Data directory ensured: {data_dir}")

            # Generate filename
            file_path = data_dir / f"relatorio-{date}.json"

            # Write JSON file with pretty-printing
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            logger.info(f"Report saved to {file_path}")
            return str(file_path)

        except IOError as e:
            logger.error(f"Failed to save report to {file_path}: {e}")
            raise

    def commit_report(self, file_path: str, date: str) -> str:
        """
        Commit report to git repository.

        Args:
            file_path: Full path to the report file.
            date: Date string in YYYY-MM-DD format.

        Returns:
            Commit SHA hash or status message.
        """
        try:
            logger.info(f"Committing report: {file_path}")

            # Git add
            subprocess.run(
                ['git', 'add', file_path],
                check=True,
                capture_output=True,
                text=True
            )
            logger.debug(f"Git add successful for {file_path}")

            # Git commit
            commit_result = subprocess.run(
                ['git', 'commit', '-m', f"data: add cardiology report for {date}"],
                check=True,
                capture_output=True,
                text=True
            )
            logger.info(f"Git commit successful for {date}")

            # Extract commit hash from output if available
            stdout = commit_result.stdout
            # Handle both bytes and str
            if isinstance(stdout, bytes):
                stdout = stdout.decode('utf-8')

            commit_hash = stdout.split()[-1] if stdout else "committed"
            return commit_hash

        except subprocess.CalledProcessError as e:
            logger.warning(f"Git commit failed: {e.stderr}")
            # Don't raise - report is already saved, git failure is not critical
            return f"git_error: {e.returncode}"

    def run(self, report_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Main execution: research → save → commit.

        Args:
            report_date: Date string in YYYY-MM-DD format. If None, uses today's date (Brasília timezone).

        Returns:
            Validated report dictionary.

        Raises:
            Exception: On research, save, or critical failures.
        """
        try:
            # Determine report date
            if report_date is None:
                # Report covers yesterday's full day of news (runs at 3 AM Brasília)
                brasilia_tz = timezone(timedelta(hours=-3))
                report_date = (datetime.now(brasilia_tz) - timedelta(days=1)).date().isoformat()
                logger.info(f"Using yesterday's date (Brasília): {report_date}")
            else:
                logger.info(f"Using specified report date: {report_date}")

            # Research
            logger.info("Phase 1: Researching...")
            report = self.research_daily(report_date)

            # Save
            logger.info("Phase 2: Saving report...")
            file_path = self.save_report(report, report_date)

            # Commit (best-effort; the workflow has its own fallback commit step)
            logger.info("Phase 3: Committing to git...")
            commit_result = self.commit_report(file_path, report_date)

            # Success — distinguish between actually committed and saved-only
            if isinstance(commit_result, str) and commit_result.startswith("git_error"):
                logger.info(f"✅ Report saved (commit deferred to workflow): {file_path}")
            else:
                logger.info(f"✅ Report generated and committed: {file_path}")
            return report

        except ParsingError as e:
            logger.error(f"Parsing error during run: {e}")
            raise
        except APIError as e:
            logger.error(f"API error during run: {e}")
            raise
        except IOError as e:
            logger.error(f"File I/O error during run: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during run: {e}")
            raise
