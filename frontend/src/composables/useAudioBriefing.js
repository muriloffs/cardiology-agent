/**
 * Gera um documento de texto estruturado a partir do relatório do dia, pronto
 * para colar no NotebookLM como fonte ("criar podcast").
 *
 * Princípio (ver docs/manuais/notebooklm-briefing-manual.md): o documento é
 * CONTEÚDO PURO, sem comandos embutidos. O comando ("público especialista,
 * cubra tudo, etc.") mora separado, na caixa do NotebookLM, e é sempre o mesmo.
 *
 * Estrutura, na ordem que o usuário consome:
 *   1. DESTAQUES DO DIA (Pulso — o que está em evidência)
 *   2. REVISÕES E DIRETRIZES — para ler na íntegra (sinalizadas)
 *   3. ARTIGOS DO DIA — o que é + conclusão, agrupados por tema (patologia)
 *   4. NOTÍCIAS
 */

// Mesma deteção de revisão/diretriz do ArticleCard (selo).
function isReviewOrGuideline(article) {
  const t = (article?.desenho_estudo?.tipo || '').toLowerCase()
  if (!t) return false
  return /revis(ã|a)o\b|\breview\b|estado da arte|state[\s\-.]of[\s\-.]the[\s\-.]art|diretriz|consenso|guideline|statement|posicionamento/.test(t)
}

function formatDateExtenso(dateStr) {
  if (!dateStr) return ''
  try {
    const [y, m, d] = dateStr.split('-').map(Number)
    const dt = new Date(y, m - 1, d)
    return dt.toLocaleDateString('pt-BR', { weekday: 'long', day: '2-digit', month: 'long', year: 'numeric' })
  } catch {
    return dateStr
  }
}

function tituloDe(item) {
  return (item?.titulo_pt || item?.titulo || '').trim()
}

/**
 * Constrói o documento de briefing em texto limpo (sem markdown pesado — o
 * NotebookLM lê melhor texto corrido com seções claras).
 */
export function buildAudioBriefing(report) {
  if (!report) return ''
  const L = []
  const artigos = report.artigos || []

  L.push(`Briefing de Cardiologia — ${formatDateExtenso(report.relatorio_data)}`)
  L.push('')
  L.push(`Resumo do dia: ${artigos.length} artigos, ${(report.noticias || []).length} notícias, ${(report.pulso || []).length} destaques.`)
  L.push('')

  // 1. DESTAQUES (Pulso)
  const pulso = report.pulso || []
  if (pulso.length) {
    L.push('SEÇÃO 1 — DESTAQUES DO DIA (o que está em maior evidência)')
    L.push('')
    pulso.forEach((p, i) => {
      const razao = (p.razao_destaque || p.o_que_paper_diz || '').trim()
      L.push(`${i + 1}. ${tituloDe(p)}.`)
      if (razao) L.push(`   ${razao}`)
    })
    L.push('')
  }

  // 2. REVISÕES E DIRETRIZES (sinalizadas para leitura completa)
  const revisoes = artigos.filter(isReviewOrGuideline)
  if (revisoes.length) {
    L.push('SEÇÃO 2 — REVISÕES E DIRETRIZES PUBLICADAS HOJE (vale baixar e ler na íntegra)')
    L.push('')
    revisoes.forEach((a) => {
      const oque = (a.contexto_clinico || a.resumo || '').trim()
      L.push(`- ${tituloDe(a)} (${a.publicacao || 'fonte'}).`)
      if (oque) L.push(`  Sobre o quê: ${oque}`)
    })
    L.push('')
  }

  // 3. ARTIGOS DO DIA — o que é + conclusão, agrupados por tema
  L.push('SEÇÃO 3 — TODOS OS ARTIGOS DO DIA (o que é + conclusão)')
  L.push('')
  const grupos = new Map()
  for (const a of artigos) {
    const tema = a.tema_principal || 'Outros temas'
    if (!grupos.has(tema)) grupos.set(tema, [])
    grupos.get(tema).push(a)
  }
  // Ordena temas por quantidade (mais artigos primeiro)
  const temasOrdenados = [...grupos.entries()].sort((a, b) => b[1].length - a[1].length)
  for (const [tema, items] of temasOrdenados) {
    L.push(`Tema: ${tema}`)
    for (const a of items) {
      const conclusao = (a.conclusao_uma_frase || a.principais_resultados || a.resumo || '').trim()
      const classe = a.classe ? ` [Classe ${a.classe}]` : ''
      L.push(`- ${tituloDe(a)}${classe}.`)
      if (conclusao) L.push(`  Conclusão: ${conclusao}`)
    }
    L.push('')
  }

  // 4. NOTÍCIAS
  const noticias = report.noticias || []
  if (noticias.length) {
    L.push('SEÇÃO 4 — NOTÍCIAS DO DIA')
    L.push('')
    noticias.forEach((n) => {
      const porque = (n.por_que_importa || n.contexto || n.resumo || '').trim()
      L.push(`- ${tituloDe(n)} (${n.publicacao || 'fonte'}).`)
      if (porque) L.push(`  ${porque}`)
    })
    L.push('')
  }

  L.push('Fim do briefing.')
  return L.join('\n')
}

/**
 * Copia o briefing pro clipboard. Retorna {ok, chars} para feedback na UI.
 * Usa a Clipboard API (precisa de https + gesto do usuário — ok no dashboard).
 */
export async function copyAudioBriefing(report) {
  const text = buildAudioBriefing(report)
  if (!text) return { ok: false, chars: 0 }
  try {
    await navigator.clipboard.writeText(text)
    return { ok: true, chars: text.length }
  } catch (e) {
    // Fallback: textarea temporária + execCommand (browsers antigos / contexto sem permissão)
    try {
      const ta = document.createElement('textarea')
      ta.value = text
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      document.body.appendChild(ta)
      ta.focus()
      ta.select()
      const ok = document.execCommand('copy')
      document.body.removeChild(ta)
      return { ok, chars: text.length }
    } catch {
      return { ok: false, chars: text.length }
    }
  }
}
