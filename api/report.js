/**
 * API Route: GET /api/report
 * Returns today's cardiology report data
 */

const https = require('https');

module.exports = function handler(req, res) {
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

  // Get today's date in local timezone, then try current and previous day
  const now = new Date();
  const today = now.getFullYear() + '-' +
                String(now.getMonth() + 1).padStart(2, '0') + '-' +
                String(now.getDate()).padStart(2, '0');

  const url = `https://raw.githubusercontent.com/muriloffs/cardiology-agent/main/data/relatorio-${today}.json`;

  https.get(url, (response) => {
    let data = '';

    if (response.statusCode === 404) {
      return res.status(404).json({ error: `No report found for ${today}` });
    }

    if (response.statusCode !== 200) {
      return res.status(response.statusCode).json({ error: 'Failed to fetch report' });
    }

    response.on('data', (chunk) => {
      data += chunk;
    });

    response.on('end', () => {
      try {
        const report = JSON.parse(data);
        res.status(200).json(report);
      } catch (error) {
        console.error('Error parsing report:', error);
        res.status(500).json({ error: 'Invalid report data' });
      }
    });
  }).on('error', (error) => {
    console.error('Error fetching report:', error);
    res.status(500).json({ error: error.message });
  });
};
