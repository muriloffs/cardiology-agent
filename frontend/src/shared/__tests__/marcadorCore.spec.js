import { describe, it, expect } from 'vitest'
import { parseMarcadorOp, parseMarcadorHash } from '../marcadorCore'

describe('marcadorCore', () => {
  it('set monta a marca com slug, anchor e data', () => {
    const r = parseMarcadorOp({ op: 'set', slug: 's1', anchor: 7 })
    expect(r.op).toBe('set')
    expect(r.slug).toBe('s1')
    expect(r.marca).toMatchObject({ slug: 's1', anchor: 7 })
    expect(r.marca.savedAt).toBeTruthy()
  })
  it('set exige slug e anchor válido (>=0)', () => {
    expect(parseMarcadorOp({ op: 'set', anchor: 1 }).error).toBeTruthy()
    expect(parseMarcadorOp({ op: 'set', slug: 's', anchor: -1 }).error).toBeTruthy()
    expect(parseMarcadorOp({ op: 'set', slug: 's', anchor: 'x' }).error).toBeTruthy()
  })
  it('set aceita anchor 0', () => {
    expect(parseMarcadorOp({ op: 'set', slug: 's', anchor: 0 }).marca.anchor).toBe(0)
  })
  it('del exige slug', () => {
    expect(parseMarcadorOp({ op: 'del', slug: 's' })).toEqual({ op: 'del', slug: 's' })
    expect(parseMarcadorOp({ op: 'del' }).error).toBeTruthy()
  })
  it('op inválida é erro', () => {
    expect(parseMarcadorOp({ op: 'x' }).error).toBeTruthy()
    expect(parseMarcadorOp(null).error).toBeTruthy()
  })
  it('parseMarcadorHash vira objeto slug->marca', () => {
    const flat = ['s1', JSON.stringify({ slug: 's1', anchor: 3 }), 's2', JSON.stringify({ slug: 's2', anchor: 9 })]
    expect(parseMarcadorHash(flat)).toEqual({ s1: { slug: 's1', anchor: 3 }, s2: { slug: 's2', anchor: 9 } })
  })
})
