/**
 * "Revisões e Diretrizes do Mês" — acumulador navegável por mês.
 *
 * Abre sempre no mês CALENDÁRIO atual; permite voltar para meses anteriores
 * (junho, maio...). Conforme os meses passam, o histórico se acumula — nada é
 * apagado, são views filtradas por mês. Cache por mês (voltar é instantâneo).
 *
 * Lazy: carrega o índice + o mês selecionado só ao abrir a aba. Singleton.
 */
import { ref, computed } from 'vue'
import { fetchIndex, fetchReportByDate } from '../utils/api'

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

function monthLabel(ym) {
  if (!ym) return ''
  try {
    const [y, m] = ym.split('-').map(Number)
    const nome = new Date(y, m - 1, 1).toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' })
    return nome.charAt(0).toUpperCase() + nome.slice(1)
  } catch {
    return ym
  }
}

function currentYM() {
  const n = new Date()
  return n.getFullYear() + '-' + String(n.getMonth() + 1).padStart(2, '0')
}

// Estado singleton
const allDates = ref([])            // datas do index.json
const indexLoaded = ref(false)
const selectedMonth = ref('')       // 'YYYY-MM'
const monthCache = ref(new Map())   // ym -> items[]
const loading = ref(false)
const loadError = ref(null)

async function ensureIndex() {
  if (indexLoaded.value) return
  allDates.value = await fetchIndex()
  indexLoaded.value = true
}

function availableMonthsRaw() {
  const set = new Set(allDates.value.map((d) => d.slice(0, 7)))
  return [...set].sort().reverse() // mais recente primeiro
}

async function loadMonth(ym) {
  if (!ym || monthCache.value.has(ym)) return // cache
  loading.value = true
  loadError.value = null
  try {
    await ensureIndex()
    const dates = allDates.value.filter((d) => d.startsWith(ym))
    const results = await Promise.allSettled(
      dates.map((d) => fetchReportByDate(d).then((r) => [d, r]))
    )
    const collected = []
    const seen = new Set()
    for (const r of results) {
      if (r.status !== 'fulfilled') continue
      const [date, report] = r.value
      for (const a of report.artigos || []) {
        if (!isReviewOrGuideline(a)) continue
        const key = a.links?.pubmed || a.links?.doi || (a.titulo || '').slice(0, 80)
        if (seen.has(key)) continue
        seen.add(key)
        collected.push({ date, article: a, tipo: classifyTipo(a) })
      }
    }
    collected.sort((x, y) => y.date.localeCompare(x.date))
    monthCache.value.set(ym, collected)
  } catch (e) {
    loadError.value = e?.message || 'Falha ao carregar o mês'
    console.error('useMonthlyReviews loadMonth failed:', e)
  } finally {
    loading.value = false
  }
}

/** Abre a aba: vai pro mês atual (ou o mais recente com dados) e carrega. */
async function open() {
  await ensureIndex()
  const ym = currentYM()
  const months = availableMonthsRaw()
  selectedMonth.value = months.includes(ym) ? ym : (months[0] || ym)
  await loadMonth(selectedMonth.value)
}

async function goToMonth(ym) {
  if (!ym) return
  selectedMonth.value = ym
  await loadMonth(ym)
}

export function useMonthlyReviews() {
  const items = computed(() => monthCache.value.get(selectedMonth.value) || [])
  const availableMonths = computed(() => availableMonthsRaw())

  // Navegação prev/next pelos meses DISPONÍVEIS (não calendário cego)
  const monthIndex = computed(() => availableMonths.value.indexOf(selectedMonth.value))
  const canOlder = computed(() => monthIndex.value >= 0 && monthIndex.value < availableMonths.value.length - 1)
  const canNewer = computed(() => monthIndex.value > 0)
  async function olderMonth() {
    if (canOlder.value) await goToMonth(availableMonths.value[monthIndex.value + 1])
  }
  async function newerMonth() {
    if (canNewer.value) await goToMonth(availableMonths.value[monthIndex.value - 1])
  }

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
    loadError,
    items,
    selectedMonth,
    availableMonths,
    monthLabelText: computed(() => monthLabel(selectedMonth.value)),
    canOlder,
    canNewer,
    olderMonth,
    newerMonth,
    goToMonth,
    byTema,
    temas,
    counts,
    open,
  }
}
