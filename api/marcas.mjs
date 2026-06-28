import { authorize, redisPlan } from '../frontend/src/shared/marcasCore.js'

const KEY = 'marcas:lidos'

// REST do Upstash: POST com corpo ["CMD","arg1",...] -> { result }
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
      const out = await redis(['SMEMBERS', KEY])
      return res.status(200).json({ ids: out.result || [] })
    }
    if (req.method === 'POST') {
      if (!authorize(req.headers['x-marcas-token'], process.env.MARCAS_SECRET)) {
        return res.status(401).json({ error: 'senha inválida' })
      }
      const body = typeof req.body === 'string' ? JSON.parse(req.body) : req.body
      const plan = redisPlan('POST', body)
      if (plan.error) return res.status(400).json({ error: plan.error })
      const membros = plan.members || [plan.member]
      await redis([plan.cmd.toUpperCase(), KEY, ...membros])
      return res.status(200).json({ ok: true })
    }
    return res.status(405).json({ error: 'método não suportado' })
  } catch (e) {
    return res.status(500).json({ error: String(e) })
  }
}
