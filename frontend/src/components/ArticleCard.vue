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

    <!-- Conclusão (paráfrase do abstract — NOVO) -->
    <div v-if="article.conclusao" class="mb-3 p-2.5 bg-emerald-50 border-l-2 border-emerald-400 rounded-r">
      <p class="text-[10px] font-bold uppercase tracking-wider text-emerald-700 mb-0.5">🎯 Conclusão do paper</p>
      <p class="text-sm text-gray-800 leading-relaxed">{{ article.conclusao }}</p>
    </div>

    <!-- Pontos-chave (dados granulares — NOVO) -->
    <div v-if="article.pontos_chave?.length" class="mb-3 p-2.5 bg-blue-50 border-l-2 border-blue-400 rounded-r">
      <p class="text-[10px] font-bold uppercase tracking-wider text-blue-700 mb-1">📊 Pontos-chave</p>
      <ul class="space-y-0.5">
        <li
          v-for="(ponto, i) in article.pontos_chave"
          :key="i"
          class="text-sm text-gray-800 leading-snug flex gap-1.5"
        >
          <span class="text-blue-500 font-bold flex-shrink-0">▸</span>
          <span>{{ ponto }}</span>
        </li>
      </ul>
    </div>

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
