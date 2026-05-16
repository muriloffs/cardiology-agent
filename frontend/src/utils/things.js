/**
 * Things 3 (Cultured Code) URL Scheme integration.
 *
 * Things accepts deeplinks `things:///add?title=X&notes=Y&tags=cardiology`
 * to create a new task in the Inbox. Works in iOS/iPadOS/macOS where the
 * Things app is installed; on other platforms the link is a no-op.
 *
 * URL Scheme reference: https://culturedcode.com/things/help/url-scheme/
 *
 * Limits observed in practice:
 *   - `title`: ~250 chars before truncation
 *   - `notes`: ~2000 chars before truncation (we send dense framework when possible)
 *   - `tags`: comma-separated, all must already exist in Things (we use a single tag
 *      "cardiology" that user creates once and we reuse forever)
 */

const THINGS_TAG = 'cardiology'

/**
 * Build URL Scheme link from raw fields.
 * Returns a string like "things:///add?title=...&notes=...&tags=cardiology".
 */
function buildThingsUrl({ title, notes }) {
  const params = new URLSearchParams()
  if (title) params.set('title', title)
  if (notes) params.set('notes', notes)
  params.set('tags', THINGS_TAG)
  return `things:///add?${params.toString()}`
}

/**
 * Build "notes" string per item type. Tries to send maximum useful context
 * within the ~2000 char practical limit.
 *
 * For artigos: full 8-section framework (contexto, pergunta, desenho, pontos,
 * resultados, interpretação, limitações, veredito) — allows offline reading.
 *
 * For others: title + summary + source URL (lighter — these are less dense items).
 */
