// frontend/src/data/congresses.ts
//
// Static list of major cardiology congresses for 2026. Used by CongressBanner
// to surface "acontecendo agora" and "próximo congresso" badges. When a major
// congress is happening, the dashboard's content landscape shifts dramatically
// (late-breaking trials, more X buzz, more press releases) — the banner
// contextualizes that for the user.
//
// To add 2027 dates: append below. Past entries can stay — the computed in
// CongressBanner only surfaces active/upcoming ones.

export interface Congress {
  slug: string
  name: string
  shortName: string
  emoji: string
  startDate: string   // YYYY-MM-DD
  endDate: string     // YYYY-MM-DD inclusive
  location: string
  city: string
  focus: string       // e.g. "Heart Failure", "Intervenção"
  category: 'general' | 'hf' | 'arrhythmia' | 'interventional' | 'imaging' | 'prevention' | 'diabetes' | 'regional'
  hashtags: string[]
}

export const CONGRESSES_2026: Congress[] = [
  {
    slug: 'acc26',
    name: 'ACC.26 — American College of Cardiology',
    shortName: 'ACC.26',
    emoji: '🇺🇸',
    startDate: '2026-03-28', endDate: '2026-03-30',
    location: 'Nova Orleans, LA, EUA', city: 'Nova Orleans',
    focus: 'Cardiologia Geral · Late-breaking trials',
    category: 'general',
    hashtags: ['ACC26', 'ACC2026'],
  },
  {
    slug: 'ehra26',
    name: 'EHRA 2026 — European Heart Rhythm Association',
    shortName: 'EHRA 2026',
    emoji: '⚡',
    startDate: '2026-04-12', endDate: '2026-04-14',
    location: 'Paris, França', city: 'Paris',
    focus: 'Arritmias · Eletrofisiologia',
    category: 'arrhythmia',
    hashtags: ['EHRA2026', 'EPeeps'],
  },
  {
    slug: 'hrs26',
    name: 'HRS 2026 — Heart Rhythm Society',
    shortName: 'HRS 2026',
    emoji: '⚡',
    startDate: '2026-04-23', endDate: '2026-04-26',
    location: 'Chicago, IL, EUA', city: 'Chicago',
    focus: 'Arritmias · Eletrofisiologia',
    category: 'arrhythmia',
    hashtags: ['HRS2026', 'HRS26'],
  },
  {
    slug: 'hfa26',
    name: 'Heart Failure 2026 — HFA Congress',
    shortName: 'HFA 2026',
    emoji: '💔',
    startDate: '2026-05-09', endDate: '2026-05-12',
    location: 'Barcelona, Espanha', city: 'Barcelona',
    focus: 'Insuficiência Cardíaca',
    category: 'hf',
    hashtags: ['HeartFailure2026', 'HFA2026'],
  },
  {
    slug: 'europcr26',
    name: 'EuroPCR 2026',
    shortName: 'EuroPCR 2026',
    emoji: '🔧',
    startDate: '2026-05-19', endDate: '2026-05-22',
    location: 'Paris, França', city: 'Paris',
    focus: 'Cardiologia Intervencionista · Dispositivos',
    category: 'interventional',
    hashtags: ['EuroPCR2026', 'EuroPCR26'],
  },
  {
    slug: 'socesp26',
    name: 'SOCESP 2026 — Sociedade Cardiologia de SP',
    shortName: 'SOCESP 2026',
    emoji: '🇧🇷',
    startDate: '2026-06-04', endDate: '2026-06-06',
    location: 'São Paulo, SP, Brasil', city: 'São Paulo',
    focus: 'Cardiologia Brasileira · Maior congresso regional do mundo',
    category: 'regional',
    hashtags: ['SOCESP2026'],
  },
  {
    slug: 'ada26',
    name: 'ADA Scientific Sessions 2026',
    shortName: 'ADA 2026',
    emoji: '🩸',
    startDate: '2026-06-05', endDate: '2026-06-08',
    location: 'Nova Orleans, LA, EUA', city: 'Nova Orleans',
    focus: 'Diabetes · GLP-1 · SGLT2',
    category: 'diabetes',
    hashtags: ['ADA2026'],
  },
  {
    slug: 'ase26',
    name: 'ASE 2026 — American Society of Echocardiography',
    shortName: 'ASE 2026',
    emoji: '🫀',
    startDate: '2026-06-26', endDate: '2026-06-28',
    location: 'Aurora, CO, EUA', city: 'Aurora',
    focus: 'Ecocardiografia · Imagem',
    category: 'imaging',
    hashtags: ['ASE2026', 'EchoFirst'],
  },
  {
    slug: 'heartuk26',
    name: 'HEART UK / IAS 2026',
    shortName: 'HEART UK 2026',
    emoji: '🧪',
    startDate: '2026-06-30', endDate: '2026-07-02',
    location: 'Nottingham, Reino Unido', city: 'Nottingham',
    focus: 'Dislipidemia · Aterosclerose',
    category: 'prevention',
    hashtags: ['HEARTUK2026'],
  },
  {
    slug: 'aspc26',
    name: 'ASPC 2026 — Preventive Cardiology',
    shortName: 'ASPC 2026',
    emoji: '🛡️',
    startDate: '2026-07-24', endDate: '2026-07-26',
    location: 'San Antonio, TX, EUA', city: 'San Antonio',
    focus: 'Prevenção · Dislipidemia',
    category: 'prevention',
    hashtags: ['ASPC2026'],
  },
  {
    slug: 'esc26',
    name: 'ESC Congress 2026 — European Society of Cardiology',
    shortName: 'ESC 2026',
    emoji: '🇪🇺',
    startDate: '2026-08-28', endDate: '2026-08-31',
    location: 'Munique, Alemanha (+ Online)', city: 'Munique',
    focus: 'Cardiologia Geral · Late-breaking trials',
    category: 'general',
    hashtags: ['ESCcongress2026', 'ESC2026'],
  },
  {
    slug: 'wcc-sbc26',
    name: 'WCC 2026 + 81º Congresso Brasileiro de Cardiologia',
    shortName: 'WCC + SBC 2026',
    emoji: '🌎',
    startDate: '2026-10-08', endDate: '2026-10-10',
    location: 'Rio de Janeiro, RJ, Brasil (Riocentro)', city: 'Rio de Janeiro',
    focus: 'Mundial + Brasil · Conferência conjunta histórica',
    category: 'general',
    hashtags: ['WCC2026', 'CongressoSBC', 'SBC2026'],
  },
  {
    slug: 'hfsa26',
    name: 'HFSA 2026 — Heart Failure Society of America',
    shortName: 'HFSA 2026',
    emoji: '💔',
    startDate: '2026-10-09', endDate: '2026-10-12',
    location: 'Phoenix, AZ, EUA', city: 'Phoenix',
    focus: 'Insuficiência Cardíaca',
    category: 'hf',
    hashtags: ['HFSA2026'],
  },
  {
    slug: 'tct26',
    name: 'TCT 2026 — Transcatheter Cardiovascular Therapeutics',
    shortName: 'TCT 2026',
    emoji: '🔧',
    startDate: '2026-10-31', endDate: '2026-11-03',
    location: 'San Diego, CA, EUA', city: 'San Diego',
    focus: 'Intervenção · Terapias Transcateter',
    category: 'interventional',
    hashtags: ['TCT2026'],
  },
  {
    slug: 'aha26',
    name: 'AHA Scientific Sessions 2026',
    shortName: 'AHA 2026',
    emoji: '🇺🇸',
    startDate: '2026-11-06', endDate: '2026-11-09',
    location: 'Chicago, IL, EUA', city: 'Chicago',
    focus: 'Cardiologia Geral · Late-breaking trials',
    category: 'general',
    hashtags: ['AHA2026'],
  },
  {
    slug: 'eacvi26',
    name: 'EACVI 2026 — European Cardiovascular Imaging',
    shortName: 'EACVI 2026',
    emoji: '📷',
    startDate: '2026-12-03', endDate: '2026-12-05',
    location: 'Milão, Itália', city: 'Milão',
    focus: 'Imagem · Echo · CMR · CT (unificado)',
    category: 'imaging',
    hashtags: ['EACVI2026', 'CVImaging'],
  },
]

