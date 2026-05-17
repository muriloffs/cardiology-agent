<!-- frontend/src/components/ShareButton.vue -->
<!--
  Botão "Compartilhar" usando Web Share API (nativo iOS/Android/macOS).
  Em desktop sem suporte, copia texto formatado para clipboard com toast.

  Caso de uso especial — NotebookLM no iPhone:
  o app NotebookLM (iOS) registra-se como destination no share sheet do sistema.
  Click aqui → share sheet → escolhe NotebookLM → URL vai como source automaticamente.
  Single botão cobre WhatsApp, Mail, AirDrop, NotebookLM, Pocket, etc.
-->
<template>
  <div class="relative inline-flex">
    <button
      @click.stop="handleShare"
      :title="tooltip"
      aria-label="Compartilhar"
      class="inline-flex items-center gap-1.5 px-2.5 py-2 bg-sky-100 text-sky-900 hover:bg-sky-200 active:bg-sky-300 rounded-lg text-sm font-medium transition-all"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        class="w-4 h-4"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        stroke-width="2.5"
      >
        <!-- Standard share icon: arrow exiting a box -->
        <path stroke-linecap="round" stroke-linejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M16 6l-4-4m0 0L8 6m4-4v12" />
      </svg>
      <span class="hidden sm:inline">Compartilhar</span>
    </button>

    <!-- Toast: appears only when clipboard fallback was used or share failed -->
    <transition
      enter-active-class="transition-all duration-200 ease-out"
      enter-from-class="opacity-0 translate-y-1"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition-all duration-200 ease-in"
      leave-from-class="opacity-100 translate-y-0"
      leave-to-class="opacity-0 translate-y-1"
    >
      <div
        v-if="toast"
        :class="[
          'absolute right-0 -bottom-10 z-10 px-2.5 py-1 text-xs font-medium rounded shadow-md whitespace-nowrap',
          toast.kind === 'ok' ? 'bg-emerald-600 text-white' : 'bg-rose-600 text-white'
        ]"
      >
        {{ toast.text }}
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { shareItem } from '../utils/share.js'

const props = defineProps({
  item: { type: Object, required: true },
  type: {
    type: String,
    required: true,
    validator: (v) => ['artigo', 'noticia', 'pulso', 'video', 'discussao', 'substack'].includes(v)
  }
})

const tooltip = 'Compartilhar via WhatsApp / Mail / NotebookLM / AirDrop / etc.'

const toast = ref(null)
let toastTimer = null

function showToast(kind, text, durationMs = 2200) {
  if (toastTimer) clearTimeout(toastTimer)
  toast.value = { kind, text }
  toastTimer = setTimeout(() => { toast.value = null }, durationMs)
}

async function handleShare() {
  const result = await shareItem(props.item, props.type)
  if (result === 'copied') {
    showToast('ok', '✓ Link copiado!')
  } else if (result === 'failed') {
    showToast('err', 'Falha ao compartilhar')
  }
  // 'shared' (native sheet) and 'cancelled' (user dismissed) → no toast
}
</script>
