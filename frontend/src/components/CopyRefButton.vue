<script setup>
import { ref } from 'vue'

// Copia "Título oficial — DOI (ou link)" pra você colar no Google e achar o
// artigo caso o link não funcione.
const props = defineProps({
  titulo: { type: String, default: '' },
  doi: { type: String, default: '' },
  url: { type: String, default: '' },
})

const copied = ref(false)
async function copiar() {
  const ref = [props.titulo, props.doi || props.url].filter(Boolean).join(' — ')
  if (!ref) return
  try {
    await navigator.clipboard.writeText(ref)
    copied.value = true
    setTimeout(() => { copied.value = false }, 1500)
  } catch {
    window.prompt('Copie a referência (Ctrl/Cmd+C):', ref)
  }
}
</script>

<template>
  <button
    @click.stop="copiar"
    class="inline-flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-md border border-gray-300 text-gray-500 bg-white hover:border-blue-300 transition-colors"
    title="Copiar título + DOI para buscar no Google"
  >
    {{ copied ? '✓ Copiado' : '📋 Copiar ref.' }}
  </button>
</template>
