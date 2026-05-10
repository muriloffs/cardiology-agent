<!-- frontend/src/components/VideoCardEnriched.vue -->
<!--
  Rich YouTube card with Gemini-enriched PT-BR fields (Phase 6).
  Shows thumbnail (16:9) on top, then channel/tier badge, title, theme,
  bullets, summary, tags, and "Assistir" button. Falls back gracefully
  to legacy fields when video is not enriched.
-->
<template>
  <article
    class="rounded-lg border border-gray-200 bg-white shadow-sm hover:shadow-md transition-shadow overflow-hidden flex flex-col"
  >
    <!-- Thumbnail (16:9) -->
    <a
      :href="video.video_url"
      target="_blank"
      rel="noopener noreferrer"
      class="relative block aspect-video bg-gray-100 overflow-hidden group"
    >
      <img
        v-if="video.thumbnail"
        :src="video.thumbnail"
        :alt="video.titulo"
        class="w-full h-full object-cover transition-transform group-hover:scale-105"
        loading="lazy"
      />
      <div v-else class="w-full h-full flex items-center justify-center text-gray-400 text-4xl">
        📺
      </div>
      <!-- Play overlay -->
      <div class="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/30">
        <div class="bg-red-600 text-white rounded-full w-14 h-14 flex items-center justify-center text-xl shadow-lg">
          ▶
        </div>
      </div>
      <!-- Tier badge top-right -->
      <span
        :class="['absolute top-2 right-2 inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide shadow',
                 tierBadgeColor]"
      >
        {{ tierLabel }}
      </span>
    </a>

    <!-- Body -->
    <div class="px-4 py-3 flex-1 flex flex-col gap-2.5">
      <!-- Channel + date -->
      <div class="flex items-center justify-between text-xs text-gray-500">
        <span class="font-medium truncate flex-1">{{ video.canal }}</span>
        <span v-if="formattedDate" class="flex-shrink-0 ml-2">{{ formattedDate }}</span>
      </div>

      <!-- Title -->
      <h3 class="font-bold text-base leading-snug text-gray-900 line-clamp-3">
        {{ video.titulo }}
      </h3>

      <!-- Tema badge -->
      <div v-if="video.tema" class="flex items-center gap-2 flex-wrap">
        <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide bg-purple-100 text-purple-800">
          {{ video.tema }}
        </span>
      </div>

      <!-- Bullets (enriched only) -->
      <ul v-if="video.bullets_pt?.length" class="space-y-1 mt-1">
        <li
          v-for="(bullet, i) in video.bullets_pt"
          :key="i"
          class="text-sm text-gray-700 leading-relaxed flex gap-2"
        >
          <span class="flex-shrink-0 text-red-500 font-bold mt-0.5">▸</span>
          <span>{{ bullet }}</span>
        </li>
      </ul>

      <!-- Summary -->
      <p v-if="video.resumo_pt" class="text-sm text-gray-600 italic leading-relaxed pt-1 border-t border-gray-100">
        {{ video.resumo_pt }}
      </p>

      <!-- Fallback to RSS description for non-enriched -->
      <p v-else-if="video.descricao_preview" class="text-sm text-gray-600 leading-relaxed pt-1 border-t border-gray-100 line-clamp-3">
        {{ video.descricao_preview }}
      </p>

      <!-- Contextual fields (Combo Total) — only render when present -->
      <div v-if="video.quem_se_aplica || video.evidencia_chave || video.contraponto" class="space-y-2 pt-1 border-t border-gray-100">
        <div v-if="video.quem_se_aplica" class="text-xs">
          <span class="font-bold text-blue-700 uppercase tracking-wide">👥 Para quem </span>
          <span class="text-gray-700">{{ video.quem_se_aplica }}</span>
        </div>
        <div v-if="video.evidencia_chave" class="text-xs">
          <span class="font-bold text-emerald-700 uppercase tracking-wide">📊 Evidência </span>
          <span class="text-gray-700">{{ video.evidencia_chave }}</span>
        </div>
        <div v-if="video.contraponto" class="text-xs">
          <span class="font-bold text-amber-700 uppercase tracking-wide">⚠️ Contraponto </span>
          <span class="text-gray-700">{{ video.contraponto }}</span>
        </div>
        <div v-if="video._transcript_used" class="text-xs">
          <span class="font-bold text-purple-700 uppercase tracking-wide">📝 Baseado em transcript</span>
        </div>
      </div>

      <!-- Tags + Watch -->
      <div class="flex items-center justify-between gap-3 pt-2 mt-auto flex-wrap">
        <div v-if="video.tags?.length" class="flex flex-wrap gap-1">
          <span
            v-for="(tag, i) in video.tags"
            :key="i"
            class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-gray-100 text-gray-600"
          >
            #{{ tag }}
          </span>
        </div>
        <a
          :href="video.video_url"
          target="_blank"
          rel="noopener noreferrer"
          class="inline-flex items-center gap-1 text-xs font-semibold text-red-600 hover:text-red-800 hover:underline whitespace-nowrap ml-auto"
        >
          ▶ Assistir →
        </a>
      </div>
    </div>
  </article>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  video: { type: Object, required: true }
})

const tierLabel = computed(() => {
  return { 0: '★ Pinned', 1: 'Sociedade', 2: 'Hospital' }[props.video.tier] || 'Vídeo'
})

const tierBadgeColor = computed(() => {
  return {
    0: 'bg-yellow-500 text-white',
    1: 'bg-purple-600 text-white',
    2: 'bg-blue-600 text-white',
  }[props.video.tier] || 'bg-gray-700 text-white'
})

const formattedDate = computed(() => {
  const raw = props.video.data_publicacao
  if (!raw) return ''
  const m = raw.match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (!m) return raw
  return `${m[3]}/${m[2]}`
})
</script>