function buildNotes(item, type) {
  const lines = []
  const url = (
    item?.links?.url ||
    item?.links?.episode_url ||
    item?.links?.post_url ||
    item?.video_url ||  // YouTube
    item?.url ||         // Substack
    ''
  )
  const source = item?.publicacao || item?.canal || item?.autor || ''

  if (type === 'artigo') {
    lines.push(`📚 ARTIGO — ${source}`)
    if (item.classe) lines.push(`Classe ${item.classe} · Score ${item.score}/10`)
    lines.push('')
    if (item.contexto_clinico) {
      lines.push('📌 CONTEXTO CLÍNICO')
      lines.push(item.contexto_clinico)
      lines.push('')
    }
    if (item.pergunta_principal) {
      lines.push('❓ PERGUNTA PRINCIPAL')
      lines.push(item.pergunta_principal)
      lines.push('')
    }
    if (item.desenho_estudo && typeof item.desenho_estudo === 'object') {
      lines.push('🔬 DESENHO DO ESTUDO')
      const d = item.desenho_estudo
      const labels = { tipo: 'Tipo', populacao: 'População', n: 'N',
                       intervencao: 'Intervenção', comparador: 'Comparador',
                       seguimento: 'Seguimento' }
      for (const key of Object.keys(labels)) {
        if (d[key]) lines.push(`${labels[key]}: ${d[key]}`)
      }
      lines.push('')
    }
    if (Array.isArray(item.pontos_chave) && item.pontos_chave.length) {
      lines.push('📊 PONTOS-CHAVE')
      for (const p of item.pontos_chave) lines.push(`• ${p}`)
      lines.push('')
    }
    if (item.principais_resultados) {
      lines.push('🎯 PRINCIPAIS RESULTADOS')
      lines.push(item.principais_resultados)
      lines.push('')
    }
    if (item.interpretacao_pratica) {
      lines.push('💡 INTERPRETAÇÃO PRÁTICA')
      lines.push(item.interpretacao_pratica)
      lines.push('')
    }
    if (Array.isArray(item.limitacoes) && item.limitacoes.length) {
      lines.push('⚠️ LIMITAÇÕES')
      for (const l of item.limitacoes) lines.push(`• ${l}`)
      lines.push('')
    }
    if (item.conclusao_uma_frase) {
      lines.push('⚡ VEREDITO')
      lines.push(item.conclusao_uma_frase)
      lines.push('')
    }
  } else if (type === 'noticia') {
    lines.push(`📰 NOTÍCIA — ${source}`)
    if (item.classe) lines.push(`Classe ${item.classe} · Score ${item.score}/10`)
    lines.push('')
    if (item.contexto) {
      lines.push('📍 CONTEXTO')
      lines.push(item.contexto)
      lines.push('')
    }
    if (Array.isArray(item.pontos_principais) && item.pontos_principais.length) {
      lines.push('📋 PONTOS PRINCIPAIS')
      for (const p of item.pontos_principais) lines.push(`• ${p}`)
      lines.push('')
    }
    if (Array.isArray(item.falas) && item.falas.length) {
      lines.push('💬 FALAS')
      for (const f of item.falas) lines.push(`"${f}"`)
      lines.push('')
    }
    if (item.insights) {
      lines.push('💡 INSIGHTS')
      lines.push(item.insights)
      lines.push('')
    }
    if (item.por_que_importa) {
      lines.push('⚡ POR QUE IMPORTA')
      lines.push(item.por_que_importa)
      lines.push('')
    }
    if (item.resumo && !item.contexto) lines.push(item.resumo)
  } else if (type === 'pulso') {
    lines.push(`🌍 PULSO DO DIA${item.is_destaque_do_dia ? ' — DESTAQUE' : ''}`)
    if (item.classe) lines.push(`Classe ${item.classe} · Score ${item.score}/10`)
    lines.push('')
    if (item.razao_destaque) {
      lines.push('POR QUE IMPORTOU')
      lines.push(item.razao_destaque)
      lines.push('')
    }
    if (item.o_que_paper_diz) {
      lines.push('📄 O QUE O PAPER DIZ')
      lines.push(item.o_que_paper_diz)
      lines.push('')
    }
    if (item.interpretacao_comunidade) {
      lines.push('💬 INTERPRETAÇÃO DA COMUNIDADE')
      lines.push(item.interpretacao_comunidade)
      lines.push('')
    }
    if (item.o_que_muda) {
      lines.push('✅ O QUE MUDA')
      lines.push(item.o_que_muda)
      lines.push('')
    }
    if (item.o_que_nao_muda_ainda) {
      lines.push('⏸️ O QUE NÃO MUDA AINDA')
      lines.push(item.o_que_nao_muda_ainda)
      lines.push('')
    }
  } else if (type === 'video') {
    lines.push(`📺 VÍDEO — ${source}`)
    lines.push('')
    if (item.descricao_preview) {
      lines.push(item.descricao_preview)
      lines.push('')
    }
  } else if (type === 'discussao') {
    lines.push(`𝕏 DISCUSSÃO — ${item.autor || source}`)
    if (item.classe) lines.push(`Classe ${item.classe} · Score ${item.score}/10`)
    lines.push('')
    if (item.resumo) {
      lines.push(item.resumo)
      lines.push('')
    }
    if (item.impacto_clinico) {
      lines.push('💡 IMPACTO CLÍNICO')
      lines.push(item.impacto_clinico)
      lines.push('')
    }
  } else if (type === 'substack') {
    lines.push(`📝 SUBSTACK — ${item.autor || source}`)
    lines.push('')
    if (item.resumo) {
      lines.push(item.resumo)
      lines.push('')
    }
    if (Array.isArray(item.bullets) && item.bullets.length) {
      lines.push('PONTOS-CHAVE')
      for (const b of item.bullets) lines.push(`• ${b}`)
      lines.push('')
    }
    if (item.quem_se_aplica) lines.push(`👥 Para quem: ${item.quem_se_aplica}`)
    if (item.evidencia_chave) lines.push(`📊 Evidência: ${item.evidencia_chave}`)
    if (item.contraponto) lines.push(`⚠️ Contraponto: ${item.contraponto}`)
    if (item.quem_se_aplica || item.evidencia_chave || item.contraponto) lines.push('')
  }

  if (url) {
    lines.push(`🔗 ${url}`)
  }

  // Truncate to a safe limit (~1900 to leave room for URL encoding overhead)
  let notes = lines.join('\n').trim()
  if (notes.length > 1900) {
    notes = notes.slice(0, 1880) + '…'
  }
  return notes
}

/**
 * Open Things with a new task pre-filled. Returns true if a deeplink was
 * actually invoked (i.e., title was non-empty); false otherwise.
 *
 * Usage: sendToThings(article, 'artigo')
 */
export function sendToThings(item, type) {
  if (!item) return false
  const title = (item.titulo || '').trim()
  if (!title) return false

  const notes = buildNotes(item, type)
  const url = buildThingsUrl({ title, notes })

  // window.location.href works in all browsers; window.open opens a blank tab
  // briefly on some browsers (annoying UX). location.href is silent.
  window.location.href = url
  return true
}
