/**
 * Shared item-content builder.
 *
 * Returns dense, well-structured representation of any card item, used by:
 *  - things.js (sends as notes + checklist to Things 3 app)
 *  - share.js (sends as single text blob to Web Share API)
 *
 * Strategy: dense narrative text with "=== SECTION ===" dividers + items
 * that fit a "checklist" mental model (pontos-chave, limitações, falas)
 * extracted separately. Caller decides how to combine.
 */

/**
 * @param {object} item - card data
 * @param {string} type - 'artigo' | 'noticia' | 'pulso' | 'video' | 'discussao' | 'substack'
 * @returns {{ notes: string, checklist: string[], url: string }}
 */
export function buildItemContent(item, type) {
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
    if (item.contexto_clinico) {
      lines.push('=== CONTEXTO CLÍNICO ===')
      lines.push(item.contexto_clinico)
      lines.push('')
    }
    if (item.pergunta_principal) {
      lines.push('=== PERGUNTA PRINCIPAL ===')
      lines.push(item.pergunta_principal)
      lines.push('')
    }
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
    if (Array.isArray(item.pontos_chave) && item.pontos_chave.length) {
      checklist.push(...item.pontos_chave)
    }
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
  return { notes, checklist: checklist.slice(0, 20), url }
}
