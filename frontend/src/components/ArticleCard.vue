<!-- frontend/src/components/ArticleCard.vue -->
<template>
  <div
    @click="$emit('click')"
    class="card cursor-pointer group"
  >
    <div class="flex items-start justify-between mb-3">
      <div class="flex items-center gap-3">
        <span class="text-2xl">{{ article.emoji }}</span>
        <div>
          <h3 class="font-bold text-lg group-hover:text-purple-600 transition-colors">
            {{ article.titulo }}
          </h3>
          <p class="text-sm text-gray-600">{{ article.publicacao }}</p>
        </div>
      </div>
      <div class="flex flex-col items-end gap-2">
        <span :class="[
          'badge',
          article.classe === 'A' ? 'badge-a' : article.classe === 'B' ? 'badge-b' : 'badge-c'
        ]">
          Classe {{ article.classe }}
        </span>
        <span class="text-sm font-bold text-gray-700">{{ article.score }}/10</span>
      </div>
    </div>

    <p class="text-gray-700 text-sm mb-3 line-clamp-2">{{ article.resumo }}</p>

    <p class="text-sm text-gray-600 mb-4 italic">💡 {{ article.impacto_clinico }}</p>

    <div class="flex items-center justify-between">
      <span class="text-xs text-gray-500">
        {{ article.categoria_fonte === 'twitter' ? '🐦' : article.categoria_fonte === 'podcast' ? '🎙️' : article.categoria_fonte === 'substack' ? '📝' : '📰' }}
        {{ article.categoria_fonte }}
      </span>
      <div class="flex gap-2">
        <DownloadButton
          @download.stop="$emit('download')"
        />
        <a
          v-if="article.links?.url"
          :href="article.links.url"
          target="_blank"
          rel="noopener"
          class="inline-flex items-center gap-2 px-3 py-2 bg-blue-100 text-blue-700 rounded-lg text-sm font-medium hover:bg-blue-200 transition-all"
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
  article: Object
})

defineEmits(['click', 'download'])
</script>
