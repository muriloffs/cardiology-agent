<script>
import { marked } from 'marked'
import DOMPurify from 'dompurify'

// Funcao pura (testavel): markdown -> HTML sanitizado, com camada de estudo
// marcada e src de imagem reescrito para a base raw do estudo.
export function renderStudyMarkdown(md, baseUrl) {
  const renderer = new marked.Renderer()
  const baseBlockquote = renderer.blockquote.bind(renderer)
  renderer.blockquote = (quote) => {
    const html = baseBlockquote(quote)
    if (quote.includes('🎓')) {
      return html.replace('<blockquote>', '<blockquote class="study-layer">')
    }
    return html
  }
  const baseImage = renderer.image.bind(renderer)
  renderer.image = (href, title, text) => {
    const abs = /^https?:\/\//.test(href) ? href : baseUrl + href
    return baseImage(abs, title, text)
  }
  // Links abrem em NOVA ABA (para nao perder o estudo ao clicar num DOI/busca)
  const baseLink = renderer.link.bind(renderer)
  renderer.link = (href, title, text) => {
    const html = baseLink(href, title, text)
    return html.replace(/^<a /, '<a target="_blank" rel="noopener noreferrer" ')
  }
  const raw = marked.parse(md || '', { renderer })
  return DOMPurify.sanitize(raw, { ADD_ATTR: ['class', 'target', 'rel'] })
}
</script>

<script setup>
import { ref, watch, computed } from 'vue'
import ReadToggle from './ReadToggle.vue'
import { useGrifos } from '../composables/useGrifos'
import { toPng } from 'html-to-image'

const props = defineProps({
  slug: { type: String, required: true },
  titulo: { type: String, default: '' },
})
const emit = defineEmits(['close'])

const grifos = useGrifos()
const flash = ref('')
const metaTitulo = ref('')   // título confiável do estudo (independe do mês na lista)

// Salvar grifo AUTOMÁTICO: lê o trecho que você COPIOU (selecione → "Copiar" →
// toque no botão). No iOS aparece um "Colar" rápido a confirmar; depois salva
// sozinho e vai pra aba "Salvos". Se a leitura do clipboard não rolar (navegador
// antigo/negado), cai no colar manual.
async function salvarGrifo() {
  let txt = ''
  try {
    txt = (await navigator.clipboard.readText() || '').trim()
  } catch {
    txt = (window.prompt('Cole aqui o trecho que você copiou:') || '').trim()
  }
  if (!txt) {
    alert('Primeiro selecione um trecho do estudo e toque em "Copiar". Depois toque em Salvar grifo.')
    return
  }
  try {
    await grifos.add(txt, props.slug, props.titulo || metaTitulo.value || props.slug)
    flash.value = 'Grifo salvo: "' + txt.slice(0, 34) + (txt.length > 34 ? '…' : '') + '"'
    setTimeout(() => { flash.value = '' }, 2200)
  } catch {
    alert('Não consegui salvar o grifo. Tente de novo.')
  }
}

// Salvar TABELA como imagem (figuras já salvam com long-press nativo no iOS).
// O botão é injetado após cada <table> no HTML do estudo; o clique é capturado
// por delegação no container.
const tableImg = ref(null)
async function onReaderClick(e) {
  const btn = e.target.closest ? e.target.closest('.tbl-save') : null
  if (!btn) return
  const table = btn.parentElement?.previousElementSibling
  if (!table || table.tagName !== 'TABLE') return
  const label = btn.textContent
  btn.textContent = 'Gerando…'
  try {
    tableImg.value = await toPng(table, { backgroundColor: '#ffffff', pixelRatio: 2 })
  } catch {
    alert('Não consegui gerar a imagem da tabela.')
  } finally {
    btn.textContent = label
  }
}

const RAW_BASE = 'https://raw.githubusercontent.com/muriloffs/cardiology-agent/main/data/estudos/'
const html = ref('')
const loading = ref(false)
const error = ref(null)
const baseUrl = computed(() => `${RAW_BASE}${props.slug}/`)

async function load() {
  loading.value = true
  error.value = null
  try {
    const resp = await fetch(`${baseUrl.value}estudo.md?t=${Date.now()}`)
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const md = await resp.text()
    // Injeta um botão "salvar como imagem" após cada tabela (já sanitizado).
    html.value = renderStudyMarkdown(md, baseUrl.value).replace(
      /<\/table>/g,
      '</table><div class="tbl-save-wrap"><button type="button" class="tbl-save">⤓ Salvar tabela como imagem</button></div>'
    )
    // Título confiável (p/ os grifos saírem com o nome certo do artigo nos Salvos)
    try {
      const mr = await fetch(`${baseUrl.value}meta.json?t=${Date.now()}`)
      if (mr.ok) metaTitulo.value = (await mr.json()).titulo || ''
    } catch { /* o título via prop continua valendo */ }
  } catch (e) {
    error.value = e?.message || 'Falha ao carregar o estudo'
  } finally {
    loading.value = false
  }
}

