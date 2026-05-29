/**
 * Full-history text search across all committed reports.
 *
 * Singleton via module-level refs (same pattern as useReader / Pinia-style).
 * The cache lazy-loads: fetch only happens when the user actually focuses the
 * search input — site initial load is not affected.
 *
 * Search semantics:
 *  - Case-insensitive
 *  - Accent-insensitive (Portuguese needs this — "IC", "ic", "Ic" all match;
 *    "isquêmico" matches "isquemico")
 *  - Substring match (no fuzzy / no regex — predictable, fast, no surprises)
 *  - All searchable fields per item are concatenated into one big string and
 *    matched against the (normalized) query — simpler than per-field logic
 *    and order doesn't matter
 *
 * Result shape: { date, type, item, snippet } where `snippet` shows the first
 * ~140 chars around the first match (helps the user see WHY a card matched).
 */
import { computed, ref } from 'vue'
import { fetchIndex, fetchReportByDate } from '../utils/api'

const query = ref('')
const allReports = ref(new Map()) // date -> report JSON
const loading = ref(false)
const loaded = ref(false)
const loadError = ref(null)

// Normalize for accent/case-insensitive comparison.
// NFD decomposes "ê" → "e" + "◌̂"; the regex strips combining diacritics (̀-ͯ).
function normalize(text) {
  if (!text) return ''
  return String(text)
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
}

/**
 * Concatenate all searchable text from one item into a single string.
 * Each card type has its own fields; we list them explicitly here (not via
 * Object.values) because we don't want to match against `_internal` keys,
 * URLs, IDs, dates, etc.
 */
function extractSearchableText(item, type) {
  if (!item) return ''
  const parts = []
  const push = (v) => {
    if (!v) return
    if (Array.isArray(v)) v.forEach(push)
    else if (typeof v === 'string') parts.push(v)
    else if (typeof v === 'object') {
      // For nested objects like desenho_estudo, flatten one level.
      Object.values(v).forEach((vv) => typeof vv === 'string' && parts.push(vv))
    }
  }

  // Common across most types
  push(item.titulo)
  push(item.publicacao)
  push(item.autor)
  push(item.autores)

  switch (type) {
    case 'artigo':
      push(item.contexto_clinico)
      push(item.pergunta_principal)
      push(item.principais_resultados)
      push(item.interpretacao_pratica)
      push(item.conclusao_uma_frase)
      push(item.impacto_clinico) // legado
      push(item.resumo)           // legado
      push(item.pontos_chave)
      push(item.limitacoes)
      push(item.desenho_estudo)
      break
    case 'noticia':
      push(item.contexto)
      push(item.insights)
      push(item.por_que_importa)
      push(item.pontos_principais)
      push(item.falas)
      push(item.resumo)
      break
    case 'pulso':
      push(item.razao_destaque)
      push(item.o_que_paper_diz)
      push(item.interpretacao_comunidade)
      push(item.o_que_muda)
      push(item.o_que_nao_muda_ainda)
      break
    case 'substack':
      push(item.resumo)
      push(item.bullets)
      push(item.quem_se_aplica)
      push(item.evidencia_chave)
      push(item.contraponto)
      push(item.tema)
      break
    case 'podcast':
      push(item.abstract)
      push(item.canal)
      break
    case 'discussao':
      push(item.resumo)
      push(item.impacto_clinico)
      push(item.categoria)
      break
    case 'video':
      push(item.canal)
      push(item.descricao_preview)
      break
    case 'idea':
      push(item.ideia)
      push(item.bullets)
      push(item.tipo)
      if (item.fonte) {
        push(item.fonte.titulo_origem)
        push(item.fonte.publicacao)
      }
      break
  }
  return parts.join(' ')
}

/** Iterate all items of a report and yield {type, item} pairs. */
function* iterReportItems(report) {
  if (!report) return
  for (const a of report.artigos || []) yield { type: 'artigo', item: a }
  for (const n of report.noticias || []) yield { type: 'noticia', item: n }
  for (const p of report.pulso || []) yield { type: 'pulso', item: p }
  for (const s of report.substacks || []) yield { type: 'substack', item: s }
  for (const p of report.podcasts || []) yield { type: 'podcast', item: p }
  for (const d of report.discussoes_x || []) yield { type: 'discussao', item: d }
  for (const v of report.videos_youtube || []) yield { type: 'video', item: v }
  for (const i of report.post_ideas || []) yield { type: 'idea', item: i }
}

/** Make a ~140-char snippet centered on the first match. */
function buildSnippet(haystack, needleNorm, contextChars = 80) {
  if (!haystack) return ''
  const norm = normalize(haystack)
  const idx = norm.indexOf(needleNorm)
  if (idx === -1) return haystack.slice(0, 140)
  const start = Math.max(0, idx - contextChars)
  const end = Math.min(haystack.length, idx + needleNorm.length + contextChars)
  let snip = haystack.slice(start, end)
  if (start > 0) snip = '… ' + snip
  if (end < haystack.length) snip = snip + ' …'
  return snip
}

async function loadAllReports() {
  if (loaded.value || loading.value) return
  loading.value = true
  loadError.value = null
  try {
    const dates = await fetchIndex()
    // Carrega em paralelo (Promise.allSettled tolera falhas pontuais)
    const results = await Promise.allSettled(
      dates.map((d) => fetchReportByDate(d).then((r) => [d, r]))
    )
    const map = new Map()
    for (const r of results) {
      if (r.status === 'fulfilled') map.set(r.value[0], r.value[1])
    }
    allReports.value = map
    loaded.value = true
  } catch (e) {
    loadError.value = e?.message || 'Falha ao carregar histórico'
    console.error('useSearch loadAllReports failed:', e)
  } finally {
    loading.value = false
  }
}

const isActive = computed(() => query.value.trim().length >= 2)

const results = computed(() => {
  if (!isActive.value) return []
  const needle = normalize(query.value.trim())
  if (!needle) return []

  const out = []
  // Iterate newest-first (Map preserves insertion order; index.json is newest-first)
  for (const [date, report] of allReports.value.entries()) {
    for (const { type, item } of iterReportItems(report)) {
      const text = extractSearchableText(item, type)
      if (!text) continue
      const norm = normalize(text)
      if (norm.includes(needle)) {
        out.push({
          date,
          type,
          item,
          snippet: buildSnippet(text, needle),
        })
      }
    }
  }
  return out
})

const resultsByDate = computed(() => {
  const grouped = new Map()
  for (const r of results.value) {
    if (!grouped.has(r.date)) grouped.set(r.date, [])
    grouped.get(r.date).push(r)
  }
  return grouped
})

const resultsByType = computed(() => {
  const counts = {}
  for (const r of results.value) counts[r.type] = (counts[r.type] || 0) + 1
  return counts
})

const daysIndexed = computed(() => allReports.value.size)

export function useSearch() {
  return {
    query,
    loading,
    loaded,
    loadError,
    isActive,
    results,
    resultsByDate,
    resultsByType,
    daysIndexed,
    loadAllReports,
    clear() { query.value = '' },
  }
}
