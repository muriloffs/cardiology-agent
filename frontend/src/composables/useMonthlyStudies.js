/**
 * "Estudo do Mes" — biblioteca de materiais de estudo navegavel por mes.
 * Espelha useMonthlyReviews: abre no mes atual, volta para meses anteriores.
 * O index.json ja vem agrupado por mes (por_mes/meses_disponiveis). Singleton.
 */
import { ref, computed } from 'vue'

const GITHUB_RAW = 'https://raw.githubusercontent.com/muriloffs/cardiology-agent/main/data/estudos/index.json'

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
const index = ref(null)            // { por_mes, meses_disponiveis }
const indexLoaded = ref(false)
const selectedMonth = ref('')
const loading = ref(false)
const loadError = ref(null)

async function ensureIndex(force = false) {
  if (indexLoaded.value && !force) return
  loading.value = true
  loadError.value = null
  try {
    const resp = await fetch(`${GITHUB_RAW}?t=${Date.now()}`)
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    index.value = await resp.json()
    indexLoaded.value = true
  } catch (e) {
    loadError.value = e?.message || 'Falha ao carregar indice de estudos'
    index.value = { por_mes: {}, meses_disponiveis: [] }
    console.error('useMonthlyStudies load failed:', e)
  } finally {
    loading.value = false
  }
}

async function open() {
  await ensureIndex()
  const months = index.value?.meses_disponiveis || []
  const ym = currentYM()
  selectedMonth.value = months.includes(ym) ? ym : (months[0] || ym)
}

function goToMonth(ym) {
  if (ym) selectedMonth.value = ym
}

export function useMonthlyStudies() {
  const availableMonths = computed(() => index.value?.meses_disponiveis || [])
  const items = computed(() => (index.value?.por_mes || {})[selectedMonth.value] || [])
  const monthIndex = computed(() => availableMonths.value.indexOf(selectedMonth.value))
  const canOlder = computed(() => monthIndex.value >= 0 && monthIndex.value < availableMonths.value.length - 1)
  const canNewer = computed(() => monthIndex.value > 0)
  function olderMonth() {
    if (canOlder.value) goToMonth(availableMonths.value[monthIndex.value + 1])
  }
  function newerMonth() {
    if (canNewer.value) goToMonth(availableMonths.value[monthIndex.value - 1])
  }
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
    open,
  }
}
