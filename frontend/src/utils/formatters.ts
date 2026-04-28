export function formatDate(dateStr: string): string {
  if (!dateStr) return ''
  const date = new Date(dateStr + 'T00:00:00')
  return date.toLocaleDateString('pt-BR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

export function formatDateTime(isoString: string): string {
  if (!isoString) return ''
  const date = new Date(isoString)
  return date.toLocaleString('pt-BR')
}

export function truncateText(text: string, maxLength: number): string {
  if (!text || text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

export function getClassColor(classe: string): string {
  switch (classe) {
    case 'A': return '#FF6B6B'
    case 'B': return '#FFA500'
    case 'C': return '#4CAF50'
    default: return '#999999'
  }
}

export function getClassBgColor(classe: string): string {
  switch (classe) {
    case 'A': return 'bg-red-100'
    case 'B': return 'bg-orange-100'
    case 'C': return 'bg-green-100'
    default: return 'bg-gray-100'
  }
}

export function getSourceEmoji(source: string): string {
  switch (source?.toLowerCase()) {
    case 'revista': return '📰'
    case 'podcast': return '🎙️'
    case 'twitter':
    case 'x/twitter': return '🐦'
    case 'substack': return '📝'
    default: return '📄'
  }
}

export function getSourceLabel(source: string): string {
  switch (source?.toLowerCase()) {
    case 'revista': return 'Revista'
    case 'podcast': return 'Podcast'
    case 'twitter':
    case 'x/twitter': return 'X/Twitter'
    case 'substack': return 'Substack'
    default: return source
  }
}
