<!-- frontend/src/components/ArticleDetail.vue -->
<template>
  <div
    v-if="article"
    class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-start justify-center p-4 pt-12"
    @click.self="$emit('close')"
  >
    <div class="bg-white rounded-lg max-w-2xl w-full max-h-[85vh] flex flex-col">
      <!-- Header — always visible, never scrolls -->
      <div class="flex-shrink-0 bg-white border-b border-gray-200 p-4 md:p-6 flex items-start justify-between gap-3 rounded-t-lg">
        <div class="flex items-start gap-3 min-w-0">
          <span class="text-3xl md:text-4xl flex-shrink-0">{{ article.emoji }}</span>
          <div class="min-w-0">
            <h2 class="text-lg md:text-2xl font-bold leading-tight">{{ article.titulo }}</h2>
            <p class="text-gray-600 text-sm md:text-base">{{ article.publicacao }}</p>
          </div>
        </div>
        <button
          @click="$emit('close')"
          class="flex-shrink-0 text-gray-500 hover:text-gray-700 font-bold text-2xl leading-none pt-1"
        >
          ✕
        </button>
      </div>

      <!-- Content — scrollable -->
      <div class="flex-1 overflow-y-auto p-6 space-y-6">
        <!-- Score and Class -->
        <div class="flex items-center gap-4">
          <span :class="[
            'badge',
            article.classe === 'A' ? 'badge-a' : article.classe === 'B' ? 'badge-b' : 'badge-c'
          ]">
            Classe {{ article.classe }}
          </span>
          <span class="text-lg font-bold text-gray-700">Score: {{ article.score }}/10</span>
        </div>

        <!-- Resumo -->
        <div>
          <h3 class="text-lg font-bold mb-2">Resumo</h3>
          <p class="text-gray-700">{{ article.resumo }}</p>
        </div>

        <!-- Impacto Clínico -->
        <div>
          <h3 class="text-lg font-bold mb-2">💡 Impacto Clínico</h3>
          <p class="text-gray-700">{{ article.impacto_clinico }}</p>
        </div>

        <!-- Metadata -->
        <div class="grid grid-cols-2 gap-4">
          <div class="bg-gray-50 p-4 rounded-lg">
            <p class="text-sm text-gray-600">Fonte</p>
            <p class="font-semibold">
              {{ { revista: '📰 Revista', noticias: '📡 Notícias', substack: '📝 Substack', podcast: '🎙️ Podcast' }[article.categoria_fonte] || '📰 Revista' }}
            </p>
          </div>
          <div class="bg-gray-50 p-4 rounded-lg">
            <p class="text-sm text-gray-600">Publicação</p>
            <p class="font-semibold">{{ article.publicacao }}</p>
          </div>
        </div>
      </div>

      <!-- Footer — always visible, never scrolls (link stays tappable on mobile) -->
      <div class="flex-shrink-0 p-4 border-t border-gray-200 flex gap-3 rounded-b-lg">
        <DownloadButton
          @download="$emit('download')"
        />
        <a
          v-if="article.links?.url"
          :href="article.links.url"
          target="_blank"
          rel="noopener"
          class="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-all"
        >
          🔗 Ler Artigo Completo
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

defineEmits(['close', 'download'])
</script>
