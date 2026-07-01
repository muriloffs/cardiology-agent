// Casamento best-effort de títulos PT (Revisão x Estudo). Os estudos não guardam
// DOI/PMID — só o título traduzido — então comparamos títulos normalizados.

export function normTitulo(s) {
  return (s || '')
    .normalize('NFKD').replace(/[̀-ͯ]/g, '')   // remove acentos
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
}

function tokens(norm) {
  return new Set(norm.split(' ').filter((w) => w.length > 3))
}

// Duas versões PT do mesmo artigo (mesma IA) tendem a bater; toleramos variação
// com substring OU sobreposição de palavras (Jaccard >= 0.6).
export function casaTitulo(a, b) {
  const na = normTitulo(a)
  const nb = normTitulo(b)
  if (!na || !nb) return false
  if (na === nb || na.includes(nb) || nb.includes(na)) return true
  const ta = tokens(na)
  const tb = tokens(nb)
  if (!ta.size || !tb.size) return false
  let inter = 0
  ta.forEach((w) => { if (tb.has(w)) inter++ })
  const uni = new Set([...ta, ...tb]).size
  return uni > 0 && inter / uni >= 0.6
}
