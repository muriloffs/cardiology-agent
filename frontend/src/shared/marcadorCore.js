// Lógica pura do marcador de leitura ("continuar de onde parei") — sem I/O,
// testável e compartilhada com o handler serverless (api/marcador.mjs).
// Uma marca por estudo: slug -> { anchor (índice do parágrafo), savedAt }.

export function parseMarcadorOp(body) {
  if (!body || typeof body !== 'object') return { error: 'body inválido' }
  if (body.op === 'set') {
    if (!body.slug) return { error: 'slug obrigatório' }
    const anchor = Number(body.anchor)
    if (!Number.isFinite(anchor) || anchor < 0) return { error: 'anchor inválido' }
    return { op: 'set', slug: body.slug, marca: { slug: body.slug, anchor, savedAt: new Date().toISOString() } }
  }
  if (body.op === 'del') {
    if (!body.slug) return { error: 'slug obrigatório' }
    return { op: 'del', slug: body.slug }
  }
  return { error: 'op inválida' }
}

// HGETALL volta [slug1, json1, slug2, json2, ...] -> objeto { slug: marca }.
export function parseMarcadorHash(flat) {
  const out = {}
  for (let i = 0; i < (flat || []).length; i += 2) {
    try { out[flat[i]] = JSON.parse(flat[i + 1]) } catch { /* ignora item corrompido */ }
  }
  return out
}
