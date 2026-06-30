import { authorize } from '../frontend/src/shared/marcasCore.js'
import { parseMarcadorOp, parseMarcadorHash } from '../frontend/src/shared/marcadorCore.js'

const KEY = 'marcadores:hash'

async function redis(args) {
  const base = process.env.KV_REST_API_URL
  const token = process.env.KV_REST_API_TOKEN
  const r = await fetch(base, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(args),
  })
  if (!r.ok) throw new Error(`KV ${r.status}`)
  return r.json()
}

export default async function handler(req, res) {
  try {
    if (req.method === 'GET') {
      const out = await redis(['HGETALL', KEY])
      return res.status(200).json({ marcadores: parseMarcadorHash(out.result || []) })
    }
    if (req.method === 'POST') {
      if (!authorize(req.headers['x-marcas-token'], process.env.MARCAS_SECRET)) {
        return res.status(401).json({ error: 'senha inválida' })
      }
      const body = typeof req.body === 'string' ? JSON.parse(req.body) : req.body
      const op = parseMarcadorOp(body)
      if (op.error) return res.status(400).json({ error: op.error })
      if (op.op === 'set') {
        await redis(['HSET', KEY, op.slug, JSON.stringify(op.marca)])
        return res.status(200).json({ ok: true, marca: op.marca })
      }
      await redis(['HDEL', KEY, op.slug])
      return res.status(200).json({ ok: true })
    }
    return res.status(405).json({ error: 'método não suportado' })
  } catch (e) {
    return res.status(500).json({ error: String(e) })
  }
}