watch(() => props.slug, load, { immediate: true })
</script>

<template>
  <div class="study-reader" @click="onReaderClick">
    <button class="study-close" @click="emit('close')">← Voltar</button>
    <div v-if="loading" class="study-status">Carregando…</div>
    <div v-else-if="error" class="study-status study-error">{{ error }}</div>
    <template v-else>
      <article class="study-body" v-html="html"></article>
      <div class="mark-row"><ReadToggle :id="'estudo:' + slug" /></div>
    </template>

    <!-- Botão fixo: copie um trecho e toque aqui (não compete com o menu do iOS) -->
    <button
      v-if="grifos.hasToken() && !loading && !error"
      class="grifo-fab-fixed"
      @click="salvarGrifo"
      title="Copie um trecho do estudo e toque para grifar"
    >🖍 Salvar grifo</button>
    <div v-if="flash" class="grifo-flash">{{ flash }}</div>

    <!-- Overlay da tabela como imagem: segure para salvar nas Fotos -->
    <div v-if="tableImg" class="img-overlay" @click.self="tableImg = null">
      <button class="img-overlay-close" @click="tableImg = null" aria-label="Fechar">✕</button>
      <img :src="tableImg" class="img-overlay-img" alt="Tabela" />
      <p class="img-overlay-hint">📲 Segure a imagem → "Adicionar às Fotos" · ou <a :href="tableImg" download="tabela.png">baixar</a></p>
    </div>
  </div>
</template>

<style scoped>
.study-reader { max-width: 760px; margin: 0 auto; padding: 1rem 1.25rem 4rem; }
.study-close { margin-bottom: 1rem; font-size: 0.95rem; color: #2563eb; background: none; border: none; cursor: pointer; }
.study-status { padding: 2rem 0; color: #6b7280; }
.study-error { color: #b91c1c; }
.study-body { line-height: 1.75; font-size: 1.05rem; color: #1f2937; }
.study-body :deep(h2) { margin-top: 2rem; font-size: 1.4rem; font-weight: 700; }
.study-body :deep(table) { border-collapse: collapse; width: 100%; margin: 1rem 0; }
.study-body :deep(th), .study-body :deep(td) { border: 1px solid #e5e7eb; padding: 0.5rem 0.75rem; text-align: left; }
.study-body :deep(img) { max-width: 100%; border-radius: 8px; margin: 1rem 0; }
.study-body :deep(.study-layer) {
  background: #f5f3ff; border-left: 4px solid #8b5cf6; border-radius: 8px;
  padding: 0.75rem 1rem; margin: 1.25rem 0; color: #4c1d95;
}
.mark-row { margin-top: 2.5rem; }
.grifo-fab-fixed {
  position: fixed; left: 1rem; bottom: 1.5rem; z-index: 50;
  background: #7c3aed; color: #fff; font-weight: 600; font-size: 0.9rem;
  padding: 0.6rem 1rem; border: none; border-radius: 999px;
  box-shadow: 0 2px 10px rgba(0,0,0,.3); cursor: pointer; white-space: nowrap;
}
.grifo-fab-fixed:active { background: #6d28d9; }
.grifo-flash {
  position: fixed; bottom: 1.5rem; left: 50%; transform: translateX(-50%); z-index: 50;
  background: #111827; color: #fff; font-size: 0.85rem; padding: 0.5rem 1rem;
  border-radius: 999px; box-shadow: 0 2px 8px rgba(0,0,0,.3);
}
.study-body :deep(.tbl-save-wrap) { margin: -0.5rem 0 1.25rem; }
.study-body :deep(.tbl-save) {
  font-size: 0.8rem; color: #0f766e; background: #f0fdfa; border: 1px solid #99f6e4;
  padding: 0.3rem 0.7rem; border-radius: 8px; cursor: pointer;
}
.study-body :deep(.tbl-save):hover { background: #ccfbf1; }
.img-overlay {
  position: fixed; inset: 0; z-index: 9999; background: rgba(0,0,0,.9);
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 1rem; gap: 0.75rem;
}
.img-overlay-close {
  position: absolute; top: 0.75rem; right: 0.75rem; color: rgba(255,255,255,.85);
  background: rgba(255,255,255,.12); border: none; font-size: 1.4rem; width: 2.75rem;
  height: 2.75rem; border-radius: 999px; cursor: pointer;
}
.img-overlay-img { max-width: 100%; max-height: 80vh; object-fit: contain; background: #fff; border-radius: 8px; }
.img-overlay-hint { color: rgba(255,255,255,.85); font-size: 0.85rem; text-align: center; }
.img-overlay-hint a { color: #5eead4; text-decoration: underline; }
</style>
