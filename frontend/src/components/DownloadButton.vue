<!-- frontend/src/components/DownloadButton.vue -->
<template>
  <button
    @click="$emit('download')"
    :disabled="loading"
    :class="[
      'inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all',
      loading
        ? 'bg-gray-300 text-gray-600 cursor-not-allowed'
        : 'bg-purple-100 text-purple-700 hover:bg-purple-200 active:scale-95'
    ]"
  >
    <span v-if="!loading">📥 Baixar PDF</span>
    <span v-else>⏳ Baixando...</span>
  </button>
</template>

<script setup>
defineProps({
  loading: Boolean
})

defineEmits(['download'])
</script>
