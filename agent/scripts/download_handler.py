"""HTTP endpoint wrapper for article downloads."""

import asyncio
import json
from typing import Dict, Any
from flask import Flask, request, jsonify

from download_article import download_and_upload

app = Flask(__name__)


@app.route('/api/download', methods=['POST'])
def download_article_endpoint() -> Dict[str, Any]:
    """
    Endpoint to download and upload article to Google Drive.

    Expected JSON body:
    {
        "articleId": "art_001",
        "titulo": "Article Title",
        "url": "https://..."
    }
    """
    try:
        data = request.get_json()

        if not all(k in data for k in ['articleId', 'titulo', 'url']):
            return jsonify({
                'success': False,
                'error': 'Missing required fields: articleId, titulo, url'
            }), 400

        # Run async function in event loop
        result = asyncio.run(download_and_upload(
            data['articleId'],
            data['titulo'],
            data['url']
        ))

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'ok'}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
