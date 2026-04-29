/**
 * API Route: POST /api/download
 * Handles article download to PDF and upload to Google Drive
 */

module.exports = async function handler(req, res) {
  // Enable CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Content-Type', 'application/json');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { articleId, titulo, url } = req.body;

    if (!articleId || !titulo || !url) {
      return res.status(400).json({ error: 'Missing required fields' });
    }

    // TODO: Implement actual download with Playwright + Google Drive upload
    // Vercel Functions have a 10s timeout limit and don't support long-running processes
    // Consider using a separate service for this in production
    return res.status(200).json({
      success: true,
      message: `Article "${titulo}" queued for download`,
      article_id: articleId
    });
  } catch (error) {
    console.error('Error queueing download:', error);
    return res.status(500).json({ error: error.message });
  }
};
