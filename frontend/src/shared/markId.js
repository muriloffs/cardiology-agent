// ID canônico de marca/favorito por tipo de conteúdo. Usado pelos cards E pelo
// "marcar tudo como lido", garantindo que os dois lados gerem o mesmo id.
//
// IMPORTANTE: NUNCA usar o campo `id` do item — ele é POSICIONAL (art_001,
// not_001, pulso_001...) e se REPETE em todos os dias. Usar o id posicional
// fazia "marcar o artigo 1 de hoje" marcar o artigo 1 de TODO dia passado.
// Usamos a URL/DOI/título, que identificam o conteúdo de fato (e marcar um
// artigo o marca onde quer que ele apareça — que é o comportamento certo).
export function markId(type, item) {
  switch (type) {
    case 'estudo':    return 'estudo:' + item.slug
    case 'artigo':    return 'artigo:' + (item.links?.url || item.links?.doi || item.titulo)
    case 'noticia':   return 'noticia:' + (item.links?.url || item.titulo)
    case 'video':     return 'video:' + (item.video_url || item.titulo)
    case 'pulso':     return 'pulso:' + item.titulo
    case 'substack':  return 'substack:' + (item.url || item.titulo)
    case 'discussao': return 'discussao:' + (item.links?.url || item.titulo)
    case 'imagem':    return 'imagem:' + item.image_url
    default:          return type + ':' + (item.titulo || '')
  }
}
