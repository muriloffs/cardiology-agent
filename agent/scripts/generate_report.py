#!/usr/bin/env python3
"""Generate daily cardiology research report via GitHub Actions."""

import sys
import logging
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agent.agent import CardologyAgent


def main():
    """Generate report and handle output safely."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    try:
        agent = CardologyAgent()
        report = agent.run()

        # Safely extract and validate report data
        report_date = report.get('relatorio_data', 'unknown')
        total_articles = report.get('resumo', {}).get('total_artigos', 0)
        reading_time = report.get('resumo', {}).get('tempo_leitura_minutos', 0)

        logger.info(f'✓ Report generated successfully: {report_date}')
        logger.info(f'✓ Total articles: {total_articles}')
        logger.info(f'✓ Reading time: {reading_time} minutes')

        return 0

    except Exception as e:
        logger.error(f'✗ Error generating report: {e}', exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
