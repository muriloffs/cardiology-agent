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
 * Encoding note: we use encodeURIComponent() directly (not URLSearchParams)
 * because Things parses newlines as `%0A`. URLSearchParams encodes spaces as
 * `+` (form-style), which most browsers handle correctly, but `encodeURIComponent`
 * is more predictable for non-form contexts like custom URL schemes.
 */

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
 * Token is per-device — get it from: Things → Settings → General → "Enable
 * Things URLs" → Manage → copy "Authorization Token". macOS only.
 *
 * If unset, the pipeline still works fully for `add`. Token is null-safe.
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
    // Things expects checklist items separated by newlines in this single param
    const checklistStr = checklist.join('\n')
    parts.push(`checklist-items=${encodeURIComponent(checklistStr)}`)
  }
  parts.push(`tags=${encodeURIComponent(THINGS_TAG)}`)
  if (THINGS_LIST) parts.push(`list=${encodeURIComponent(THINGS_LIST)}`)
  if (THINGS_AUTH_TOKEN) parts.push(`auth-token=${encodeURIComponent(THINGS_AUTH_TOKEN)}`)
  return `things:///add?${parts.join('&')}`
}

// =============================================================================
// Per-type content builders
// =============================================================================

/**
 * Build notes body + checklist for a given item type. Returns:
 *   { notes: string, checklist: string[] }
 *
 * Strategy: dense text in notes (with section dividers) + actionable items
 * extracted as checklist (so user can tick off as they read).
 */
