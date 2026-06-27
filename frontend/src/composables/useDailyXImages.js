/**
 * Imagens do X navegáveis por DIA (histórico).
 *
 * Cada dia tem seu arquivo `imagens-x-<data>.json`; `imagens-x-index.json` lista
 * os dias disponíveis (mais recente primeiro). Abre sempre no dia mais recente;
 * navega ◄ ► pelos dias com imagens. Cache por dia (voltar é instantâneo).
 * Lazy + singleton — espelha o estilo de useMonthlyStudies/useXImages.
 */
import { ref, computed } from 'vue'

const RAW_BASE = 'https://raw.githubusercontent.com/muriloffs/cardiology-agent/main/data/'

function dateLabelFmt(d) {
  if (!d) return ''
  try {
    const [y, m, day] = d.split('-').map(Number)
    return new Date(y, m - 1, day).toLocaleDateString('pt-BR', { day: '2-digit', month: 'long', year: 'numeric' })
  } catch {
    return d
  }
}

// estado singleton
const dates = ref([])             // dias disponíveis (mais recente primeiro)
const indexLoaded = ref(false)
const selectedDate = ref('')
const dayCache = ref(new Map())   // data -> payload
const loading = ref(false)
const loadError = ref(null)

async function ensureIndex() {
  if (indexLoaded.value) return
  try {
    const r = await fetch(`${RAW_BASE}imagens-x-index.json?t=${Date.now()}`)
    if (!r.ok) throw new Error(`HTTP ${r.status}`)
    dates.value = (await r.json()).dates || []
  } catch (e) {
    dates.value = []
    console.error('useDailyXImages: índice falhou:', e)
  }
  indexLoaded.value = true
}

async function loadDay(d) {
  if (!d || dayCache.value.has(d)) return
  loading.value = true
  loadError.value = null
  try {
    const r = await fetch(`${RAW_BASE}imagens-x-${d}.json?t=${Date.now()}`)
    if (!r.ok) throw new Error(`HTTP ${r.status}`)
    dayCache.value.set(d, await r.json())
  } catch (e) {
    loadError.value = e?.message || 'Falha ao carregar o dia'
    dayCache.value.set(d, { data: d, total: 0, imagens: [] })
  } finally {
    loading.value = false
  }
}

async function open() {
  await ensureIndex()
  selectedDate.value = dates.value[0] || ''
  if (selectedDate.value) await loadDay(selectedDate.value)
}

async function goToDate(d) {
  if (!d) return
  selectedDate.value = d
  await loadDay(d)
}

export function useDailyXImages() {
  const data = computed(() => dayCache.value.get(selectedDate.value) || null)
  const availableDates = computed(() => dates.value)
  const idx = computed(() => dates.value.indexOf(selectedDate.value))
  // dates em ordem desc: index 0 = mais novo. "dia anterior" (mais antigo) tem
  // index MAIOR; "dia seguinte" (mais novo) tem index MENOR.
  const canPrev = computed(() => idx.value >= 0 && idx.value < dates.value.length - 1)
  const canNext = computed(() => idx.value > 0)
  async function prevDay() { if (canPrev.value) await goToDate(dates.value[idx.value + 1]) }
  async function nextDay() { if (canNext.value) await goToDate(dates.value[idx.value - 1]) }

  return {
    loading,
    loadError,
    data,
    selectedDate,
    availableDates,
    dateLabel: computed(() => dateLabelFmt(selectedDate.value)),
    canPrev,
    canNext,
    prevDay,
    nextDay,
    open,
  }
}
