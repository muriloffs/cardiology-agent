// frontend/src/utils/api.ts
import axios from 'axios'

const GITHUB_RAW_URL = 'https://raw.githubusercontent.com/muriloffs/cardiology-agent/main/data'

function getTodayDate(): string {
  const now = new Date()
  return now.getFullYear() + '-' +
    String(now.getMonth() + 1).padStart(2, '0') + '-' +
    String(now.getDate()).padStart(2, '0')
}

export async function fetchLatestReport() {
  for (let daysBack = 0; daysBack < 7; daysBack++) {
    const date = new Date()
    date.setDate(date.getDate() - daysBack)
    const dateStr = date.getFullYear() + '-' +
      String(date.getMonth() + 1).padStart(2, '0') + '-' +
      String(date.getDate()).padStart(2, '0')
    try {
      const response = await axios.get(`${GITHUB_RAW_URL}/relatorio-${dateStr}.json`)
      return response.data
    } catch (error: any) {
      if (error?.response?.status !== 404) {
        console.error('Failed to fetch report:', error)
        throw new Error('Erro ao carregar relatório')
      }
    }
  }
  throw new Error('Nenhum relatório encontrado nos últimos 7 dias')
}

export async function downloadArticle(articleId: string, titulo: string, url: string) {
  try {
    const response = await axios.post('/api/download', {
      articleId,
      titulo,
      url
    })
    return response.data
  } catch (error) {
    console.error('Download failed:', error)
    throw new Error('Failed to download article')
  }
}

export async function fetchIndex(): Promise<string[]> {
  try {
    const response = await axios.get(`${GITHUB_RAW_URL}/index.json`)
    return response.data.dates || []
  } catch {
    return []
  }
}

export async function fetchReportByDate(date: string) {
  const response = await axios.get(`${GITHUB_RAW_URL}/relatorio-${date}.json`)
  return response.data
}
