/**
 * API Route: GET /api/proxy-image?url=...&filename=...
 *
 * Proxies open-access images from PMC (PubMed Central) so the browser can
 * save them directly via Content-Disposition: attachment. Two reasons we
 * cannot just point an <a download> at NCBI directly:
 *
 *   1. NCBI serves images with no Content-Disposition header — the
 *      `download` attribute is ignored on cross-origin responses without it,
 *      so the file opens inline instead of saving.
 *   2. Some browsers strip the suggested filename for cross-origin downloads.
 *
 * Security: we only proxy URLs that match the NCBI/PMC hostnames. Anything
 * else returns 400 — this endpoint must NOT be a generic open proxy.
 */

const https = require('https');
const { URL } = require('url');

const ALLOWED_HOSTS = new Set([
  'www.ncbi.nlm.nih.gov',
  'ncbi.nlm.nih.gov',
  'pmc.ncbi.nlm.nih.gov',
]);

function sanitizeFilename(name) {
  if (!name) return 'figure.jpg';
  // Strip path traversal, control chars, quotes
  const cleaned = String(name).replace(/[\\/\x00-\x1f"']/g, '_').slice(0, 120);
  return cleaned || 'figure.jpg';
}

module.exports = function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');

  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'GET') return res.status(405).json({ error: 'Method not allowed' });

  const rawUrl = req.query?.url;
  if (!rawUrl) return res.status(400).json({ error: 'Missing url param' });

  let parsed;
  try {
    parsed = new URL(rawUrl);
  } catch {
    return res.status(400).json({ error: 'Invalid url' });
  }

  if (parsed.protocol !== 'https:' || !ALLOWED_HOSTS.has(parsed.hostname)) {
    return res.status(400).json({ error: 'Host not allowed' });
  }

  const filename = sanitizeFilename(req.query?.filename);

  https.get(parsed.toString(), (upstream) => {
    if (upstream.statusCode !== 200) {
      return res.status(upstream.statusCode || 502).json({
        error: `Upstream returned ${upstream.statusCode}`,
      });
    }

    const contentType = upstream.headers['content-type'] || 'image/jpeg';
    res.setHeader('Content-Type', contentType);
    res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
    res.setHeader('Cache-Control', 'public, max-age=86400');

    upstream.pipe(res);
  }).on('error', (err) => {
    console.error('proxy-image upstream error:', err);
    res.status(502).json({ error: err.message });
  });
};
