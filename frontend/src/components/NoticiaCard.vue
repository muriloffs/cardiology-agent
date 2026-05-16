<!-- frontend/src/components/NoticiaCard.vue -->
<!--
  Notícia card com resumo rico (estilo Substack):
  - Header: emoji, título, classe, fonte
  - Contexto (por que surgiu agora)
  - Pontos principais (bullets factuais)
  - Falas (quotes opcionais)
  - Insights (interpretação)
  - Por que importa (relevância clínica)
  - Link "Ler completo"

  Fallback: se notícia não tem os campos enriquecidos (falha 2-pass ou
  notícia antiga), mostra resumo legacy + impacto_clinico básicos.
-->
<template>
  <div
    @click="$emit('click')"
    class="card cursor-pointer group"
  >
    <!-- Header -->
    <div class="flex items-start gap-3 mb-3">
      <span class="text-2xl flex-shrink-0">{{ noticia.emoji || '📰' }}</span>
      <div class="flex-1 min-w-0">
        <div class="flex items-start justify-between gap-2">
          <h3 class="font-bold text-base md:text-lg group-hover:text-orange-600 transition-colors break-words min-w-0">
            {{ noticia.titulo }}
          </h3>
          <div class="flex flex-col items-end gap-1 flex-shrink-0">
            <span :class="[
              'badge',
              noticia.classe === 'A' ? 'badge-a' : noticia.classe === 'B' ? 'badge-b' : 'badge-c'
            ]">
              Classe {{ noticia.classe }}
            </span>
            <span class="text-xs font-bold text-gray-700">{{ noticia.score }}/10</span>
          </div>
        </div>
        <p class="text-sm text-gray-600 break-words">{{ noticia.publicacao }}</p>
      </div>
    </div>

    <!-- Contexto (por que surgiu agora) -->
    <div v-if="noticia.contexto" class="mb-3 p-2.5 bg-slate-50 border-l-2 border-slate-400 rounded-r">
      <p class="text-[10px] font-bold uppercase tracking-wider text-slate-700 mb-0.5">📍 Contexto</p>
      <p class="text-sm text-gray-800 leading-relaxed break-words">{{ noticia.contexto }}</p>
    </div>

    <!-- Pontos principais -->
    <div v-if="noticia.pontos_principais?.length" class="mb-3 p-2.5 bg-blue-50 border-l-2 border-blue-400 rounded-r">
      <p class="text-[10px] font-bold uppercase tracking-wider text-blue-700 mb-1">📋 Pontos principais</p>
      <ul class="space-y-0.5">
        <li
          v-for="(ponto, i) in noticia.pontos_principais"
          :key="i"
          class="text-sm text-gray-800 leading-snug flex gap-1.5"
        >
          <span class="text-blue-500 font-bold flex-shrink-0">▸</span>
          <span class="break-words min-w-0">{{ ponto }}</span>
        </li>
      </ul>
    </div>

    <!-- Falas (quotes de especialistas) -->
    <div v-if="noticia.falas?.length" class="mb-3 p-2.5 bg-amber-50 border-l-2 border-amber-400 rounded-r">
      <p class="text-[10px] font-bold uppercase tracking-wider text-amber-800 mb-1">💬 Falas</p>
      <ul class="space-y-1.5">
        <li
          v-for="(fala, i) in noticia.falas"
          :key="i"
          class="text-sm text-gray-800 leading-snug italic break-words"
        >
          {{ fala }}
        </li>
      </ul>
    </div>

    <!-- Insights -->
    <div v-if="noticia.insights" class="mb-3 p-2.5 bg-purple-50 border-l-2 border-purple-400 rounded-r">
      <p class="text-[10px] font-bold uppercase tracking-wider text-purple-700 mb-0.5">💡 Insights</p>
      <p class="text-sm text-gray-800 leading-relaxed break-words">{{ noticia.insights }}</p>
    </div>

    <!-- Por que importa (relevância clínica destacada) -->
    <div v-if="noticia.por_que_importa" class="mb-3 p-3 bg-gradient-to-r from-rose-50 to-pink-50 border-2 border-rose-300 rounded">
      <p class="text-[10px] font-bold uppercase tracking-wider text-rose-700 mb-0.5">⚡ Por que importa</p>
      <p class="text-sm font-semibold text-gray-900 leading-relaxed break-words">{{ noticia.por_que_importa }}</p>
    </div>

    <!-- Fallback legacy: resumo + impacto_clinico quando 2-pass falhou ou nao rodou -->
    <template v-if="!hasRichFields">
      <p v-if="noticia.resumo" class="text-gray-700 text-sm mb-3 break-words">{{ noticia.resumo }}</p>
      <p v-if="noticia.impacto_clinico" class="text-sm text-gray-600 mb-3 italic break-words">💡 {{ noticia.impacto_clinico }}</p>
    </template>

    <!-- Footer -->
    <div class="flex items-center justify-between gap-2 flex-wrap">
      <span class="text-xs text-gray-500">📡 {{ noticia.publicacao }}</span>
      <div class="flex items-center gap-2 flex-wrap">
        <SendToThingsButton :item="noticia" type="noticia" />
        <a
          v-if="noticia.links?.url"
          :href="noticia.links.url"
          target="_blank"
          rel="noopener"
          class="inline-flex items-center gap-2 px-3 py-2 bg-orange-100 text-orange-700 rounded-lg text-sm font-medium hover:bg-orange-200 transition-all"
          @click.stop
        >
          🔗 Ler completo
        </a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import SendToThingsButton from './SendToThingsButton.vue'

const props = defineProps({
  noticia: { type: Object, required: true }
})

defineEmits(['click'])

const hasRichFields = computed(() => {
  const n = props.noticia
  return Boolean(
    n.contexto ||
    n.pontos_principais?.length ||
    n.insights ||
    n.por_que_importa
  )
})
</script>
