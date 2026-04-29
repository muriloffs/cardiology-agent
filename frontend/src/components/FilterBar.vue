<!-- frontend/src/components/FilterBar.vue -->
<template>
  <div class="sticky top-[88px] md:top-[132px] bg-white border-b border-gray-200 z-30">
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

      <!-- Source Filters -->
      <div class="mb-4">
        <p class="text-sm font-semibold text-gray-700 mb-2">Fonte</p>
        <div class="flex gap-2 flex-wrap">
          <button
            v-for="source in availableSources"
            :key="source"
            @click="$emit('update:selected-source', source)"
            :class="[
              'px-4 py-2 rounded-full text-sm font-medium transition-all',
              selectedSource === source
                ? 'bg-purple-600 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            ]"
          >
            {{ { all: 'Todas', revista: 'Revista', noticias: 'Notícias', substack: 'Substack' }[source] || source }}
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
const props = defineProps({
  selectedClass: String,
  selectedSource: String,
  searchQuery: String,
  availableSources: {
    type: Array,
    default: () => ['all', 'revista']
  }
})

defineEmits(['update:selected-class', 'update:selected-source', 'update:search-query', 'refresh'])
</script>
