// @vitest-environment jsdom
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useMarcadores } from '../useMarcadores'

describe('useMarcadores', () => {
  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem('marcas_token', 'senha')
  })

  it('carrega o mapa de marcadores', async () => {
    global.fetch = vi.fn(() => Promise.resolve({
      ok: true, json: () => Promise.resolve({ marcadores: { s1: { slug: 's1', anchor: 4 } } }),
    }))
    const m = useMarcadores()
    await m.reload()
    expect(m.has('s1')).toBe(true)
    expect(m.get('s1').anchor).toBe(4)
    expect(m.has('s2')).toBe(false)
  })

  it('set grava otimista e manda op set', async () => {
    global.fetch = vi.fn((url, opts) => {
      if (opts && opts.method === 'POST') return Promise.resolve({ ok: true, json: () => Promise.resolve({ ok: true }) })
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ marcadores: {} }) })
    })
    const m = useMarcadores()
    await m.reload()
    await m.set('s9', 12)
    expect(m.get('s9').anchor).toBe(12)
    const call = global.fetch.mock.calls.find((c) => c[1] && c[1].method === 'POST')
    expect(JSON.parse(call[1].body)).toEqual({ op: 'set', slug: 's9', anchor: 12 })
  })

  it('clear remove otimista e reverte se falhar', async () => {
    global.fetch = vi.fn((url, opts) => {
      if (opts && opts.method === 'POST') return Promise.resolve({ ok: false })
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ marcadores: { s1: { slug: 's1', anchor: 1 } } }) })
    })
    const m = useMarcadores()
    await m.reload()
    await expect(m.clear('s1')).rejects.toThrow()
    expect(m.has('s1')).toBe(true)   // revertido
  })
})
