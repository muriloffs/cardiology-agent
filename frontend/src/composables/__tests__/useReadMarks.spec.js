// @vitest-environment jsdom
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useReadMarks } from '../useReadMarks'

function mockFetch(getIds = []) {
  return vi.fn((url, opts) => {
    if (!opts || opts.method !== 'POST') {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ ids: getIds }) })
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve({ ok: true }) })
  })
}

describe('useReadMarks', () => {
  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem('marcas_token', 'senha')
  })

  it('carrega os ids do GET e isRead reflete', async () => {
    global.fetch = mockFetch(['estudo:a'])
    const m = useReadMarks()
    await m.reload()
    expect(m.isRead('estudo:a')).toBe(true)
    expect(m.isRead('estudo:b')).toBe(false)
  })

  it('toggle marca otimista e chama POST com token', async () => {
    global.fetch = mockFetch([])
    const m = useReadMarks()
    await m.reload()
    await m.toggle('estudo:b')
    expect(m.isRead('estudo:b')).toBe(true)
    const call = global.fetch.mock.calls.find(c => c[1] && c[1].method === 'POST')
    expect(call[1].headers['x-marcas-token']).toBe('senha')
    expect(JSON.parse(call[1].body)).toEqual({ id: 'estudo:b', lido: true })
  })

  it('reverte a marca se o POST falhar', async () => {
    global.fetch = vi.fn((url, opts) => {
      if (opts && opts.method === 'POST') return Promise.resolve({ ok: false })
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ ids: [] }) })
    })
    const m = useReadMarks()
    await m.reload()
    await expect(m.toggle('estudo:c')).rejects.toThrow()
    expect(m.isRead('estudo:c')).toBe(false)
  })
})
