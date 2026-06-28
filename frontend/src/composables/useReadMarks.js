import { ref } from 'vue'

// Marcas "já li / já estudei" sincronizadas via /api/marcas (KV). Singleton:
// um único conjunto reativo de IDs, compartilhado por toda a app. Lê ao iniciar
// e ao voltar o foco da aba; escreve otimista (reverte se o POST falhar).
const TOKEN_KEY = 'marcas_token'
const ids = ref(new Set())
let started = false

async function reload() {
  try {
    const r = await fetch('/api/marcas')
    if (r.ok) ids.value = new Set((await r.json()).ids || [])
  } catch { /* mantém o que tem; nunca quebra a tela */ }
}

export function useReadMarks() {
  if (!started) {
    started = true
    reload()
    if (typeof document !== 'undefined') {
      document.addEventListener('visibilitychange', () => {
        if (!document.hidden) reload()   // recarrega ao voltar pra aba
      })
    }
  }

  function isRead(id) { return ids.value.has(id) }
  function hasToken() { return Boolean(localStorage.getItem(TOKEN_KEY)) }
  function setToken(t) { if (t) localStorage.setItem(TOKEN_KEY, t) }

  async function toggle(id) {
    const novo = !ids.value.has(id)
    const otim = new Set(ids.value)
    novo ? otim.add(id) : otim.delete(id)
    ids.value = otim                       // otimista

    try {
      const r = await fetch('/api/marcas', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-marcas-token': localStorage.getItem(TOKEN_KEY) || '' },
        body: JSON.stringify({ id, lido: novo }),
      })
      if (!r.ok) throw new Error('falha ao salvar')
    } catch (e) {
      const rev = new Set(ids.value)
      novo ? rev.delete(id) : rev.add(id)
      ids.value = rev                      // reverte
      throw e
    }
  }

  return { isRead, toggle, hasToken, setToken, reload }
}
