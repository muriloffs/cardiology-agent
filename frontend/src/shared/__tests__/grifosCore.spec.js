import { describe, it, expect } from 'vitest'
import { parseGrifoOp, parseHgetall, newId } from '../grifosCore'

describe('grifosCore', () => {
  it('add monta o grifo com id, data e campos', () => {
    const r = parseGrifoOp({ op: 'add', trecho: '  texto  ', slug: 's1', titulo: 'T' }, '2026-06-28')
    expect(r.op).toBe('add')
    expect(r.grifo).toMatchObject({ slug: 's1', titulo: 'T', trecho: 'texto', data: '2026-06-28' })
    expect(r.grifo.id).toBeTruthy()
  })
  it('add sem trecho ou sem slug é erro', () => {
    expect(parseGrifoOp({ op: 'add', trecho: '   ', slug: 's' }).error).toBeTruthy()
    expect(parseGrifoOp({ op: 'add', trecho: 'x' }).error).toBeTruthy()
  })
  it('del exige id', () => {
    expect(parseGrifoOp({ op: 'del', id: 'abc' })).toEqual({ op: 'del', id: 'abc' })
    expect(parseGrifoOp({ op: 'del' }).error).toBeTruthy()
  })
  it('op desconhecida é erro', () => {
    expect(parseGrifoOp({ op: 'nope' }).error).toBeTruthy()
    expect(parseGrifoOp(null).error).toBeTruthy()
  })
  it('parseHgetall extrai valores e ordena por data desc', () => {
    const flat = [
      'id1', JSON.stringify({ id: 'id1', data: '2026-06-01', trecho: 'a' }),
      'id2', JSON.stringify({ id: 'id2', data: '2026-06-10', trecho: 'b' }),
    ]
    const out = parseHgetall(flat)
    expect(out.map(g => g.id)).toEqual(['id2', 'id1'])
  })
  it('newId gera ids distintos', () => {
    expect(newId()).not.toBe(newId())
  })
})
