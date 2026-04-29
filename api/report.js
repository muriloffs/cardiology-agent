/**
 * API Route: GET /api/report
 * Returns today's cardiology report data
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const dataDir = path.join(__dirname, '..', 'data');

export default function handler(req, res) {
  // Enable CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Content-Type', 'application/json');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const today = new Date().toISOString().split('T')[0];
    const reportPath = path.join(dataDir, `relatorio-${today}.json`);

    if (!fs.existsSync(reportPath)) {
      return res.status(404).json({ error: `No report found for ${today}` });
    }

    const data = fs.readFileSync(reportPath, 'utf-8');
    const report = JSON.parse(data);

    return res.status(200).json(report);
  } catch (error) {
    console.error('Error fetching report:', error);
    return res.status(500).json({ error: error.message });
  }
}
