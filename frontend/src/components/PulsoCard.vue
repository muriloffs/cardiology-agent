<!-- frontend/src/components/PulsoCard.vue -->
<!--
  Pulso highlight card. Shows multi-source synthesis of one impactful topic.
  Big One (is_destaque_do_dia=true) gets amber gradient header + "🌟 Destaque".
  Others get standard purple/blue accent based on classe.
-->
<template>
  <article :class="[
    'rounded-lg border-l-4 bg-white shadow-sm hover:shadow-md transition-shadow overflow-hidden',
    item.is_destaque_do_dia ? 'border-amber-500' : classeBorderColor
  ]">
    <!-- Header: Big One gets gradient, others get classe-colored background -->
    <header :class="[
      'px-4 md:px-5 py-3',
      item.is_destaque_do_dia
        ? 'bg-gradient-to-br from-amber-50 via-yellow-50 to-orange-50 border-b border-amber-200'
        : 'bg-gray-50 border-b border-gray-200'
    ]">
      <!-- Big One label OR classe + score -->
      <div class="flex items-start justify-between gap-3 mb-2">
        <div class="flex items-center gap-2">
          <template v-if="item.is_destaque_do_dia">
            <span class="text-xl">🌟</span>
            <span class="text-xs font-bold uppercase tracking-wider text-amber-800">
              Destaque do Dia
            </span>
          </template>
          <template v-else>
            <span :class="['inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide',
                           classeBadgeColor]">
              Classe {{ item.classe }}
            </span>
            <span class="text-xs text-gray-500">Score {{ item.score }}/10</span>
          </template>
        </div>
        <span v-if="!item.is_destaque_do_dia" class="text-xs text-gray-400 flex-shrink-0">
          {{ item.fontes_cobertura?.length || 0 }} fontes
        </span>
      </div>

      <!-- Title -->
      <h3 :class="[
        'font-bold leading-snug',
        item.is_destaque_do_dia ? 'text-lg md:text-xl text-gray-900' : 'text-base md:text-lg text-gray-800'
      ]">
        {{ item.titulo }}
      </h3>
    </header>

    <!-- Body -->
    <div class="px-4 md:px-5 py-4 space-y-4">
      <!-- Razão de ser destaque -->
      <div>
        <p class="text-[11px] font-bold uppercase tracking-wider text-gray-500 mb-1">
          Por que importou hoje
        </p>
        <p class="text-sm text-gray-700 leading-relaxed">{{ item.razao_destaque }}</p>
      </div>

      <!-- O que o paper diz -->
      <div>
        <p class="text-[11px] font-bold uppercase tracking-wider text-blue-700 mb-1">
          📄 O que o paper diz
        </p>
        <p class="text-sm text-gray-700 leading-relaxed">{{ item.o_que_paper_diz }}</p>
      </div>

      <!-- Interpretação da comunidade -->
      <div>
        <p class="text-[11px] font-bold uppercase tracking-wider text-purple-700 mb-1">
          💬 Interpretação da comunidade
        </p>
        <p class="text-sm text-gray-700 leading-relaxed italic">{{ item.interpretacao_comunidade }}</p>
      </div>

      <!-- 2-col grid: muda × não muda -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
        <div class="bg-green-50 border border-green-200 rounded-md p-3">
          <p class="text-[11px] font-bold uppercase tracking-wider text-green-700 mb-1">
            ✅ O que muda
          </p>
          <p class="text-sm text-gray-800 leading-relaxed">{{ item.o_que_muda }}</p>
        </div>
        <div class="bg-gray-100 border border-gray-300 rounded-md p-3">
          <p class="text-[11px] font-bold uppercase tracking-wider text-gray-600 mb-1">
            ⏸️ O que não muda ainda
          </p>
          <p class="text-sm text-gray-800 leading-relaxed">{{ item.o_que_nao_muda_ainda }}</p>
        </div>
      </div>

      <!-- Fontes de cobertura -->
      <div v-if="item.fontes_cobertura?.length" class="pt-2 border-t border-gray-100">
        <p class="text-[11px] font-bold uppercase tracking-wider text-gray-500 mb-2">
          🔗 Cobertura cruzada ({{ item.fontes_cobertura.length }} fonte{{ item.fontes_cobertura.length > 1 ? 's' : '' }})
        </p>
        <div class="flex flex-wrap gap-1.5">
          <span
            v-for="(fonte, i) in item.fontes_cobertura"
            :key="i"
            :class="['inline-flex items-center gap-1 px-2 py-1 rounded text-xs',
                     fonteBadgeColor(fonte.tipo)]"
          >
            <span>{{ fonteEmoji(fonte.tipo) }}</span>
            <span class="font-medium">{{ fonte.publicacao || fonte.autor || fonte.tipo }}</span>
          </span>
        </div>
      </div>
    </div>
  </article>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  item: { type: Object, required: true }
})

const classeBorderColor = computed(() => {
  if (props.item.classe === 'A') return 'border-red-500'
  if (props.item.classe === 'B') return 'border-orange-500'
  return 'border-green-500'
})

const classeBadgeColor = computed(() => {
  if (props.item.classe === 'A') return 'bg-red-100 text-red-800'
  if (props.item.classe === 'B') return 'bg-orange-100 text-orange-800'
  return 'bg-green-100 text-green-800'
})

function fonteEmoji(tipo) {
  return {
    artigo: '📚',
    noticia: '📰',
    podcast: '🎙️',
    video: '📺',
    x: '𝕏',
    bluesky: '🦋'
  }[tipo] || '📎'
}

function fonteBadgeColor(tipo) {
  return {
    artigo:  'bg-purple-100 text-purple-800',
    noticia: 'bg-orange-100 text-orange-800',
    podcast: 'bg-indigo-100 text-indigo-800',
    video:   'bg-red-100 text-red-800',
    x:       'bg-gray-200 text-gray-800',
    bluesky: 'bg-sky-100 text-sky-800'
  }[tipo] || 'bg-gray-100 text-gray-700'
}
</script>
