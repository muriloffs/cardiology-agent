// frontend/src/utils/api.ts
import axios from 'axios'

const GITHUB_RAW_URL = 'https://raw.githubusercontent.com/muriloffs/cardiology-agent/main/data'

export async function fetchLatestReport() {
  try {
    const today = new Date().toISOString().split('T')[0]
    const url = `${GITHUB_RAW_URL}/relatorio-${today}.json`
    const response = await axios.get(url)
    return response.data
  } catch (error) {
    console.error('Failed to fetch report:', error)
    throw new Error('Unable to fetch today\'s cardiology report')
  }
}

export async function downloadArticle(articleId, titulo, url) {
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

export async function fetchReportHistory(dates) {
  const reports = {}
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
