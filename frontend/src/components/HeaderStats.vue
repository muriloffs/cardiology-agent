<!-- frontend/src/components/HeaderStats.vue -->
<template>
  <header class="bg-white border-b border-gray-200">
    <div class="max-w-6xl mx-auto px-4 py-3 md:py-6">
      <h1 class="text-xl md:text-4xl font-bold mb-1 md:mb-2">📚 Relatório de Cardiologia</h1>

      <div class="flex items-center gap-3 mb-2 md:mb-4">
        <button
          @click="$emit('prev')"
          :disabled="!hasPrev"
          class="p-1.5 rounded-lg transition-all disabled:opacity-30 disabled:cursor-not-allowed hover:bg-gray-100"
        >◀</button>
        <p class="text-gray-600 text-sm md:text-base font-medium">{{ formattedDate }}</p>
        <button
          @click="$emit('next')"
          :disabled="!hasNext"
          class="p-1.5 rounded-lg transition-all disabled:opacity-30 disabled:cursor-not-allowed hover:bg-gray-100"
        >▶</button>
      </div>

      <div class="grid grid-cols-3 gap-2 md:gap-4">
        <div class="bg-purple-50 rounded-lg p-2 md:p-4">
          <p class="text-xs md:text-sm text-gray-600">Artigos Hoje</p>
          <p class="text-xl md:text-2xl font-bold text-purple-600">{{ totalArticles }}</p>
        </div>
        <div class="bg-blue-50 rounded-lg p-2 md:p-4">
          <p class="text-xs md:text-sm text-gray-600">Tempo de Leitura</p>
          <p class="text-xl md:text-2xl font-bold text-blue-600">~{{ readingTime }}m</p>
        </div>
        <div class="bg-indigo-50 rounded-lg p-2 md:p-4">
          <p class="text-xs md:text-sm text-gray-600">Atualizado</p>
          <p class="text-base md:text-lg font-bold text-indigo-600">🔄</p>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  reportDate: String,
  totalArticles: Number,
  readingTime: Number,
  hasPrev: Boolean,
  hasNext: Boolean
})

defineEmits(['prev', 'next'])

const formattedDate = computed(() => {
  if (!props.reportDate) return 'Carregando...'
  const date = new Date(props.reportDate + 'T00:00:00')
  return date.toLocaleDateString('pt-BR', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
})
</script>
