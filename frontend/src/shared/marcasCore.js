// Lógica pura da função /api/marcas — sem I/O, testável e compartilhada com o
// handler serverless (api/marcas.mjs a importa por caminho relativo).

export function authorize(token, secret) {
  return Boolean(secret) && token === secret
}

export function redisPlan(method, body) {
  if (method === 'GET') return { cmd: 'smembers' }
  if (method === 'POST') {
    const id = body && body.id
    if (!id || typeof id !== 'string') return { error: 'id obrigatório' }
    return { cmd: body.lido ? 'sadd' : 'srem', member: id }
  }
  return { error: 'método não suportado' }
}
