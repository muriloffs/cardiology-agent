import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useMonthlyStudies } from '../useMonthlyStudies'

const INDEX = {
  por_mes: {
    '2026-06': [{ slug: 'a-2026-06-24', titulo: 'A', fonte: '@NEJM', tipo: 'revisao', data: '2026-06-24' }],
    '2026-05': [{ slug: 'b-2026-05-10', titulo: 'B', fonte: '@ESC', tipo: 'diretriz', data: '2026-05-10' }],
  },
  meses_disponiveis: ['2026-06', '2026-05'],
}

describe('useMonthlyStudies', () => {
  beforeEach(() => {
    global.fetch = vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve(INDEX) }))
  })

  it('abre no mes mais recente e lista seus estudos', async () => {
    const s = useMonthlyStudies()
    await s.open()
    expect(s.selectedMonth.value).toBe('2026-06')
    expect(s.items.value.map((i) => i.slug)).toEqual(['a-2026-06-24'])
  })

  it('navega para o mes anterior', async () => {
    const s = useMonthlyStudies()
    await s.open()
    expect(s.canOlder.value).toBe(true)
    await s.olderMonth()
    expect(s.selectedMonth.value).toBe('2026-05')
    expect(s.items.value[0].slug).toBe('b-2026-05-10')
    expect(s.canNewer.value).toBe(true)
  })
})
