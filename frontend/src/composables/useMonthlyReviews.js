/**
 * "Revisões e Diretrizes do Mês" — acumulador de leitura.
 *
 * Junta todas as revisões/diretrizes publicadas no MÊS CALENDÁRIO ATUAL
 * (varrendo os relatórios daquele mês), para o usuário ter uma fila do que
 * vale baixar e ler na íntegra. "Reseta" no dia 1 do mês seguinte sem apagar
 * nada — é só uma view filtrada por mês; o histórico permanece.
 *
 * Lazy-load: só busca os relatórios quando a aba é aberta. Singleton.
 */
import { ref, computed } from 'vue'
import { fetchIndex, fetchReportByDate } from '../utils/api'

// Mesma deteção do selo no ArticleCard / do briefing de áudio.
function isReviewOrGuideline(article) {
  const t = (article?.desenho_estudo?.tipo || '').toLowerCase()
  if (!t) return false
  return /revis(ã|a)o\b|\breview\b|estado da arte|state[\s\-.]of[\s\-.]the[\s\-.]art|diretriz|consenso|guideline|statement|posicionamento/.test(t)
}

function classifyTipo(article) {
  const t = (article?.desenho_estudo?.tipo || '').toLowerCase()
  if (/diretriz|consenso|guideline|statement|posicionamento/.test(t)) return 'diretriz'
  return 'revisao'
}

const loading = ref(false)
const loaded = ref(false)
const loadError = ref(null)
const items = ref([])       // [{ date, article, tipo }]
const currentMonth = ref('') // 'YYYY-MM'

function monthLabel(ym) {
  if (!ym) return ''
  try {
    const [y, m] = ym.split('-').map(Number)
    const dt = new Date(y, m - 1, 1)
    const nome = dt.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' })
    return nome.charAt(0).toUpperCase() + nome.slice(1)
  } catch {
    return ym
  }
}

async function loadMonth(force = false) {
  // Recarrega se o mês virou desde o último load (caso a aba fique aberta)
  const now = new Date()
  const ym = now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0')
  if (!force && loaded.value && currentMonth.value === ym) return
  if (loading.value) return

  loading.value = true
  loadError.value = null
  currentMonth.value = ym
  try {
    const dates = await fetchIndex()
    const monthDates = dates.filter((d) => d.startsWith(ym))
    const results = await Promise.allSettled(
      monthDates.map((d) => fetchReportByDate(d).then((r) => [d, r]))
    )
    const collected = []
    const seen = new Set()
    for (const r of results) {
      if (r.status !== 'fulfilled') continue
      const [date, report] = r.value
      for (const a of report.artigos || []) {
        if (!isReviewOrGuideline(a)) continue
        // Dedupe: mesmo paper pode reaparecer em dias diferentes
        const key = a.links?.pubmed || a.links?.doi || (a.titulo || '').slice(0, 80)
        if (seen.has(key)) continue
        seen.add(key)
        collected.push({ date, article: a, tipo: classifyTipo(a) })
      }
    }
    collected.sort((x, y) => y.date.localeCompare(x.date)) // mais recente primeiro
    items.value = collected
    loaded.value = true
  } catch (e) {
    loadError.value = e?.message || 'Falha ao carregar o mês'
    console.error('useMonthlyReviews loadMonth failed:', e)
  } finally {
    loading.value = false
  }
}

export function useMonthlyReviews() {
  const byTema = computed(() => {
    const g = {}
    for (const it of items.value) {
      const t = it.article.tema_principal || 'Outros temas'
      ;(g[t] = g[t] || []).push(it)
    }
    return g
  })

  const temas = computed(() =>
    Object.entries(byTema.value)
      .map(([tema, arr]) => ({ tema, count: arr.length }))
      .sort((a, b) => b.count - a.count)
  )

  const counts = computed(() => ({
    total: items.value.length,
    revisoes: items.value.filter((i) => i.tipo === 'revisao').length,
    diretrizes: items.value.filter((i) => i.tipo === 'diretriz').length,
  }))

  return {
    loading,
    loaded,
    loadError,
    items,
    currentMonth,
    monthLabelText: computed(() => monthLabel(currentMonth.value)),
    byTema,
    temas,
    counts,
    loadMonth,
  }
}
