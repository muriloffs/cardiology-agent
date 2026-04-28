<!-- frontend/src/components/FeaturedCard.vue -->
<template>
  <div
    @click="$emit('click')"
    :class="[
      'card-featured cursor-pointer text-white',
      index === 0 && 'bg-gradient-to-br from-red-500 to-red-600',
      index === 1 && 'bg-gradient-to-br from-teal-500 to-teal-600',
      index === 2 && 'bg-gradient-to-br from-orange-500 to-orange-600'
    ]"
  >
    <div class="mb-4">
      <span class="text-4xl">{{ article.emoji }}</span>
    </div>

    <h2 class="text-2xl font-bold mb-2">{{ article.titulo }}</h2>

    <p class="text-sm opacity-90 mb-4">{{ article.publicacao }}</p>

    <div class="mb-4">
      <p class="text-sm font-semibold mb-2">Impacto Clínico:</p>
      <p class="text-sm opacity-95">{{ article.impacto_clinico }}</p>
    </div>

    <div class="flex items-center justify-between pt-4 border-t border-white border-opacity-30">
      <span class="text-sm font-semibold">Score: {{ article.score }}/10</span>
      <div class="flex gap-2">
        <DownloadButton
          @download.stop="$emit('download')"
        />
        <a
          v-if="article.links?.url"
          :href="article.links.url"
          target="_blank"
          rel="noopener"
          class="inline-flex items-center gap-2 px-3 py-2 bg-white bg-opacity-20 hover:bg-opacity-30 rounded-lg text-sm font-medium transition-all"
          @click.stop
        >
          🔗 Ler
        </a>
      </div>
    </div>
  </div>
</template>

<script setup>
import DownloadButton from './DownloadButton.vue'

defineProps({
  article: Object,
  index: Number
})

defineEmits(['click', 'download'])
</script>
