"""Download articles from URLs using Playwright with paywall bypassing."""

import asyncio
import os
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from playwright.async_api import async_playwright

from google_drive_client import GoogleDriveClient


class ArticleDownloader:
    """Download articles and handle paywall verification."""

    def __init__(self, headless: bool = True):
        """Initialize downloader."""
        self.headless = headless
        self.downloads_dir = os.getenv('DOWNLOAD_TEMP_DIR', '/tmp/downloads')
        Path(self.downloads_dir).mkdir(parents=True, exist_ok=True)

    async def download_article(self, url: str, article_id: str, titulo: str) -> Optional[str]:
        """
        Download article PDF from URL.

        Args:
            url: Article URL
            article_id: Unique article identifier
            titulo: Article title

        Returns:
            Path to downloaded PDF file
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page = await browser.new_page()

            try:
                # Navigate to URL
                await page.goto(url, wait_until='networkidle')

                # Check for verification challenges (paywall, "you are human", etc.)
                await self._handle_verification(page)

                # Try to find and download PDF link
                pdf_link = await self._find_pdf_link(page)
                if pdf_link:
                    pdf_path = await self._download_pdf_from_link(pdf_link, article_id)
                    if pdf_path:
                        return pdf_path

                # Fallback: Extract content and generate PDF
                pdf_path = await self._generate_pdf_from_content(page, article_id, titulo, url)
                return pdf_path

            except Exception as e:
                print(f'Error downloading article {article_id}: {e}')
                return None
            finally:
                await browser.close()

    async def _handle_verification(self, page) -> None:
        """Handle common paywall verification challenges."""
        try:
            # Look for "verify you are human" or CAPTCHA elements
            verify_button = await page.query_selector('[aria-label*="verify"], button:has-text("Verify")')
            if verify_button:
                # Wait for user interaction or timeout
                await asyncio.sleep(2)

            # Check for cookie consent or overlay closers
            close_buttons = await page.query_selector_all('[aria-label*="close"], [class*="close"]')
            for btn in close_buttons[:3]:  # Try first 3 close buttons
                try:
                    await btn.click(timeout=1000)
                except:
                    pass

        except Exception:
            pass  # Continue if verification check fails

    async def _find_pdf_link(self, page) -> Optional[str]:
        """Find direct PDF download link on page."""
        # Look for common PDF link patterns
        pdf_link = await page.query_selector('a[href*=".pdf"]')
        if pdf_link:
            href = await pdf_link.get_attribute('href')
            if href:
                # Handle relative URLs
                if href.startswith('http'):
                    return href
                base_url = page.url.split('/')[2]
                return f"https://{base_url}{href}"

        # Look for download buttons
        download_btn = await page.query_selector('[aria-label*="download"], button:has-text("Download")')
        if download_btn:
            try:
                await download_btn.click()
                await asyncio.sleep(2)
            except:
                pass

        return None

    async def _download_pdf_from_link(self, pdf_url: str, article_id: str) -> Optional[str]:
        """Download PDF from direct link."""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless)
                context = await browser.new_context()
                page = await context.new_page()

                async with page.expect_download() as download_info:
                    await page.goto(pdf_url)

                download = await download_info.value
                pdf_path = os.path.join(self.downloads_dir, f'article-{article_id}.pdf')
                await download.save_as(pdf_path)
                await browser.close()
                return pdf_path if Path(pdf_path).exists() else None
        except Exception:
            return None

    async def _generate_pdf_from_content(self, page, article_id: str, titulo: str, url: str) -> str:
        """Generate PDF from HTML content when direct PDF unavailable."""
        pdf_path = os.path.join(self.downloads_dir, f'article-{article_id}.pdf')

        try:
            # Generate PDF using page.pdf() (Playwright feature)
            pdf_bytes = await page.pdf(format='A4')

            with open(pdf_path, 'wb') as f:
                f.write(pdf_bytes)

            return pdf_path
        except Exception as e:
            print(f'Error generating PDF: {e}')
            return None


async def download_and_upload(article_id: str, titulo: str, url: str) -> Dict[str, Any]:
    """
    Main function: Download article and upload to Google Drive.

    Args:
        article_id: Unique article ID
        titulo: Article title
        url: Article URL

    Returns:
        Dictionary with download status and Drive link
    """
    downloader = ArticleDownloader()
    drive_client = GoogleDriveClient()

    # Download article
    pdf_path = await downloader.download_article(url, article_id, titulo)
    if not pdf_path:
        return {
            'success': False,
            'error': 'Failed to download article PDF'
        }

    # Upload to Google Drive
    try:
        result = drive_client.upload_file(
            pdf_path,
            f'{titulo}.pdf',
            folder_structure=['Cardiology Articles', datetime.now().strftime('%Y-%m')]
        )

        # Upload metadata
        metadata = {
            'article_id': article_id,
            'titulo': titulo,
            'url': url,
            'downloaded_at': datetime.now().isoformat(),
            'file_id': result['file_id']
        }
        drive_client.upload_metadata(metadata, article_id)

        # Clean up temp file
        os.remove(pdf_path)

        return {
            'success': True,
            'file_id': result['file_id'],
            'file_name': result['file_name'],
            'drive_url': result['web_view_link'],
            'titulo': titulo
        }
    except Exception as e:
        print(f'Error uploading to Drive: {e}')
        return {
            'success': False,
            'error': str(e)
        }


if __name__ == '__main__':
    # Test usage
    article_id = 'test_001'
    titulo = 'Test Article'
    url = 'https://example.com/article'

    result = asyncio.run(download_and_upload(article_id, titulo, url))
    print(f'Result: {result}')
