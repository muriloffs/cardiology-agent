import { ref, computed } from 'vue'

// Grifos (trechos salvos) sincronizados via /api/grifos (KV). Singleton.
// Mesma senha das marcas (localStorage 'marcas_token'). Lê ao iniciar e ao
// voltar o foco da aba.
const TOKEN_KEY = 'marcas_token'
const grifos = ref([])
let started = false

async function reload() {
  try {
    const r = await fetch('/api/grifos')
    if (r.ok) grifos.value = (await r.json()).grifos || []
  } catch { /* mantém o que tem; nunca quebra a tela */ }
}

export function useGrifos() {
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

  async function add(trecho, slug, titulo) {
    const r = await fetch('/api/grifos', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'x-marcas-token': localStorage.getItem(TOKEN_KEY) || '' },
      body: JSON.stringify({ op: 'add', trecho, slug, titulo }),
    })
    if (!r.ok) throw new Error('falha ao salvar')
    const { grifo } = await r.json()
    grifos.value = [grifo, ...grifos.value]
    return grifo
  }

  async function remove(id) {
    const prev = grifos.value
    grifos.value = grifos.value.filter(g => g.id !== id)   // otimista
    try {
      const r = await fetch('/api/grifos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-marcas-token': localStorage.getItem(TOKEN_KEY) || '' },
        body: JSON.stringify({ op: 'del', id }),
      })
      if (!r.ok) throw new Error('falha ao apagar')
    } catch (e) {
      grifos.value = prev                                  // reverte
      throw e
    }
  }

  // Agrupado por estudo (preserva a ordem de chegada dos grupos).
  const porEstudo = computed(() => {
    const map = new Map()
    for (const g of grifos.value) {
      if (!map.has(g.slug)) map.set(g.slug, { slug: g.slug, titulo: g.titulo, itens: [] })
      map.get(g.slug).itens.push(g)
    }
    return [...map.values()]
  })

  return { grifos, porEstudo, add, remove, hasToken, reload }
}
