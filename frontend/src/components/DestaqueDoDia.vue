<!-- frontend/src/components/DestaqueDoDia.vue -->
<template>
  <section v-if="destaque" class="px-4 py-5 max-w-6xl mx-auto">
    <div class="bg-gradient-to-br from-amber-50 via-yellow-50 to-orange-50 border-l-4 border-amber-500 rounded-lg shadow-sm p-5 md:p-6">
      <!-- Star + label -->
      <div class="flex items-center gap-2 mb-3">
        <span class="text-2xl">🌟</span>
        <span class="text-xs font-bold uppercase tracking-wider text-amber-800">Destaque do dia</span>
        <span class="ml-auto text-[10px] font-medium uppercase text-amber-700 bg-amber-100 px-2 py-0.5 rounded-full">
          {{ tipoLabel }}
        </span>
      </div>

      <!-- Title -->
      <h2 class="text-lg md:text-2xl font-bold text-gray-900 leading-snug mb-1">
        {{ destaque.titulo }}
      </h2>
      <p v-if="destaque.publicacao" class="text-sm text-gray-600 mb-4">
        <span class="font-medium">{{ destaque.publicacao }}</span>
      </p>

      <!-- Razão -->
      <div class="mb-4">
        <p class="text-xs font-bold uppercase tracking-wide text-amber-800 mb-1">Por que é o destaque</p>
        <p class="text-sm md:text-base text-gray-800 leading-relaxed">{{ destaque.razao }}</p>
      </div>

      <!-- Two-column: muda vs não muda -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div class="bg-white/70 backdrop-blur-sm rounded-md p-3 border border-green-200">
          <p class="text-xs font-bold uppercase tracking-wide text-green-700 mb-1">✅ O que muda</p>
          <p class="text-sm text-gray-800 leading-relaxed">{{ destaque.o_que_muda }}</p>
        </div>
        <div class="bg-white/70 backdrop-blur-sm rounded-md p-3 border border-gray-300">
          <p class="text-xs font-bold uppercase tracking-wide text-gray-600 mb-1">⏸️ O que não muda ainda</p>
          <p class="text-sm text-gray-800 leading-relaxed">{{ destaque.o_que_nao_muda_ainda }}</p>
        </div>
      </div>

      <!-- Jump to item link (if we can find it in the report) -->
      <button
        v-if="onJumpToItem"
        @click="onJumpToItem(destaque)"
        class="mt-4 inline-flex items-center gap-1.5 text-sm font-medium text-amber-800 hover:text-amber-900 underline-offset-4 hover:underline"
      >
        Ver item completo →
      </button>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  destaque: { type: Object, default: null },
  onJumpToItem: { type: Function, default: null }
})

const tipoLabel = computed(() => {
  const t = props.destaque?.tipo_origem
  if (t === 'artigo') return '📚 Artigo'
  if (t === 'noticia') return '📰 Notícia'
  if (t === 'podcast') return '🎙️ Podcast'
  return '⭐ Destaque'
})
</script>
