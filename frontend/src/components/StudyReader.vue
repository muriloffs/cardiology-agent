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
import { ref, watch, computed, onMounted, onUnmounted } from 'vue'
import ReadToggle from './ReadToggle.vue'
import { useGrifos } from '../composables/useGrifos'

const props = defineProps({
  slug: { type: String, required: true },
  titulo: { type: String, default: '' },
})
const emit = defineEmits(['close'])

const grifos = useGrifos()
const articleEl = ref(null)
const selBtn = ref({ show: false, x: 0, y: 0, text: '' })
const flash = ref(false)

// Botão flutuante "Salvar grifo" quando há texto selecionado DENTRO do estudo.
// Captura o texto na hora (mesmo que o toque seguinte limpe a seleção no iOS).
function onSelChange() {
  const s = typeof window !== 'undefined' && window.getSelection ? window.getSelection() : null
  const txt = s ? s.toString().trim() : ''
  if (!txt || !s.rangeCount || !articleEl.value) { selBtn.value.show = false; return }
  const range = s.getRangeAt(0)
  if (!articleEl.value.contains(range.commonAncestorContainer)) { selBtn.value.show = false; return }
  const r = range.getBoundingClientRect()
  if (!r || (r.width === 0 && r.height === 0)) { selBtn.value.show = false; return }
  selBtn.value = { show: true, x: r.left + r.width / 2, y: r.top, text: txt }
}

async function salvarGrifo() {
  const txt = selBtn.value.text
  selBtn.value.show = false
  try {
    await grifos.add(txt, props.slug, props.titulo)
    window.getSelection()?.removeAllRanges()
    flash.value = true
    setTimeout(() => { flash.value = false }, 1500)
  } catch {
    alert('Não consegui salvar o grifo. Tente de novo.')
  }
}

onMounted(() => document.addEventListener('selectionchange', onSelChange))
onUnmounted(() => document.removeEventListener('selectionchange', onSelChange))

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
    html.value = renderStudyMarkdown(md, baseUrl.value)
  } catch (e) {
    error.value = e?.message || 'Falha ao carregar o estudo'
  } finally {
    loading.value = false
  }
}

watch(() => props.slug, load, { immediate: true })
</script>

<template>
  <div class="study-reader">
    <button class="study-close" @click="emit('close')">← Voltar</button>
    <div v-if="loading" class="study-status">Carregando…</div>
    <div v-else-if="error" class="study-status study-error">{{ error }}</div>
    <template v-else>
      <article ref="articleEl" class="study-body" v-html="html"></article>
      <div class="mark-row"><ReadToggle :id="'estudo:' + slug" /></div>
    </template>

    <!-- Botão flutuante: aparece ao selecionar texto do estudo -->
    <button
      v-if="selBtn.show && grifos.hasToken()"
      class="grifo-fab"
      :style="{ left: selBtn.x + 'px', top: (selBtn.y - 46) + 'px' }"
      @mousedown.prevent
      @click="salvarGrifo"
    >✚ Salvar grifo</button>
    <div v-if="flash" class="grifo-flash">Grifo salvo ✓</div>
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
.grifo-fab {
  position: fixed; transform: translateX(-50%); z-index: 50;
  background: #7c3aed; color: #fff; font-weight: 600; font-size: 0.85rem;
  padding: 0.45rem 0.85rem; border: none; border-radius: 999px;
  box-shadow: 0 2px 8px rgba(0,0,0,.25); cursor: pointer; white-space: nowrap;
}
.grifo-flash {
  position: fixed; bottom: 1.5rem; left: 50%; transform: translateX(-50%); z-index: 50;
  background: #111827; color: #fff; font-size: 0.85rem; padding: 0.5rem 1rem;
  border-radius: 999px; box-shadow: 0 2px 8px rgba(0,0,0,.3);
}
</style>
