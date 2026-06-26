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
  const raw = marked.parse(md || '', { renderer })
  return DOMPurify.sanitize(raw, { ADD_ATTR: ['class'] })
}
</script>

<script setup>
import { ref, watch, computed } from 'vue'

const props = defineProps({ slug: { type: String, required: true } })
const emit = defineEmits(['close'])

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
    <article v-else class="study-body" v-html="html"></article>
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
</style>
