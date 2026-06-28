// Lógica pura dos favoritos — sem I/O, testável e compartilhada com o handler
// serverless (api/favoritos.mjs). Um favorito guarda o CARD INTEIRO (snapshot),
// porque o conteúdo do dia some do feed depois.

export function parseFavOp(body, mes = new Date().toISOString().slice(0, 7)) {
  if (!body || typeof body !== 'object') return { error: 'body inválido' }
  if (body.op === 'add') {
    if (!body.id || typeof body.id !== 'string') return { error: 'id obrigatório' }
    if (!body.type) return { error: 'type obrigatório' }
    if (!body.item || typeof body.item !== 'object') return { error: 'item obrigatório' }
    return {
      op: 'add',
      fav: { id: body.id, type: body.type, mes, item: body.item, savedAt: new Date().toISOString() },
    }
  }
  if (body.op === 'del') {
    if (!body.id) return { error: 'id obrigatório' }
    return { op: 'del', id: body.id }
  }
  return { error: 'op inválida' }
}

// HGETALL volta [campo1, valor1, ...]; valores (índices ímpares) são JSON dos
// favoritos. Parseia e ordena por savedAt desc (mais recente primeiro).
export function parseFavHgetall(flat) {
  const out = []
  for (let i = 1; i < (flat || []).length; i += 2) {
    try { out.push(JSON.parse(flat[i])) } catch { /* ignora item corrompido */ }
  }
  out.sort((a, b) => (b.savedAt || '').localeCompare(a.savedAt || ''))
  return out
}

// Meses distintos presentes nos favoritos, mais recente primeiro.
export function mesesDeFavoritos(favs) {
  return [...new Set((favs || []).map((f) => f.mes).filter(Boolean))].sort().reverse()
}
