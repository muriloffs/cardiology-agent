// @vitest-environment jsdom
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useGrifos } from '../useGrifos'

describe('useGrifos', () => {
  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem('marcas_token', 'senha')
  })

  it('carrega os grifos do GET e agrupa por estudo', async () => {
    global.fetch = vi.fn(() => Promise.resolve({
      ok: true, json: () => Promise.resolve({ grifos: [
        { id: 'a', slug: 's1', titulo: 'T1', trecho: 'x', data: '2026-06-10' },
        { id: 'b', slug: 's1', titulo: 'T1', trecho: 'y', data: '2026-06-09' },
        { id: 'c', slug: 's2', titulo: 'T2', trecho: 'z', data: '2026-06-08' },
      ] }),
    }))
    const g = useGrifos()
    await g.reload()
    expect(g.grifos.value).toHaveLength(3)
    expect(g.porEstudo.value.map(e => e.slug)).toEqual(['s1', 's2'])
    expect(g.porEstudo.value[0].itens).toHaveLength(2)
  })

  it('add posta e adiciona o grifo retornado no topo', async () => {
    global.fetch = vi.fn((url, opts) => {
      if (opts && opts.method === 'POST') {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ ok: true, grifo: { id: 'novo', slug: 's', titulo: 'T', trecho: 'oi', data: '2026-06-28' } }) })
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ grifos: [] }) })
    })
    const g = useGrifos()
    await g.reload()
    const novo = await g.add('oi', 's', 'T')
    expect(novo.id).toBe('novo')
    expect(g.grifos.value[0].id).toBe('novo')
    const call = global.fetch.mock.calls.find(c => c[1] && c[1].method === 'POST')
    expect(JSON.parse(call[1].body)).toEqual({ op: 'add', trecho: 'oi', slug: 's', titulo: 'T' })
  })

  it('remove é otimista e reverte se falhar', async () => {
    let first = true
    global.fetch = vi.fn((url, opts) => {
      if (opts && opts.method === 'POST') return Promise.resolve({ ok: false })
      // GET inicial com um grifo
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ grifos: [{ id: 'x', slug: 's', titulo: 'T', trecho: 'a', data: '2026-06-01' }] }) })
    })
    const g = useGrifos()
    await g.reload()
    expect(g.grifos.value).toHaveLength(1)
    await expect(g.remove('x')).rejects.toThrow()
    expect(g.grifos.value).toHaveLength(1)  // revertido
  })
})
