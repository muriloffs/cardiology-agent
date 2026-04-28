"""Google Drive integration for article uploads."""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any

from google.auth.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


class GoogleDriveClient:
    """Handles authentication and file uploads to Google Drive."""

    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    FOLDER_NAME = 'Cardiology Articles'

    def __init__(self, credentials_path: Optional[str] = None):
        """Initialize Google Drive client with service account credentials."""
        if not credentials_path:
            credentials_path = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')

        if not credentials_path or not Path(credentials_path).exists():
            raise FileNotFoundError(
                f'Google service account credentials not found at {credentials_path}. '
                'Set GOOGLE_SERVICE_ACCOUNT_JSON environment variable.'
            )

        self.credentials_path = credentials_path
        self.service = None
        self.root_folder_id = None
        self._authenticate()

    def _authenticate(self) -> None:
        """Authenticate with Google Drive using service account."""
        credentials = Credentials.from_service_account_file(
            self.credentials_path,
            scopes=self.SCOPES
        )
        self.service = build('drive', 'v3', credentials=credentials)

    def _get_or_create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> str:
        """Get folder ID or create if it doesn't exist."""
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent_id:
            query += f" and parents='{parent_id}'"

        results = self.service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)',
            pageSize=1
        ).execute()

        files = results.get('files', [])
        if files:
            return files[0]['id']

        # Create folder if not found
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            file_metadata['parents'] = [parent_id]

        folder = self.service.files().create(
            body=file_metadata,
            fields='id'
        ).execute()

        return folder.get('id')

    def upload_file(
        self,
        file_path: str,
        file_name: str,
        folder_structure: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Upload file to Google Drive.

        Args:
            file_path: Local file path to upload
            file_name: Name for the file in Drive
            folder_structure: List of folder names to organize file in Drive

        Returns:
            Dictionary with file_id, file_name, and web_view_link
        """
        if not Path(file_path).exists():
            raise FileNotFoundError(f'File not found: {file_path}')

        # Create folder structure if specified
        parent_id = None
        if folder_structure:
            for folder_name in folder_structure:
                parent_id = self._get_or_create_folder(folder_name, parent_id)

        # Upload file
        file_metadata = {'name': file_name}
        if parent_id:
            file_metadata['parents'] = [parent_id]

        media = MediaFileUpload(file_path, resumable=True)
        file = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()

        return {
            'file_id': file.get('id'),
            'file_name': file_name,
            'web_view_link': file.get('webViewLink')
        }

    def upload_metadata(self, metadata: Dict[str, Any], article_id: str) -> Optional[str]:
        """Upload metadata JSON file for an article."""
        import tempfile
        temp_file = os.path.join(tempfile.gettempdir(), f'article-{article_id}-metadata.json')
        with open(temp_file, 'w') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        result = self.upload_file(
            temp_file,
            f'article-{article_id}-metadata.json',
            folder_structure=[self.FOLDER_NAME, 'Metadata']
        )

        os.remove(temp_file)
        return result.get('file_id')
