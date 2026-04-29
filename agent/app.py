"""Flask app for Cardiology Dashboard API."""

import json
import os
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Get paths relative to this file
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'


@app.route('/api/report', methods=['GET'])
def get_report():
    """Get today's cardiology report."""
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        report_path = DATA_DIR / f'relatorio-{today}.json'

        if not report_path.exists():
            return jsonify({'error': f'No report found for {today}'}), 404

        with open(report_path, 'r', encoding='utf-8') as f:
            report = json.load(f)

        return jsonify(report)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/download', methods=['POST'])
def download_article():
    """Download article as PDF and upload to Google Drive."""
    try:
        data = request.get_json()
        article_id = data.get('articleId')
        titulo = data.get('titulo')
        url = data.get('url')

        if not all([article_id, titulo, url]):
            return jsonify({'error': 'Missing required fields'}), 400

        # For now, just return success
        # TODO: Implement actual download with Playwright + Google Drive upload
        return jsonify({
            'success': True,
            'message': f'Article "{titulo}" downloaded',
            'article_id': article_id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
