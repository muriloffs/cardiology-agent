// Lógica pura da função /api/marcas — sem I/O, testável e compartilhada com o
// handler serverless (api/marcas.mjs a importa por caminho relativo).

export function authorize(token, secret) {
  return Boolean(secret) && token === secret
}

export function redisPlan(method, body) {
  if (method === 'GET') return { cmd: 'smembers' }
  if (method === 'POST') {
    // Lote: { ids: [...], lido } — marca/desmarca vários (botão "marcar tudo")
    const ids = Array.isArray(body?.ids)
      ? body.ids.filter((x) => typeof x === 'string' && x)
      : null
    if (ids && ids.length) return { cmd: body.lido ? 'sadd' : 'srem', members: ids }
    // Único: { id, lido }
    const id = body && body.id
    if (!id || typeof id !== 'string') return { error: 'id obrigatório' }
    return { cmd: body.lido ? 'sadd' : 'srem', member: id }
  }
  return { error: 'método não suportado' }
}
