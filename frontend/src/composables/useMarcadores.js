import { ref } from 'vue'

// Marcador de leitura ("continuar de onde parei") sincronizado via /api/marcador.
// Singleton. Uma marca por estudo (slug -> { anchor, savedAt }). Mesma senha.
const TOKEN_KEY = 'marcas_token'
const marcas = ref({})   // slug -> { anchor, savedAt }
let started = false

async function reload() {
  try {
    const r = await fetch('/api/marcador')
    if (r.ok) marcas.value = (await r.json()).marcadores || {}
  } catch { /* mantém o que tem; nunca quebra a tela */ }
}

export function useMarcadores() {
  if (!started) {
    started = true
    reload()
    if (typeof document !== 'undefined') {
      document.addEventListener('visibilitychange', () => {
        if (!document.hidden) reload()
      })
    }
  }

  function hasToken() { return Boolean(localStorage.getItem(TOKEN_KEY)) }
  function get(slug) { return marcas.value[slug] || null }
  function has(slug) { return Boolean(marcas.value[slug]) }

  async function set(slug, anchor) {
    const prev = marcas.value
    marcas.value = { ...marcas.value, [slug]: { slug, anchor, savedAt: new Date().toISOString() } }
    try {
      const r = await fetch('/api/marcador', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-marcas-token': localStorage.getItem(TOKEN_KEY) || '' },
        body: JSON.stringify({ op: 'set', slug, anchor }),
      })
      if (!r.ok) throw new Error('falha ao marcar')
    } catch (e) {
      marcas.value = prev
      throw e
    }
  }

  async function clear(slug) {
    if (!marcas.value[slug]) return
    const prev = marcas.value
    const m = { ...marcas.value }
    delete m[slug]
    marcas.value = m
    try {
      const r = await fetch('/api/marcador', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-marcas-token': localStorage.getItem(TOKEN_KEY) || '' },
        body: JSON.stringify({ op: 'del', slug }),
      })
      if (!r.ok) throw new Error('falha ao limpar')
    } catch (e) {
      marcas.value = prev
      throw e
    }
  }

  return { marcas, get, has, set, clear, hasToken, reload }
}
