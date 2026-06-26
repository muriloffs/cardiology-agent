import { describe, it, expect } from 'vitest'
import { renderStudyMarkdown } from '../StudyReader.vue'

const BASE = 'https://raw.example/data/estudos/a-2026-06-24/'

describe('renderStudyMarkdown', () => {
  it('marca a camada de estudo com classe distinta', () => {
    const html = renderStudyMarkdown('> 🎓 **Aprofunde:** rigidez ventricular', BASE)
    expect(html).toContain('class="study-layer"')
    expect(html).toContain('Aprofunde')
  })

  it('reescreve src de imagem relativa para a base raw', () => {
    const html = renderStudyMarkdown('![forest plot](fig-1.png)', BASE)
    expect(html).toContain(`src="${BASE}fig-1.png"`)
  })

  it('renderiza tabela e paragrafo normais', () => {
    const html = renderStudyMarkdown('## Intro\n\nTexto normal.', BASE)
    expect(html).toContain('<h2')
    expect(html).toContain('Texto normal')
  })
})
