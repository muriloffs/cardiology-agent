<!-- frontend/src/components/FilterBar.vue -->
<!--
  Compact filter strip: class filter (A/B/C/all) + refresh.
  Search bar and section navigation removed — each tab is its own focused view now.
-->
<template>
  <div class="bg-white border-b border-gray-200">
    <div class="max-w-6xl mx-auto px-4 py-3 flex items-center gap-3 flex-wrap">
      <span class="text-sm font-semibold text-gray-700">Classe:</span>
      <div class="flex gap-2 flex-wrap">
        <button
          v-for="cls in ['all', 'A', 'B', 'C']"
          :key="cls"
          @click="$emit('update:selected-class', cls)"
          :class="[
            'px-3 py-1.5 rounded-full text-sm font-medium transition-all',
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
      <button
        @click="$emit('refresh')"
        class="ml-auto px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-all text-sm font-medium"
      >
        🔄 Atualizar
      </button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  selectedClass: String
})

defineEmits(['update:selected-class', 'refresh'])
</script>
