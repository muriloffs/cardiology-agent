// @vitest-environment jsdom
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useFavoritos } from '../useFavoritos'

describe('useFavoritos', () => {
  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem('marcas_token', 'senha')
  })

  it('carrega favoritos e agrupa meses (desc)', async () => {
    global.fetch = vi.fn(() => Promise.resolve({
      ok: true, json: () => Promise.resolve({ favoritos: [
        { id: 'artigo:a', type: 'artigo', mes: '2026-06', item: {}, savedAt: '2026-06-10' },
        { id: 'noticia:b', type: 'noticia', mes: '2026-05', item: {}, savedAt: '2026-05-01' },
      ] }),
    }))
    const f = useFavoritos()
    await f.reload()
    expect(f.favs.value).toHaveLength(2)
    expect(f.meses.value).toEqual(['2026-06', '2026-05'])
    expect(f.favsDoMes('2026-06').map((x) => x.id)).toEqual(['artigo:a'])
    expect(f.isFav('artigo:a')).toBe(true)
  })

  it('toggle adiciona e manda op add com type+item', async () => {
    global.fetch = vi.fn((url, opts) => {
      if (opts && opts.method === 'POST') {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ ok: true, fav: { id: 'artigo:z', type: 'artigo', mes: '2026-06', item: { t: 1 } } }) })
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ favoritos: [] }) })
    })
    const f = useFavoritos()
    await f.reload()
    await f.toggle('artigo:z', 'artigo', { t: 1 })
    expect(f.isFav('artigo:z')).toBe(true)
    const call = global.fetch.mock.calls.find((c) => c[1] && c[1].method === 'POST')
    expect(JSON.parse(call[1].body)).toEqual({ op: 'add', id: 'artigo:z', type: 'artigo', item: { t: 1 } })
  })

  it('remove é otimista e reverte se falhar', async () => {
    global.fetch = vi.fn((url, opts) => {
      if (opts && opts.method === 'POST') return Promise.resolve({ ok: false })
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ favoritos: [{ id: 'artigo:a', type: 'artigo', mes: '2026-06', item: {}, savedAt: '2026-06-01' }] }) })
    })
    const f = useFavoritos()
    await f.reload()
    await expect(f.remove('artigo:a')).rejects.toThrow()
    expect(f.isFav('artigo:a')).toBe(true)  // revertido
  })
})
