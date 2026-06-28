import { ref, computed } from 'vue'
import { mesesDeFavoritos } from '../shared/favoritosCore'

// Favoritos sincronizados via /api/favoritos (KV). Singleton. Guarda o card
// inteiro (snapshot) + o mês em que foi salvo. Mesma senha das marcas.
const TOKEN_KEY = 'marcas_token'
const favs = ref([])
let started = false

async function reload() {
  try {
    const r = await fetch('/api/favoritos')
    if (r.ok) favs.value = (await r.json()).favoritos || []
  } catch { /* mantém o que tem; nunca quebra a tela */ }
}

export function useFavoritos() {
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
  function isFav(id) { return favs.value.some((f) => f.id === id) }

  async function add(id, type, item) {
    const r = await fetch('/api/favoritos', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'x-marcas-token': localStorage.getItem(TOKEN_KEY) || '' },
      body: JSON.stringify({ op: 'add', id, type, item }),
    })
    if (!r.ok) throw new Error('falha ao favoritar')
    const { fav } = await r.json()
    favs.value = [fav, ...favs.value.filter((f) => f.id !== id)]
    return fav
  }

  async function remove(id) {
    const prev = favs.value
    favs.value = favs.value.filter((f) => f.id !== id)   // otimista
    try {
      const r = await fetch('/api/favoritos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-marcas-token': localStorage.getItem(TOKEN_KEY) || '' },
        body: JSON.stringify({ op: 'del', id }),
      })
      if (!r.ok) throw new Error('falha ao remover')
    } catch (e) {
      favs.value = prev                                  // reverte
      throw e
    }
  }

  async function toggle(id, type, item) {
    return isFav(id) ? remove(id) : add(id, type, item)
  }

  const meses = computed(() => mesesDeFavoritos(favs.value))
  function favsDoMes(mes) { return favs.value.filter((f) => f.mes === mes) }

  return { favs, meses, favsDoMes, isFav, toggle, add, remove, hasToken, reload }
}
