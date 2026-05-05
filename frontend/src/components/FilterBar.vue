<!-- frontend/src/components/FilterBar.vue -->
<template>
  <div class="bg-white border-b border-gray-200">
    <div class="max-w-6xl mx-auto px-4 py-4">
      <!-- Class Filters -->
      <div class="mb-4">
        <p class="text-sm font-semibold text-gray-700 mb-2">Classe</p>
        <div class="flex gap-2 flex-wrap">
          <button
            v-for="cls in ['all', 'A', 'B', 'C']"
            :key="cls"
            @click="$emit('update:selected-class', cls)"
            :class="[
              'px-4 py-2 rounded-full text-sm font-medium transition-all',
              selectedClass === cls
                ? cls === 'all'
                  ? 'bg-purple-600 text-white'
                  : cls === 'A'
                  ? 'bg-red-600 text-white'
                  : cls === 'B'
                  ? 'bg-orange-600 text-white'
                  : 'bg-green-600 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            ]"
          >
            {{ cls === 'all' ? 'Todas' : `Classe ${cls}` }}
          </button>
        </div>
      </div>

      <!-- Section Navigation -->
      <div class="mb-4">
        <p class="text-sm font-semibold text-gray-700 mb-2">Ir para</p>
        <div class="flex gap-2 flex-wrap">
          <button
            v-for="section in sections"
            :key="section.id"
            @click="scrollToSection(section.id)"
            :disabled="!section.count"
            :class="[
              'px-4 py-2 rounded-full text-sm font-medium transition-all',
              section.count
                ? 'bg-gray-200 text-gray-700 hover:bg-purple-600 hover:text-white'
                : 'bg-gray-100 text-gray-400 cursor-not-allowed opacity-50'
            ]"
          >
            {{ section.label }}{{ section.count ? ` (${section.count})` : '' }}
          </button>
        </div>
      </div>

      <!-- Search -->
      <div>
        <input
          type="text"
          placeholder="🔍 Buscar por título ou publicação..."
          :value="searchQuery"
          @input="$emit('update:search-query', $event.target.value)"
          class="w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-purple-600"
        />
      </div>

      <!-- Refresh Button -->
      <button
        @click="$emit('refresh')"
        class="mt-4 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-all text-sm font-medium"
      >
        🔄 Atualizar
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  selectedClass: String,
  searchQuery: String,
  totalArtigos: { type: Number, default: 0 },
  totalNoticias: { type: Number, default: 0 },
  totalDiscussoes: { type: Number, default: 0 },
  totalPodcasts: { type: Number, default: 0 }
})

defineEmits(['update:selected-class', 'update:search-query', 'refresh'])

const sections = computed(() => [
  { id: 'section-artigos',    label: '📚 Artigos',     count: props.totalArtigos },
  { id: 'section-noticias',   label: '📰 Notícias',    count: props.totalNoticias },
  { id: 'section-discussoes', label: '𝕏 Discussões',  count: props.totalDiscussoes },
  { id: 'section-podcasts',   label: '🎙️ Podcasts',   count: props.totalPodcasts }
])

function scrollToSection(id) {
  const el = document.getElementById(id)
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}
</script>
