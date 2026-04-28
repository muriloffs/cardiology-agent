import { describe, it, expect } from 'vitest'
import { formatDate, formatDateTime, truncateText, getSourceEmoji } from '../formatters'

describe('formatters', () => {
  it('formatDate converts YYYY-MM-DD to Portuguese locale', () => {
    const result = formatDate('2026-04-28')
    expect(result).toMatch(/28.*abril.*2026/)
  })

  it('truncateText shortens text longer than maxLength', () => {
    const result = truncateText('Hello World', 5)
    expect(result).toBe('Hello...')
  })

  it('truncateText returns original text if under maxLength', () => {
    const result = truncateText('Hi', 10)
    expect(result).toBe('Hi')
  })

  it('getSourceEmoji returns correct emoji for each source', () => {
    expect(getSourceEmoji('revista')).toBe('📰')
    expect(getSourceEmoji('podcast')).toBe('🎙️')
    expect(getSourceEmoji('twitter')).toBe('🐦')
    expect(getSourceEmoji('substack')).toBe('📝')
  })

  it('formatDateTime handles ISO datetime strings', () => {
    const result = formatDateTime('2026-04-28T10:30:00Z')
    expect(result).toMatch(/28.*04.*2026/)
  })
})
