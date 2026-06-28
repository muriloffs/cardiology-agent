import { describe, it, expect } from 'vitest'
import { parseFavOp, parseFavHgetall, mesesDeFavoritos } from '../favoritosCore'

describe('favoritosCore', () => {
  it('add monta o favorito com mes e snapshot do item', () => {
    const r = parseFavOp({ op: 'add', id: 'artigo:x', type: 'artigo', item: { titulo: 'T' } }, '2026-06')
    expect(r.op).toBe('add')
    expect(r.fav).toMatchObject({ id: 'artigo:x', type: 'artigo', mes: '2026-06', item: { titulo: 'T' } })
    expect(r.fav.savedAt).toBeTruthy()
  })
  it('add exige id, type e item', () => {
    expect(parseFavOp({ op: 'add', type: 'artigo', item: {} }).error).toBeTruthy()
    expect(parseFavOp({ op: 'add', id: 'x', item: {} }).error).toBeTruthy()
    expect(parseFavOp({ op: 'add', id: 'x', type: 'artigo' }).error).toBeTruthy()
  })
  it('del exige id', () => {
    expect(parseFavOp({ op: 'del', id: 'x' })).toEqual({ op: 'del', id: 'x' })
    expect(parseFavOp({ op: 'del' }).error).toBeTruthy()
  })
  it('parseFavHgetall extrai e ordena por savedAt desc', () => {
    const flat = [
      'a', JSON.stringify({ id: 'a', savedAt: '2026-06-01T00:00:00Z' }),
      'b', JSON.stringify({ id: 'b', savedAt: '2026-06-10T00:00:00Z' }),
    ]
    expect(parseFavHgetall(flat).map((f) => f.id)).toEqual(['b', 'a'])
  })
  it('mesesDeFavoritos: distintos, mais recente primeiro', () => {
    const favs = [{ mes: '2026-05' }, { mes: '2026-06' }, { mes: '2026-05' }]
    expect(mesesDeFavoritos(favs)).toEqual(['2026-06', '2026-05'])
  })
})
