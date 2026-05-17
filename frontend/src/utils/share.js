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
 * Content building is delegated to itemContent.js so that Share and Things
 * send the SAME dense per-type content. The Share button concatenates
 * `notes` + `checklist` into a single text blob (Web Share API only has
 * one text field).
 *
 * Spec: https://developer.mozilla.org/en-US/docs/Web/API/Web_Share_API
 */

import { buildItemContent } from './itemContent.js'

/**
 * Combine notes + checklist into a single text for share sheet apps.
 * (Web Share API doesn't have separate fields for body and checklist.)
 */
function composeShareText({ notes, checklist }) {
  const parts = []
  if (notes) parts.push(notes)
  if (checklist && checklist.length > 0) {
    parts.push('') // blank line separator
    parts.push('=== PONTOS-CHAVE / CHECKLIST ===')
    for (const item of checklist) parts.push(`• ${item}`)
  }
  return parts.join('\n').trim()
}

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
  const content = buildItemContent(item, type)
  const text = composeShareText(content)
  const url = content.url

  // Path 1: Web Share API (iOS/Android/Mac Safari/modern Chrome)
  if (typeof navigator !== 'undefined' && typeof navigator.share === 'function') {
    try {
      const sharePayload = { title }
      if (text) sharePayload.text = text
      if (url && url.startsWith('http')) sharePayload.url = url

      await navigator.share(sharePayload)
      return 'shared'
    } catch (err) {
      if (err && err.name === 'AbortError') return 'cancelled'
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
