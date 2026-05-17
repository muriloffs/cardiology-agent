/**
 * Things 3 (Cultured Code) URL Scheme integration.
 *
 * Things accepts deeplinks of the form:
 *   things:///add?title=X&notes=Y&tags=cardiology&list=Cardiology
 *
 * Works in iOS/iPadOS/macOS where the Things app is installed. On other
 * platforms the link is a no-op.
 *
 * URL Scheme reference: https://culturedcode.com/things/help/url-scheme/
 *
 * IMPORTANT — for `list` to work, the Area/Project named in THINGS_LIST must
 * already exist in your Things database. If it doesn't exist, Things silently
 * falls back to the Inbox. Create it once: in Things, click "+" at the bottom
 * of the sidebar → "New Area" or "New Project" → name it exactly the same as
 * THINGS_LIST below (case-sensitive).
 *
 * Limits in practice:
 *   - title:  ~250 chars before truncation
 *   - notes:  ~2000 chars before truncation
 *   - checklist-items: up to ~25 items, separated by newlines
 *
 * Content building is delegated to itemContent.js so the Share button can
 * reuse the same dense per-type content.
 */

import { buildItemContent } from './itemContent.js'

// =============================================================================
// CONFIGURATION — change these to customize behavior
// =============================================================================

/**
 * Name of the Things list/area/project where items should land.
 * MUST match an existing Area or Project in your Things app exactly.
 * If it doesn't exist, items go to Inbox instead.
 */
const THINGS_LIST = 'Cardiology'

/**
 * Tag automatically applied to every item.
 * MUST exist as a tag in Things (create once: Things → Settings → Tags → +).
 * Lowercase by convention.
 */
const THINGS_TAG = 'cardiology'

/**
 * Optional Things auth-token. Not required for the `add` command (creating new
 * tasks), but recommended if you ever want to programmatically UPDATE those
 * same tasks later (via `update` command, which DOES require auth-token).
 *
 * Set via Vercel env var `VITE_THINGS_AUTH_TOKEN` — NEVER hardcode in this file.
 */
const THINGS_AUTH_TOKEN = import.meta.env.VITE_THINGS_AUTH_TOKEN || ''

// =============================================================================
// URL builder
// =============================================================================

function buildThingsUrl({ title, notes, checklist }) {
  const parts = []
  if (title) parts.push(`title=${encodeURIComponent(title)}`)
  if (notes) parts.push(`notes=${encodeURIComponent(notes)}`)
  if (checklist && checklist.length > 0) {
    const checklistStr = checklist.join('\n')
    parts.push(`checklist-items=${encodeURIComponent(checklistStr)}`)
  }
  parts.push(`tags=${encodeURIComponent(THINGS_TAG)}`)
  if (THINGS_LIST) parts.push(`list=${encodeURIComponent(THINGS_LIST)}`)
  if (THINGS_AUTH_TOKEN) parts.push(`auth-token=${encodeURIComponent(THINGS_AUTH_TOKEN)}`)
  return `things:///add?${parts.join('&')}`
}

// =============================================================================
// Public API
// =============================================================================

/**
 * Open Things with a new task pre-filled.
 *
 * @param {object} item - The card item (artigo, noticia, pulso, etc.)
 * @param {string} type - One of: 'artigo', 'noticia', 'pulso', 'video', 'discussao', 'substack'
 * @returns {boolean} true if a deeplink was actually invoked; false if no title.
 */
export function sendToThings(item, type) {
  if (!item) return false
  const title = (item.titulo || '').trim()
  if (!title) return false

  const { notes, checklist } = buildItemContent(item, type)
  const url = buildThingsUrl({ title, notes, checklist })

  window.location.href = url
  return true
}
