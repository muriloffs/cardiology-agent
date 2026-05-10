<!-- frontend/src/components/HeaderStats.vue -->
<!--
  Streamlined header: title + date navigator + reading time.
  Per-category counters (Artigos/Notícias/Vídeos/Discussões) were removed
  because they duplicate the tab buttons below (which show counts AND
  navigate). Sub-section counts inside Relatório still live in FilterBar.
-->
<template>
  <header class="bg-white border-b border-gray-200">
    <div class="max-w-6xl mx-auto px-4 py-3 md:py-5">
      <h1 class="text-xl md:text-3xl font-bold mb-1 md:mb-2">📚 Relatório de Cardiologia</h1>

      <div class="flex items-center gap-3">
        <button
          @click="$emit('prev')"
          :disabled="!hasPrev"
          class="flex-shrink-0 p-1.5 rounded-lg transition-all disabled:opacity-30 disabled:cursor-not-allowed hover:bg-gray-100"
        >◀</button>
        <p class="text-gray-600 font-medium min-w-0 flex-1">
          <span class="hidden md:inline text-base">{{ formattedDate }}</span>
          <span class="md:hidden text-sm">{{ shortDate }}</span>
          <span v-if="readingTime" class="text-xs text-gray-400 ml-2">· ⏱️ ~{{ readingTime }} min</span>
        </p>
        <button
          @click="$emit('next')"
          :disabled="!hasNext"
          class="flex-shrink-0 p-1.5 rounded-lg transition-all disabled:opacity-30 disabled:cursor-not-allowed hover:bg-gray-100"
        >▶</button>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  reportDate: String,
  readingTime: Number,
  hasPrev: Boolean,
  hasNext: Boolean
})

defineEmits(['prev', 'next'])

const formattedDate = computed(() => {
  if (!props.reportDate) return 'Carregando...'
  const date = new Date(props.reportDate + 'T00:00:00')
  return date.toLocaleDateString('pt-BR', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })
})

const shortDate = computed(() => {
  if (!props.reportDate) return '...'
  const date = new Date(props.reportDate + 'T00:00:00')
  return date.toLocaleDateString('pt-BR', { weekday: 'short', day: 'numeric', month: 'short' })
})
</script>
