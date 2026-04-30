<!-- frontend/src/components/ArticleCard.vue -->
<template>
  <div
    @click="$emit('click')"
    class="card cursor-pointer group"
  >
    <div class="flex items-start gap-3 mb-3">
      <span class="text-2xl flex-shrink-0">{{ article.emoji }}</span>
      <div class="flex-1 min-w-0">
        <div class="flex items-start justify-between gap-2">
          <h3 class="font-bold text-base md:text-lg group-hover:text-purple-600 transition-colors">
            {{ article.titulo }}
          </h3>
          <div class="flex flex-col items-end gap-1 flex-shrink-0">
            <span :class="[
              'badge',
              article.classe === 'A' ? 'badge-a' : article.classe === 'B' ? 'badge-b' : 'badge-c'
            ]">
              Classe {{ article.classe }}
            </span>
            <span class="text-xs font-bold text-gray-700">{{ article.score }}/10</span>
          </div>
        </div>
        <p class="text-sm text-gray-600">{{ article.publicacao }}</p>
      </div>
    </div>

    <p class="text-gray-700 text-sm mb-3 line-clamp-2">{{ article.resumo }}</p>

    <p class="text-sm text-gray-600 mb-4 italic">💡 {{ article.impacto_clinico }}</p>

    <div class="flex items-center justify-between">
      <span class="text-xs text-gray-500">
        {{ { revista: '📰 Revista', noticias: '📡 Notícias', substack: '📝 Substack', podcast: '🎙️ Podcast' }[article.categoria_fonte] || '📰 Revista' }}
      </span>
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
</template>

<script setup>
defineProps({
  article: Object
})

defineEmits(['click'])
</script>
