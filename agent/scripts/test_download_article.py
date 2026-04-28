"""Tests for article downloader."""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import os
from pathlib import Path

from download_article import ArticleDownloader, download_and_upload


class TestArticleDownloader:
    """Test article downloader functionality."""

    def test_init_creates_downloads_dir(self):
        """Test that downloader creates downloads directory."""
        with patch.dict(os.environ, {'DOWNLOAD_TEMP_DIR': '/tmp/test_downloads'}):
            with patch('download_article.Path.mkdir'):
                downloader = ArticleDownloader()
                assert downloader.downloads_dir == '/tmp/test_downloads'
                assert downloader.headless is True

    def test_init_with_custom_headless(self):
        """Test downloader initialization with custom headless setting."""
        downloader = ArticleDownloader(headless=False)
        assert downloader.headless is False

    @pytest.mark.asyncio
    async def test_find_pdf_link_direct(self):
        """Test finding direct PDF link on page."""
        downloader = ArticleDownloader()

        # Mock page object
        mock_page = AsyncMock()
        mock_pdf_link = AsyncMock()
        mock_pdf_link.get_attribute.return_value = 'https://example.com/article.pdf'

        mock_page.query_selector.return_value = mock_pdf_link

        result = await downloader._find_pdf_link(mock_page)

        assert result == 'https://example.com/article.pdf'

    @pytest.mark.asyncio
    async def test_find_pdf_link_relative_url(self):
        """Test handling relative PDF URLs."""
        downloader = ArticleDownloader()

        mock_page = AsyncMock()
        mock_pdf_link = AsyncMock()
        mock_pdf_link.get_attribute.return_value = '/docs/article.pdf'
        mock_page.url = 'https://example.com/page'
        mock_page.query_selector.return_value = mock_pdf_link

        result = await downloader._find_pdf_link(mock_page)

        assert result == 'https://example.com/docs/article.pdf'

    @pytest.mark.asyncio
    async def test_find_pdf_link_not_found(self):
        """Test when no PDF link is found."""
        downloader = ArticleDownloader()

        mock_page = AsyncMock()
        mock_page.query_selector.return_value = None
        mock_page.query_selector_all.return_value = []

        result = await downloader._find_pdf_link(mock_page)

        assert result is None

    @pytest.mark.asyncio
    async def test_handle_verification_no_challenge(self):
        """Test verification handling when no challenge present."""
        downloader = ArticleDownloader()

        mock_page = AsyncMock()
        mock_page.query_selector.return_value = None
        mock_page.query_selector_all.return_value = []

        # Should not raise exception
        await downloader._handle_verification(mock_page)

    @pytest.mark.asyncio
    async def test_generate_pdf_from_content(self):
        """Test PDF generation from HTML content."""
        downloader = ArticleDownloader()

        mock_page = AsyncMock()
        mock_page.pdf.return_value = b'PDF_CONTENT'

        with patch('builtins.open', create=True) as mock_open:
            with patch('download_article.Path.exists', return_value=True):
                result = await downloader._generate_pdf_from_content(
                    mock_page,
                    'test_001',
                    'Test Article',
                    'https://example.com/article'
                )

                assert 'article-test_001.pdf' in result
                mock_page.pdf.assert_called_once()


class TestDownloadAndUpload:
    """Test download and upload workflow."""

    @pytest.mark.asyncio
    async def test_download_and_upload_missing_pdf(self):
        """Test workflow when PDF download fails."""
        with patch('download_article.ArticleDownloader') as mock_downloader_class:
            with patch('download_article.GoogleDriveClient') as mock_drive_class:
                mock_downloader = AsyncMock()
                mock_downloader.download_article.return_value = None
                mock_downloader_class.return_value = mock_downloader

                result = await download_and_upload('test_001', 'Test', 'https://example.com')

                assert result['success'] is False
                assert 'error' in result

    @pytest.mark.asyncio
    async def test_download_and_upload_success(self):
        """Test successful download and upload."""
        with patch('download_article.ArticleDownloader') as mock_downloader_class:
            with patch('download_article.GoogleDriveClient') as mock_drive_class:
                with patch('download_article.os.remove'):
                    mock_downloader = AsyncMock()
                    mock_downloader.download_article.return_value = '/tmp/article.pdf'
                    mock_downloader_class.return_value = mock_downloader

                    mock_drive = MagicMock()
                    mock_drive.upload_file.return_value = {
                        'file_id': 'file123',
                        'file_name': 'Test Article.pdf',
                        'web_view_link': 'https://drive.google.com/file/d/file123'
                    }
                    mock_drive.upload_metadata.return_value = 'metadata_file_id'
                    mock_drive_class.return_value = mock_drive

                    result = await download_and_upload(
                        'test_001',
                        'Test Article',
                        'https://example.com/article'
                    )

                    assert result['success'] is True
                    assert result['file_id'] == 'file123'
                    assert 'drive_url' in result
                    assert result['titulo'] == 'Test Article'
