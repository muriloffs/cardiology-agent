import { describe, it, expect } from 'vitest'
import { normTitulo, casaTitulo } from '../matchTitulo'

describe('matchTitulo', () => {
  it('normaliza acentos/pontuação/caixa', () => {
    expect(normTitulo('Avaliação da Função Diastólica!')).toBe('avaliacao da funcao diastolica')
  })
  it('casa títulos idênticos e com pequena variação', () => {
    expect(casaTitulo('Diretriz 2026 AHA/ACC para prevenção', 'Diretriz 2026 AHA ACC para prevenção')).toBe(true)
    expect(casaTitulo('Passado, presente e futuro da avaliação da função diastólica',
                       'Passado presente e futuro da avaliacao da funcao diastolica do ventriculo')).toBe(true)
  })
  it('casa por sobreposição de palavras (Jaccard)', () => {
    expect(casaTitulo('Prevenção de insuficiência cardíaca na atenção primária',
                       'Prevenção da insuficiência cardíaca primária')).toBe(true)
  })
  it('não casa títulos de artigos diferentes', () => {
    expect(casaTitulo('Estenose aórtica e TAVR em 10 anos',
                       'Fibrilação atrial e anticoagulação')).toBe(false)
  })
  it('vazio não casa', () => {
    expect(casaTitulo('', 'algo')).toBe(false)
  })
})
