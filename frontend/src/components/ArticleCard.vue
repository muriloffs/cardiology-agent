<!-- frontend/src/components/ArticleCard.vue -->
<!--
  Article card — Framework 8 Seções (2026-05-11):
  1. Header (emoji, título, classe/score, publicação)
  2. Contexto clínico (problema + motivação)
  3. Pergunta principal
  4. Desenho do estudo (tabela compacta 2x6)
  5. Pontos-chave (chips numéricos N/HR/NNT)
  6. Principais resultados (narrativa clínica longa)
  7. Interpretação prática (muda conduta?)
  8. Limitações
  9. Conclusão em uma frase (veredito)
  10. Link "Ler" no rodapé

  Fallback gracioso: cada seção tem v-if. Artigos antigos (sem framework)
  mostram só o que têm.
-->
<template>
  <div
    @click="$emit('click')"
    class="card cursor-pointer group"
  >
    <!-- Header -->
    <div class="flex items-start gap-3 mb-3">
      <span class="text-2xl flex-shrink-0">{{ article.emoji }}</span>
      <div class="flex-1 min-w-0">
        <div class="flex items-start justify-between gap-2">
          <h3 class="font-bold text-base md:text-lg group-hover:text-purple-600 transition-colors break-words min-w-0">
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
        <p class="text-sm text-gray-600 break-words">{{ article.publicacao }}</p>
      </div>
    </div>

    <!-- 1. Contexto clínico -->
    <div v-if="article.contexto_clinico" class="mb-3 p-2.5 bg-slate-50 border-l-2 border-slate-400 rounded-r">
      <p class="text-[10px] font-bold uppercase tracking-wider text-slate-700 mb-0.5">🩺 Contexto clínico</p>
      <p class="text-sm text-gray-800 leading-relaxed break-words">{{ article.contexto_clinico }}</p>
    </div>

    <!-- 2. Pergunta principal -->
    <div v-if="article.pergunta_principal" class="mb-3 p-2.5 bg-indigo-50 border-l-2 border-indigo-400 rounded-r">
      <p class="text-[10px] font-bold uppercase tracking-wider text-indigo-700 mb-0.5">❓ Pergunta principal</p>
      <p class="text-sm text-gray-800 leading-relaxed break-words">{{ article.pergunta_principal }}</p>
    </div>

    <!-- 3. Desenho do estudo (tabela 2 colunas) -->
    <div v-if="hasDesenho" class="mb-3 p-2.5 bg-amber-50 border-l-2 border-amber-400 rounded-r">
      <p class="text-[10px] font-bold uppercase tracking-wider text-amber-800 mb-1.5">🔬 Desenho do estudo</p>
      <dl class="grid grid-cols-[auto,1fr] gap-x-3 gap-y-0.5 text-sm">
        <template v-for="(value, key) in desenhoFields" :key="key">
          <dt class="font-semibold text-amber-900 whitespace-nowrap">{{ desenhoLabels[key] }}</dt>
          <dd class="text-gray-800 break-words">{{ value }}</dd>
        </template>
      </dl>
    </div>

    <!-- 4. Pontos-chave (chips numéricos) -->
    <div v-if="article.pontos_chave?.length" class="mb-3 p-2.5 bg-blue-50 border-l-2 border-blue-400 rounded-r">
      <p class="text-[10px] font-bold uppercase tracking-wider text-blue-700 mb-1">📊 Pontos-chave</p>
      <ul class="space-y-0.5">
        <li
          v-for="(ponto, i) in article.pontos_chave"
          :key="i"
          class="text-sm text-gray-800 leading-snug flex gap-1.5"
        >
          <span class="text-blue-500 font-bold flex-shrink-0">▸</span>
          <span class="break-words min-w-0">{{ ponto }}</span>
        </li>
      </ul>
    </div>

    <!-- 5. Principais resultados (parte MAIS importante — sem cap) -->
    <div v-if="article.principais_resultados" class="mb-3 p-3 bg-emerald-50 border-l-2 border-emerald-500 rounded-r">
      <p class="text-[10px] font-bold uppercase tracking-wider text-emerald-700 mb-1">🎯 Principais resultados</p>
      <p class="text-sm text-gray-900 leading-relaxed break-words whitespace-pre-line">{{ article.principais_resultados }}</p>
    </div>

    <!-- 6. Interpretação prática (muda conduta?) -->
    <div v-if="article.interpretacao_pratica" class="mb-3 p-2.5 bg-purple-50 border-l-2 border-purple-400 rounded-r">
      <p class="text-[10px] font-bold uppercase tracking-wider text-purple-700 mb-0.5">💡 Interpretação prática</p>
      <p class="text-sm text-gray-800 leading-relaxed break-words">{{ article.interpretacao_pratica }}</p>
    </div>

    <!-- Fallback legacy: impacto_clinico (apenas se não houver interpretacao_pratica) -->
    <p v-else-if="article.impacto_clinico" class="text-sm text-gray-600 mb-3 italic break-words">💡 {{ article.impacto_clinico }}</p>

    <!-- 7. Limitações -->
    <div v-if="article.limitacoes?.length" class="mb-3 p-2.5 bg-orange-50 border-l-2 border-orange-400 rounded-r">
      <p class="text-[10px] font-bold uppercase tracking-wider text-orange-700 mb-1">⚠️ Limitações</p>
      <ul class="space-y-0.5">
        <li
          v-for="(lim, i) in article.limitacoes"
          :key="i"
          class="text-sm text-gray-800 leading-snug flex gap-1.5"
        >
          <span class="text-orange-500 font-bold flex-shrink-0">▸</span>
          <span class="break-words min-w-0">{{ lim }}</span>
        </li>
      </ul>
    </div>

    <!-- 8. Conclusão em uma frase (veredito final, destaque visual) -->
    <div v-if="article.conclusao_uma_frase" class="mb-3 p-3 bg-gradient-to-r from-rose-50 to-pink-50 border-2 border-rose-300 rounded">
      <p class="text-[10px] font-bold uppercase tracking-wider text-rose-700 mb-0.5">⚡ Veredito</p>
      <p class="text-sm font-semibold text-gray-900 leading-relaxed break-words">{{ article.conclusao_uma_frase }}</p>
    </div>

    <!-- Footer: source + actions -->
    <div class="flex items-center justify-between gap-2 flex-wrap">
      <span class="text-xs text-gray-500">
        {{ { revista: '📰 Revista', noticias: '📡 Notícias', substack: '📝 Substack', podcast: '🎙️ Podcast' }[article.categoria_fonte] || '📰 Revista' }}
      </span>
      <div class="flex items-center gap-2 flex-wrap">
        <ShareButton :item="article" type="artigo" />
        <SendToThingsButton :item="article" type="artigo" />
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
import { computed } from 'vue'
import SendToThingsButton from './SendToThingsButton.vue'
import ShareButton from './ShareButton.vue'

const props = defineProps({
  article: Object
})

defineEmits(['click'])

const desenhoLabels = {
  tipo: 'Tipo',
  populacao: 'População',
  n: 'N',
  intervencao: 'Intervenção',
  comparador: 'Comparador',
  seguimento: 'Seguimento',
}

const desenhoFields = computed(() => {
  const d = props.article?.desenho_estudo
  if (!d || typeof d !== 'object') return {}
  const ordered = {}
  for (const k of Object.keys(desenhoLabels)) {
    if (d[k] && typeof d[k] === 'string' && d[k].trim()) {
      ordered[k] = d[k]
    }
  }
  return ordered
})

const hasDesenho = computed(() => Object.keys(desenhoFields.value).length > 0)
</script>
