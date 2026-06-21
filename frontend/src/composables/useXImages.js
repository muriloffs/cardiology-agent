/**
 * PROTÓTIPO — carrega a amostra de imagens colhidas do X
 * (data/imagens-x-sample.json gerado pelo fetch_x_images.py).
 *
 * Lazy-load no primeiro acesso à aba. Singleton.
 */
import { ref } from 'vue'

const GITHUB_RAW = 'https://raw.githubusercontent.com/muriloffs/cardiology-agent/main/data/imagens-x-sample.json'

const loading = ref(false)
const loaded = ref(false)
const loadError = ref(null)
const data = ref(null) // { total, por_tipo, por_categoria_fonte, imagens, gerado_em }

async function loadXImages(force = false) {
  if (loading.value) return
  if (loaded.value && !force) return
  loading.value = true
  loadError.value = null
  try {
    const resp = await fetch(`${GITHUB_RAW}?t=${Date.now()}`)
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    data.value = await resp.json()
    loaded.value = true
  } catch (e) {
    loadError.value = e?.message || 'Falha ao carregar amostra'
    console.error('useXImages load failed:', e)
  } finally {
    loading.value = false
  }
}

export function useXImages() {
  return { loading, loaded, loadError, data, loadXImages }
}
