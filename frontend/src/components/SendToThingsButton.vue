<!-- frontend/src/components/SendToThingsButton.vue -->
<!--
  Botão pequeno "Things" para enviar o item para o Things 3 (Cultured Code)
  via URL Scheme. Click → abre o app Things com tarefa pré-preenchida
  (título + notes + tag "cardiology").

  Funciona em iOS/iPadOS/macOS onde o Things está instalado. Em outras
  plataformas, o clique não faz nada (link é silenciosamente ignorado).

  Visual: amarelo claro (cor da marca Things) com ícone de checkbox.
-->
<template>
  <button
    @click.stop="handleClick"
    :title="tooltip"
    aria-label="Enviar para Things"
    class="inline-flex items-center gap-1.5 px-2.5 py-2 bg-yellow-100 text-yellow-900 hover:bg-yellow-200 active:bg-yellow-300 rounded-lg text-sm font-medium transition-all"
  >
    <svg
      xmlns="http://www.w3.org/2000/svg"
      class="w-4 h-4"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      stroke-width="2.5"
    >
      <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
    <span class="hidden sm:inline">Things</span>
  </button>
</template>

<script setup>
import { sendToThings } from '../utils/things.js'

const props = defineProps({
  item: { type: Object, required: true },
  type: {
    type: String,
    required: true,
    validator: (v) => ['artigo', 'noticia', 'pulso', 'video', 'discussao', 'substack'].includes(v)
  }
})

const tooltip = `Enviar para Things (lista 'cardiology')`

function handleClick() {
  sendToThings(props.item, props.type)
}
</script>
