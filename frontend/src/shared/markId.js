// ID canônico de marca/favorito por tipo de conteúdo. Usado pelos cards E pelo
// "marcar tudo como lido", garantindo que os dois lados gerem o mesmo id.
export function markId(type, item) {
  switch (type) {
    case 'estudo':    return 'estudo:' + item.slug
    case 'artigo':    return 'artigo:' + (item.id || item.links?.url || item.titulo)
    case 'noticia':   return 'noticia:' + (item.id || item.links?.url || item.titulo)
    case 'video':     return 'video:' + (item.video_url || item.id)
    case 'pulso':     return 'pulso:' + (item.id || item.titulo)
    case 'substack':  return 'substack:' + (item.id || item.url)
    case 'discussao': return 'discussao:' + (item.id || item.url)
    case 'imagem':    return 'imagem:' + item.image_url
    default:          return type + ':' + (item.id || item.titulo || '')
  }
}
