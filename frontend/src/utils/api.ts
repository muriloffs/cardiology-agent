// frontend/src/utils/api.ts
import axios from 'axios'

const GITHUB_RAW_URL = 'https://raw.githubusercontent.com/muriloffs/cardiology-agent/main/data'

/**
 * Cache-busting query param. GitHub raw serves files with `Cache-Control:
 * max-age=300` AND sits behind Fastly's CDN — both can serve a stale view
 * (an old report, or a 404 cached before today's file was committed).
 * A fresh `?t=` value each page load forces browser + CDN to revalidate.
 */
function bust(): string {
  return `?t=${Date.now()}`
}

/**
 * Fetch the most recent report.
 *
 * Strategy: read `index.json` (the source of truth — the daily workflow
 * rewrites it listing exactly which reports exist, newest first) and fetch
 * `dates[0]`. This never requests a non-existent file, so there are no 404s
 * to get cached by the browser or CDN — which is what made the site appear
 * "stuck" on an old report.
 *
 * Fallback: if index.json is unreachable, probe dates backwards from today.
 */
export async function fetchLatestReport() {
  try {
    const indexResp = await axios.get(`${GITHUB_RAW_URL}/index.json${bust()}`)
    const dates: string[] = indexResp.data?.dates || []
    if (dates.length > 0) {
      const latest = dates[0] // index.json is sorted newest-first
      const reportResp = await axios.get(`${GITHUB_RAW_URL}/relatorio-${latest}.json${bust()}`)
      return reportResp.data
    }
  } catch (error) {
    console.warn('index.json lookup failed, falling back to date probing:', error)
  }

  // Fallback: probe dates backwards (legacy behavior, kept for resilience).
  for (let daysBack = 0; daysBack < 7; daysBack++) {
    const date = new Date()
    date.setDate(date.getDate() - daysBack)
    const dateStr = date.getFullYear() + '-' +
      String(date.getMonth() + 1).padStart(2, '0') + '-' +
      String(date.getDate()).padStart(2, '0')
    try {
      const response = await axios.get(`${GITHUB_RAW_URL}/relatorio-${dateStr}.json${bust()}`)
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

export async function fetchIndex(): Promise<string[]> {
  try {
    const response = await axios.get(`${GITHUB_RAW_URL}/index.json${bust()}`)
    return response.data.dates || []
  } catch {
    return []
  }
}

export async function fetchReportByDate(date: string) {
  // Past reports are immutable; today's may have just been committed —
  // cache-bust keeps "navigate to latest" consistent with fetchLatestReport.
  const response = await axios.get(`${GITHUB_RAW_URL}/relatorio-${date}.json${bust()}`)
  return response.data
}
