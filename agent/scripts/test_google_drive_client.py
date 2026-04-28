"""Tests for Google Drive client."""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from google_drive_client import GoogleDriveClient


class TestGoogleDriveClient:
    """Test Google Drive client functionality."""

    def test_init_missing_credentials(self):
        """Test initialization fails without credentials file."""
        with patch.dict(os.environ, {'GOOGLE_SERVICE_ACCOUNT_JSON': '/nonexistent/path.json'}):
            with pytest.raises(FileNotFoundError):
                GoogleDriveClient()

    @patch('google_drive_client.Credentials.from_service_account_file')
    @patch('google_drive_client.build')
    def test_init_with_valid_credentials(self, mock_build, mock_creds):
        """Test successful initialization with valid credentials."""
        # Create a temporary credentials file
        import tempfile
        import json

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({'type': 'service_account'}, f)
            temp_path = f.name

        try:
            mock_service = MagicMock()
            mock_build.return_value = mock_service

            with patch.dict(os.environ, {'GOOGLE_SERVICE_ACCOUNT_JSON': temp_path}):
                client = GoogleDriveClient()
                assert client.service == mock_service
                assert client.credentials_path == temp_path
                mock_creds.assert_called_once()
        finally:
            os.unlink(temp_path)

    @patch('google_drive_client.Credentials.from_service_account_file')
    @patch('google_drive_client.build')
    def test_upload_file_missing(self, mock_build, mock_creds):
        """Test upload fails when file doesn't exist."""
        import tempfile
        import json

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({'type': 'service_account'}, f)
            temp_path = f.name

        try:
            mock_build.return_value = MagicMock()

            with patch.dict(os.environ, {'GOOGLE_SERVICE_ACCOUNT_JSON': temp_path}):
                client = GoogleDriveClient()

                with pytest.raises(FileNotFoundError):
                    client.upload_file('/nonexistent/file.pdf', 'test.pdf')
        finally:
            os.unlink(temp_path)

    @patch('google_drive_client.Credentials.from_service_account_file')
    @patch('google_drive_client.build')
    def test_get_or_create_folder_exists(self, mock_build, mock_creds):
        """Test getting existing folder."""
        import tempfile
        import json

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({'type': 'service_account'}, f)
            temp_path = f.name

        try:
            mock_service = MagicMock()
            mock_build.return_value = mock_service

            # Mock the folder list response
            mock_service.files().list().execute.return_value = {
                'files': [{'id': 'folder123', 'name': 'TestFolder'}]
            }

            with patch.dict(os.environ, {'GOOGLE_SERVICE_ACCOUNT_JSON': temp_path}):
                client = GoogleDriveClient()
                folder_id = client._get_or_create_folder('TestFolder')

                assert folder_id == 'folder123'
        finally:
            os.unlink(temp_path)

    @patch('google_drive_client.Credentials.from_service_account_file')
    @patch('google_drive_client.build')
    def test_get_or_create_folder_creates_new(self, mock_build, mock_creds):
        """Test creating new folder when doesn't exist."""
        import tempfile
        import json

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({'type': 'service_account'}, f)
            temp_path = f.name

        try:
            mock_service = MagicMock()
            mock_build.return_value = mock_service

            # Mock empty list (folder doesn't exist)
            mock_service.files().list().execute.return_value = {'files': []}
            # Mock folder creation
            mock_service.files().create().execute.return_value = {'id': 'newfolder456'}

            with patch.dict(os.environ, {'GOOGLE_SERVICE_ACCOUNT_JSON': temp_path}):
                client = GoogleDriveClient()
                folder_id = client._get_or_create_folder('NewFolder')

                assert folder_id == 'newfolder456'
        finally:
            os.unlink(temp_path)
