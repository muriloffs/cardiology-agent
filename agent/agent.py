"""CardologyAgent: Autonomous daily cardiology research agent with Claude API integration."""

import json
import logging
import os
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from anthropic import Anthropic, APIError
from agent.parser import parse_report, ParsingError
from agent.scripts.fetch_articles import fetch_recent_cardiology_articles
from agent.scripts.fetch_rss import fetch_all_rss
from agent.scripts.fetch_grok import fetch_x_cardiology_posts


# Configure logging for GitHub Actions diagnostics
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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

        self.client = Anthropic(api_key=api_key)
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
        # Step 1: Fetch real articles from PubMed (curated journals)
        logger.info("Fetching articles from PubMed curated journals...")
        pubmed_articles = fetch_recent_cardiology_articles(days_back=1)
        logger.info(f"PubMed: {len(pubmed_articles)} articles")

        # Step 2: Fetch from RSS feeds (Substacks, news, TCTMD)
        logger.info("Fetching from RSS feeds...")
        rss_articles = fetch_all_rss(days_back=2)
        logger.info(f"RSS: {len(rss_articles)} items")

        # Step 3: Fetch cardiology highlights from X via Grok (optional — requires XAI_API_KEY)
        logger.info("Fetching cardiology highlights from X via Grok...")
        grok_articles = fetch_x_cardiology_posts(days_back=1)
        logger.info(f"Grok/X: {len(grok_articles)} posts")

        for a in pubmed_articles:
            a["source_type"] = "pubmed"
        for a in rss_articles:
            a["source_type"] = "rss"
        for a in grok_articles:
            a["source_type"] = "twitter"

        articles = pubmed_articles + rss_articles + grok_articles

        if not articles:
            raise RuntimeError("No articles fetched from any source. Cannot generate report.")

        logger.info(f"Total: {len(articles)} articles from all sources")

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

        # Step 4: Call Claude to classify
        # Extended output beta allows >8192 tokens — needed for 30 artigos + 15 discussoes_x
        try:
            logger.info(f"Calling Claude API to classify {len(articles)} articles for {report_date}")
            response = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=16000,
                extra_headers={"anthropic-beta": "output-128k-2025-02-19"},
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Date: {report_date}\n\n"
                            f"Here are {len(articles)} real cardiology articles fetched from PubMed, "
                            f"RSS feeds, and X/Twitter in the last 24 hours. Classify and include up to 50 per the instructions:\n\n"
                            f"{articles_text}"
                        )
                    }
                ]
            )
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
            lines.append(f"Published: {a['data_publicacao']}")
            if a.get("abstract"):
                lines.append(f"Abstract: {a['abstract'][:600]}")
            lines.append(f"URL: {a['pubmed_url']}")
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
                # Get current date in Brasília timezone (UTC-3)
                brasilia_tz = timezone(timedelta(hours=-3))
                report_date = datetime.now(brasilia_tz).date().isoformat()
                logger.info(f"Using today's date (Brasília): {report_date}")
            else:
                logger.info(f"Using specified report date: {report_date}")

            # Research
            logger.info("Phase 1: Researching...")
            report = self.research_daily(report_date)

            # Save
            logger.info("Phase 2: Saving report...")
            file_path = self.save_report(report, report_date)

            # Commit
            logger.info("Phase 3: Committing to git...")
            commit_result = self.commit_report(file_path, report_date)

            # Success
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