// Color palette per category — drives banner accent color.
export const CATEGORY_COLORS: Record<Congress['category'], { bg: string; text: string; ring: string }> = {
  general:        { bg: 'bg-purple-50',   text: 'text-purple-900',   ring: 'ring-purple-300' },
  hf:             { bg: 'bg-rose-50',     text: 'text-rose-900',     ring: 'ring-rose-300' },
  arrhythmia:     { bg: 'bg-yellow-50',   text: 'text-yellow-900',   ring: 'ring-yellow-300' },
  interventional: { bg: 'bg-orange-50',   text: 'text-orange-900',   ring: 'ring-orange-300' },
  imaging:        { bg: 'bg-cyan-50',     text: 'text-cyan-900',     ring: 'ring-cyan-300' },
  prevention:     { bg: 'bg-emerald-50',  text: 'text-emerald-900',  ring: 'ring-emerald-300' },
  diabetes:       { bg: 'bg-pink-50',     text: 'text-pink-900',     ring: 'ring-pink-300' },
  regional:       { bg: 'bg-green-50',    text: 'text-green-900',    ring: 'ring-green-300' },
}

/**
 * Returns congresses split into: currently active, starting in the next 14 days,
 * and recently ended (last 3 days, optional context). Today is treated in
 * America/Sao_Paulo timezone (Brasília).
 */
export function classifyCongresses(today: Date = new Date()) {
  const todayStr = formatLocalDate(today)
  const active: Congress[] = []
  const upcoming: { c: Congress; daysAway: number }[] = []

  for (const c of CONGRESSES_2026) {
    if (todayStr >= c.startDate && todayStr <= c.endDate) {
      active.push(c)
      continue
    }
    if (c.startDate > todayStr) {
      const daysAway = daysBetween(todayStr, c.startDate)
      if (daysAway <= 14) {
        upcoming.push({ c, daysAway })
      }
    }
  }
  upcoming.sort((a, b) => a.daysAway - b.daysAway)
  return { active, upcoming: upcoming.slice(0, 2) }
}

function formatLocalDate(d: Date): string {
  // YYYY-MM-DD in local time
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function daysBetween(a: string, b: string): number {
  const [ya, ma, da] = a.split('-').map(Number)
  const [yb, mb, db] = b.split('-').map(Number)
  const dateA = new Date(ya, ma - 1, da)
  const dateB = new Date(yb, mb - 1, db)
  return Math.round((dateB.getTime() - dateA.getTime()) / 86400000)
}

/** Day number within congress (1-indexed). E.g., day 2 of 4 of HFA. */
export function dayOfCongress(c: Congress, today: Date = new Date()): { current: number; total: number } {
  const todayStr = formatLocalDate(today)
  const total = daysBetween(c.startDate, c.endDate) + 1
  const current = daysBetween(c.startDate, todayStr) + 1
  return { current: Math.max(1, Math.min(current, total)), total }
}
