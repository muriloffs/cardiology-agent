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
  const today = getTodayDate()
  try {
    const response = await axios.get(`${GITHUB_RAW_URL}/relatorio-${today}.json`)
    return response.data
  } catch (error: any) {
    if (error?.response?.status === 404) {
      throw new Error(`Nenhum relatório encontrado para ${today}`)
    }
    console.error('Failed to fetch report:', error)
    throw new Error('Unable to fetch today\'s cardiology report')
  }
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

export async function fetchReportHistory(dates: string[]) {
  const reports: Record<string, any> = {}
  for (const date of dates) {
    try {
      const url = `${GITHUB_RAW_URL}/relatorio-${date}.json`
      reports[date] = await axios.get(url).then(r => r.data)
    } catch (e) {
      // Date not available
    }
  }
  return reports
}
