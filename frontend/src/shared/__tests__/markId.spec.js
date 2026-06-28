import { describe, it, expect } from 'vitest'
import { markId } from '../markId'

describe('markId', () => {
  it('NUNCA usa o id posicional (art_001 etc.) — usa URL/título', () => {
    const art = { id: 'art_001', links: { url: 'https://x/y', doi: '10.1/z' }, titulo: 'T' }
    expect(markId('artigo', art)).toBe('artigo:https://x/y')
    // sem url: cai no DOI; sem DOI: cai no título — mas nunca em art_001
    expect(markId('artigo', { id: 'art_001', titulo: 'T' })).toBe('artigo:T')
  })
  it('o mesmo conteúdo gera o mesmo id (independe do dia/posição)', () => {
    const hoje = { id: 'not_001', links: { url: 'https://n/1' }, titulo: 'N' }
    const ontem = { id: 'not_007', links: { url: 'https://n/1' }, titulo: 'N' }
    expect(markId('noticia', hoje)).toBe(markId('noticia', ontem))
  })
  it('conteúdos diferentes geram ids diferentes', () => {
    const a = { id: 'art_001', links: { url: 'https://a' }, titulo: 'A' }
    const b = { id: 'art_001', links: { url: 'https://b' }, titulo: 'B' }
    expect(markId('artigo', a)).not.toBe(markId('artigo', b))
  })
  it('tipos com campo único', () => {
    expect(markId('video', { id: null, video_url: 'V', titulo: 'T' })).toBe('video:V')
    expect(markId('substack', { id: 'sub_001', url: 'U', titulo: 'T' })).toBe('substack:U')
    expect(markId('pulso', { id: 'pulso_001', titulo: 'P' })).toBe('pulso:P')
    expect(markId('imagem', { image_url: 'I' })).toBe('imagem:I')
    expect(markId('estudo', { slug: 'S' })).toBe('estudo:S')
  })
})
