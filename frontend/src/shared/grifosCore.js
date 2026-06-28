// Lógica pura dos grifos (trechos salvos) — sem I/O, testável e compartilhada
// com o handler serverless (api/grifos.mjs).

export function newId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8)
}

// Valida o corpo do POST e devolve a operação a executar (ou um erro).
// op 'add' -> cria o objeto grifo (com id e data); op 'del' -> id a remover.
export function parseGrifoOp(body, hoje = new Date().toISOString().slice(0, 10)) {
  if (!body || typeof body !== 'object') return { error: 'body inválido' }
  if (body.op === 'add') {
    const trecho = (body.trecho || '').trim()
    if (!trecho) return { error: 'trecho vazio' }
    if (!body.slug) return { error: 'slug obrigatório' }
    return {
      op: 'add',
      grifo: { id: newId(), slug: body.slug, titulo: body.titulo || '', trecho, data: hoje },
    }
  }
  if (body.op === 'del') {
    if (!body.id) return { error: 'id obrigatório' }
    return { op: 'del', id: body.id }
  }
  return { error: 'op inválida' }
}

// HGETALL volta um array plano [campo1, valor1, campo2, valor2, ...]; os valores
// (índices ímpares) são JSON dos grifos. Parseia e ordena por data desc.
export function parseHgetall(flat) {
  const out = []
  for (let i = 1; i < (flat || []).length; i += 2) {
    try { out.push(JSON.parse(flat[i])) } catch { /* ignora item corrompido */ }
  }
  out.sort((a, b) => (b.data || '').localeCompare(a.data || ''))
  return out
}
