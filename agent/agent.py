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
        Generate daily cardiology research report using Claude API.

        Args:
            report_date: Date string in YYYY-MM-DD format for the report.

        Returns:
            Validated report dictionary with articles, featured items, and metadata.

        Raises:
            ParsingError: If Claude response cannot be parsed or validated.
            APIError: If Claude API call fails.
            FileNotFoundError: If prompt.txt is not found.
        """
        # Load system prompt
        try:
            prompt_path = Path(__file__).parent / "prompt.txt"
            with open(prompt_path, 'r', encoding='utf-8') as f:
                system_prompt = f.read()
            logger.debug(f"Loaded system prompt from {prompt_path}")
        except FileNotFoundError:
            logger.error(f"Prompt file not found at {prompt_path}")
            raise

        # Call Claude API
        try:
            logger.info(f"Calling Claude API for report date {report_date}")
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": f"Today's date: {report_date}. Please generate the daily cardiology research report."
                    }
                ]
            )
            logger.debug(f"Claude API response received")
        except APIError as e:
            logger.error(f"Claude API error: {e}")
            raise

        # Extract and parse response
        try:
            # Handle both dict (mock) and object (real API) responses
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
