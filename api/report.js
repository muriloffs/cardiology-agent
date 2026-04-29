/**
 * API Route: GET /api/report
 * Returns today's cardiology report data
 */

export default async function handler(req, res) {
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

    // Fetch from raw GitHub URL instead of local filesystem
    // (more reliable in Vercel serverless environment)
    const url = `https://raw.githubusercontent.com/muriloffs/cardiology-agent/main/data/relatorio-${today}.json`;

    const response = await fetch(url);
    if (!response.ok) {
      return res.status(404).json({ error: `No report found for ${today}` });
    }

    const report = await response.json();
    return res.status(200).json(report);
  } catch (error) {
    console.error('Error fetching report:', error);
    return res.status(500).json({ error: error.message });
  }
}