function buildContent(item, type) {
  const lines = []
  const checklist = []
  const url = (
    item?.links?.url ||
    item?.links?.episode_url ||
    item?.links?.post_url ||
    item?.video_url ||
    item?.url ||
    ''
  )
  const source = item?.publicacao || item?.canal || item?.autor || ''

  if (type === 'artigo') {
    lines.push(`Fonte: ${source}`)
    if (item.classe) lines.push(`Classe ${item.classe} · Score ${item.score}/10`)
    lines.push('')
    lines.push('=== CONTEXTO CLÍNICO ===')
    if (item.contexto_clinico) lines.push(item.contexto_clinico)
    lines.push('')
    lines.push('=== PERGUNTA PRINCIPAL ===')
    if (item.pergunta_principal) lines.push(item.pergunta_principal)
    lines.push('')
    if (item.desenho_estudo && typeof item.desenho_estudo === 'object') {
      lines.push('=== DESENHO DO ESTUDO ===')
      const d = item.desenho_estudo
      const labels = { tipo: 'Tipo', populacao: 'População', n: 'N',
                       intervencao: 'Intervenção', comparador: 'Comparador',
                       seguimento: 'Seguimento' }
      for (const key of Object.keys(labels)) {
        if (d[key]) lines.push(`${labels[key]}: ${d[key]}`)
      }
      lines.push('')
    }
    if (item.principais_resultados) {
      lines.push('=== PRINCIPAIS RESULTADOS ===')
      lines.push(item.principais_resultados)
      lines.push('')
    }
    if (item.interpretacao_pratica) {
      lines.push('=== INTERPRETAÇÃO PRÁTICA ===')
      lines.push(item.interpretacao_pratica)
      lines.push('')
    }
    if (item.conclusao_uma_frase) {
      lines.push('=== VEREDITO ===')
      lines.push(item.conclusao_uma_frase)
      lines.push('')
    }
    // Pontos-chave viram CHECKLIST (clicáveis no Things)
    if (Array.isArray(item.pontos_chave) && item.pontos_chave.length) {
      checklist.push(...item.pontos_chave)
    }
    // Limitações também viram checklist (para "revisar com mente crítica")
    if (Array.isArray(item.limitacoes) && item.limitacoes.length) {
      for (const l of item.limitacoes) checklist.push(`⚠️ Limitação: ${l}`)
    }
  } else if (type === 'noticia') {
    lines.push(`Fonte: ${source}`)
    if (item.classe) lines.push(`Classe ${item.classe} · Score ${item.score}/10`)
    lines.push('')
    if (item.contexto) {
      lines.push('=== CONTEXTO ===')
      lines.push(item.contexto)
      lines.push('')
    }
    if (item.insights) {
      lines.push('=== INSIGHTS ===')
      lines.push(item.insights)
      lines.push('')
    }
    if (item.por_que_importa) {
      lines.push('=== POR QUE IMPORTA ===')
      lines.push(item.por_que_importa)
      lines.push('')
    }
    if (Array.isArray(item.pontos_principais) && item.pontos_principais.length) {
      checklist.push(...item.pontos_principais)
    }
    if (Array.isArray(item.falas) && item.falas.length) {
      for (const f of item.falas) checklist.push(`💬 ${f}`)
    }
    if (!item.contexto && item.resumo) {
      lines.push(item.resumo)
      lines.push('')
    }
  } else if (type === 'pulso') {
    lines.push(item.is_destaque_do_dia ? '★ DESTAQUE DO DIA' : 'Pulso do Dia')
    if (item.classe) lines.push(`Classe ${item.classe} · Score ${item.score}/10`)
    lines.push('')
    if (item.razao_destaque) {
      lines.push('=== POR QUE IMPORTOU ===')
      lines.push(item.razao_destaque)
      lines.push('')
    }
    if (item.o_que_paper_diz) {
      lines.push('=== O QUE O PAPER DIZ ===')
      lines.push(item.o_que_paper_diz)
      lines.push('')
    }
    if (item.interpretacao_comunidade) {
      lines.push('=== INTERPRETAÇÃO DA COMUNIDADE ===')
      lines.push(item.interpretacao_comunidade)
      lines.push('')
    }
    if (item.o_que_muda) checklist.push(`✅ Muda: ${item.o_que_muda}`)
    if (item.o_que_nao_muda_ainda) checklist.push(`⏸️ Não muda ainda: ${item.o_que_nao_muda_ainda}`)
  } else if (type === 'video') {
    lines.push(`Canal: ${source}`)
    if (item.data_publicacao) lines.push(`Publicado: ${item.data_publicacao}`)
    lines.push('')
    if (item.descricao_preview) {
      lines.push('=== DESCRIÇÃO ===')
      lines.push(item.descricao_preview)
      lines.push('')
    }
  } else if (type === 'discussao') {
    lines.push(`Autor: ${item.autor || source}`)
    if (item.classe) lines.push(`Classe ${item.classe} · Score ${item.score}/10`)
    lines.push('')
    if (item.resumo) {
      lines.push(item.resumo)
      lines.push('')
    }
    if (item.impacto_clinico) {
      lines.push('=== IMPACTO CLÍNICO ===')
      lines.push(item.impacto_clinico)
      lines.push('')
    }
  } else if (type === 'substack') {
    lines.push(`Autor: ${item.autor || source}`)
    if (item.publicacao) lines.push(`Publicação: ${item.publicacao}`)
    lines.push('')
    if (item.resumo) {
      lines.push(item.resumo)
      lines.push('')
    }
    if (Array.isArray(item.bullets) && item.bullets.length) {
      checklist.push(...item.bullets)
    }
    if (item.quem_se_aplica) lines.push(`👥 Para quem: ${item.quem_se_aplica}`)
    if (item.evidencia_chave) lines.push(`📊 Evidência: ${item.evidencia_chave}`)
    if (item.contraponto) lines.push(`⚠️ Contraponto: ${item.contraponto}`)
    if (item.quem_se_aplica || item.evidencia_chave || item.contraponto) lines.push('')
  }

  if (url) {
    lines.push('=== LINK ===')
    lines.push(url)
  }

  let notes = lines.join('\n').trim()
  // Conservative truncation accounting for URL encoding overhead
  if (notes.length > 1900) {
    notes = notes.slice(0, 1880).trimEnd() + '…'
  }
  return { notes, checklist: checklist.slice(0, 20) }
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

  const { notes, checklist } = buildContent(item, type)
  const url = buildThingsUrl({ title, notes, checklist })

  window.location.href = url
  return true
}
