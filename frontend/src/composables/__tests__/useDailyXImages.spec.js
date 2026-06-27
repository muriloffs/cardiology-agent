import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useDailyXImages } from '../useDailyXImages'

const INDEX = { dates: ['2026-06-26', '2026-06-25'] }
const DAYS = {
  '2026-06-26': { data: '2026-06-26', total: 41, imagens: [{ image_url: 'a' }] },
  '2026-06-25': { data: '2026-06-25', total: 22, imagens: [{ image_url: 'b' }] },
}

describe('useDailyXImages', () => {
  beforeEach(() => {
    global.fetch = vi.fn((url) => {
      if (url.includes('imagens-x-index.json')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(INDEX) })
      }
      const m = url.match(/imagens-x-(\d{4}-\d{2}-\d{2})\.json/)
      return Promise.resolve({ ok: true, json: () => Promise.resolve(DAYS[m[1]]) })
    })
  })

  it('abre no dia mais recente', async () => {
    const x = useDailyXImages()
    await x.open()
    expect(x.selectedDate.value).toBe('2026-06-26')
    expect(x.data.value.total).toBe(41)
  })

  it('navega para o dia anterior (mais antigo)', async () => {
    const x = useDailyXImages()
    await x.open()
    expect(x.canPrev.value).toBe(true)
    await x.prevDay()
    expect(x.selectedDate.value).toBe('2026-06-25')
    expect(x.data.value.total).toBe(22)
    expect(x.canNext.value).toBe(true)
  })
})
