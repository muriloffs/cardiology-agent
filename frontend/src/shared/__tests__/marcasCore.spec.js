import { describe, it, expect } from 'vitest'
import { authorize, redisPlan } from '../marcasCore'

describe('marcasCore', () => {
  it('authorize só aceita token igual ao secret não-vazio', () => {
    expect(authorize('abc', 'abc')).toBe(true)
    expect(authorize('abc', 'xyz')).toBe(false)
    expect(authorize('', '')).toBe(false)
    expect(authorize(undefined, 'abc')).toBe(false)
  })
  it('redisPlan: GET lista', () => {
    expect(redisPlan('GET', null)).toEqual({ cmd: 'smembers' })
  })
  it('redisPlan: POST adiciona/remove pelo campo lido', () => {
    expect(redisPlan('POST', { id: 'estudo:x', lido: true })).toEqual({ cmd: 'sadd', member: 'estudo:x' })
    expect(redisPlan('POST', { id: 'estudo:x', lido: false })).toEqual({ cmd: 'srem', member: 'estudo:x' })
  })
  it('redisPlan: POST sem id é erro', () => {
    expect(redisPlan('POST', {}).error).toBeTruthy()
  })
  it('redisPlan: método não suportado é erro', () => {
    expect(redisPlan('PUT', {}).error).toBeTruthy()
  })
})
