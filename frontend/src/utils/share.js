/**
 * Native share integration using the Web Share API.
 *
 * On iOS/iPadOS/macOS/Android: opens the system share sheet — user picks
 * destination (AirDrop, WhatsApp, Mail, Slack, Notion, **NotebookLM** if the
 * app is installed, etc.). The NotebookLM iOS/Mac app registers as a share
 * destination automatically, so a single button covers messaging apps AND
 * sending sources to NotebookLM.
 *
 * On desktop Firefox / older browsers / Chrome without HTTPS in dev:
 * `navigator.share` doesn't exist → fall back to copying a formatted text
 * block to the clipboard (with a toast notification).
 *
 * Spec: https://developer.mozilla.org/en-US/docs/Web/API/Web_Share_API
 */

// =============================================================================
// Per-type share text builder
// =============================================================================

/**
 * Resolve the canonical URL for an item — what NotebookLM/Pocket/etc. will
 * capture as the "source link". Prefers the original publication URL over
 * any internal/derivative link.
 */
function resolveUrl(item, type) {
  if (!item) return ''
  if (type === 'video') return item.video_url || ''
  if (type === 'substack') return item.url || ''
  const links = item.links || {}
  return (
    links.url ||
    links.episode_url ||
    links.post_url ||
    (links.doi ? `https://doi.org/${links.doi}` : '') ||
    (links.pubmed ? `https://pubmed.ncbi.nlm.nih.gov/${links.pubmed}/` : '') ||
    ''
  )
}

/**
 * Build a short share message — title + 1 sentence of context + URL.
 * Kept intentionally compact: WhatsApp/Mail recipients shouldn't get walls
 * of text. For dense content (full framework), Things button is the path.
 */
function buildShareText(item, type) {
  if (!item) return ''
  const lines = []
  const title = (item.titulo || '').trim()
  const source = item?.publicacao || item?.canal || item?.autor || ''

  if (title) lines.push(title)
  if (source) lines.push(`— ${source}`)
  lines.push('')

  // 1 short contextual sentence per type
  const oneliner = (
    item?.conclusao_uma_frase ||
    item?.por_que_importa ||
    item?.razao_destaque ||
    item?.impacto_clinico ||
    item?.resumo ||
    ''
  ).trim()
  if (oneliner) {
    // Keep to ~280 chars (Twitter-friendly)
    lines.push(oneliner.length > 280 ? oneliner.slice(0, 277) + '…' : oneliner)
  }

  return lines.join('\n').trim()
}

// =============================================================================
// Public API
// =============================================================================

/**
 * Share an item via the native Web Share API, or fall back to clipboard.
 *
 * @param {object} item - The card data
 * @param {string} type - 'artigo' | 'noticia' | 'pulso' | 'video' | 'discussao' | 'substack'
 * @returns {Promise<'shared' | 'copied' | 'cancelled' | 'failed'>}
 *   'shared'    — native share sheet succeeded (no toast needed)
 *   'copied'    — clipboard fallback succeeded (show "✓ Copiado!" toast)
 *   'cancelled' — user dismissed the share sheet (no toast)
 *   'failed'    — both paths failed (show error toast)
 */
export async function shareItem(item, type) {
  if (!item) return 'failed'
  const title = (item.titulo || '').trim()
  const text = buildShareText(item, type)
  const url = resolveUrl(item, type)

  // Path 1: Web Share API (iOS/Android/Mac Safari/modern Chrome)
  if (typeof navigator !== 'undefined' && typeof navigator.share === 'function') {
    try {
      // Only include `url` if it's a real http(s) link — Web Share API
      // refuses non-http schemes.
      const sharePayload = { title }
      if (text) sharePayload.text = text
      if (url && url.startsWith('http')) sharePayload.url = url

      await navigator.share(sharePayload)
      return 'shared'
    } catch (err) {
      // User pressed Cancel — not an error
      if (err && err.name === 'AbortError') return 'cancelled'
      // Other errors: try fallback (don't surface to user yet)
      console.warn('navigator.share failed, falling back to clipboard:', err)
    }
  }

  // Path 2: clipboard fallback (desktop Firefox, etc.)
  try {
    const composed = url ? `${text}\n\n${url}` : text
    await navigator.clipboard.writeText(composed)
    return 'copied'
  } catch (err) {
    console.error('Clipboard fallback also failed:', err)
    return 'failed'
  }
}
