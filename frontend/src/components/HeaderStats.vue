<!-- frontend/src/components/HeaderStats.vue -->
<template>
  <header class="bg-white border-b border-gray-200">
    <div class="max-w-6xl mx-auto px-4 py-3 md:py-6">
      <h1 class="text-xl md:text-4xl font-bold mb-1 md:mb-2">📚 Relatório de Cardiologia</h1>

      <div class="flex items-center gap-3 mb-2 md:mb-4">
        <button
          @click="$emit('prev')"
          :disabled="!hasPrev"
          class="flex-shrink-0 p-1.5 rounded-lg transition-all disabled:opacity-30 disabled:cursor-not-allowed hover:bg-gray-100"
        >◀</button>
        <p class="text-gray-600 font-medium min-w-0">
          <span class="hidden md:inline text-base">{{ formattedDate }}</span>
          <span class="md:hidden text-sm">{{ shortDate }}</span>
        </p>
        <button
          @click="$emit('next')"
          :disabled="!hasNext"
          class="flex-shrink-0 p-1.5 rounded-lg transition-all disabled:opacity-30 disabled:cursor-not-allowed hover:bg-gray-100"
        >▶</button>
      </div>

      <div class="grid grid-cols-2 md:grid-cols-4 gap-2 md:gap-3">
        <div class="bg-purple-50 rounded-lg p-2 md:p-4">
          <p class="text-xs md:text-sm text-gray-600">📚 Artigos</p>
          <p class="text-xl md:text-2xl font-bold text-purple-600">{{ totalArticles }}</p>
        </div>
        <div class="bg-orange-50 rounded-lg p-2 md:p-4">
          <p class="text-xs md:text-sm text-gray-600">📰 Notícias</p>
          <p class="text-xl md:text-2xl font-bold text-orange-600">{{ totalNoticias }}</p>
        </div>
        <div class="bg-red-50 rounded-lg p-2 md:p-4">
          <p class="text-xs md:text-sm text-gray-600">📺 Vídeos</p>
          <p class="text-xl md:text-2xl font-bold text-red-600">{{ totalVideos }}</p>
        </div>
        <div class="bg-gray-100 rounded-lg p-2 md:p-4">
          <p class="text-xs md:text-sm text-gray-600">𝕏 Discussões</p>
          <p class="text-xl md:text-2xl font-bold text-gray-800">{{ totalDiscussoes }}</p>
        </div>
      </div>
      <p class="text-xs text-gray-500 mt-2 md:mt-3">⏱️ Tempo de leitura: ~{{ readingTime }} min</p>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  reportDate: String,
  totalArticles: Number,
  totalNoticias: { type: Number, default: 0 },
  totalDiscussoes: { type: Number, default: 0 },
  totalVideos: { type: Number, default: 0 },
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
