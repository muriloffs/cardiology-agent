<!-- frontend/src/components/HeaderStats.vue -->
<template>
  <header class="sticky top-0 bg-white border-b border-gray-200 z-40">
    <div class="max-w-6xl mx-auto px-4 py-6">
      <h1 class="text-4xl font-bold mb-2">📚 Relatório de Cardiologia</h1>
      <p class="text-gray-600 mb-4">{{ formattedDate }}</p>

      <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
        <div class="bg-purple-50 rounded-lg p-4">
          <p class="text-sm text-gray-600">Artigos Hoje</p>
          <p class="text-2xl font-bold text-purple-600">{{ totalArticles }}</p>
        </div>
        <div class="bg-blue-50 rounded-lg p-4">
          <p class="text-sm text-gray-600">Tempo de Leitura</p>
          <p class="text-2xl font-bold text-blue-600">~{{ readingTime }}m</p>
        </div>
        <div class="bg-indigo-50 rounded-lg p-4">
          <p class="text-sm text-gray-600">Atualizado</p>
          <p class="text-lg font-bold text-indigo-600">🔄</p>
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
  readingTime: Number
})

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
