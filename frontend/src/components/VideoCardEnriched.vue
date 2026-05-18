<!-- frontend/src/components/VideoCardEnriched.vue -->
<!--
  YouTube video card — minimal version.
  Shows ONLY real content: thumbnail, channel name, title, RSS description
  (literal text the uploader wrote). No LLM-inferred fields (no bullets,
  resumo_pt, tema, tags, source-of-truth chip) because without a transcript
  any synthesis risks distorting the actual content of the video.
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
      @click="handleExternalLinkClick($event, video.video_url)"
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
        <span class="font-medium truncate flex-1 break-words">{{ video.canal }}</span>
        <span v-if="formattedDate" class="flex-shrink-0 ml-2">{{ formattedDate }}</span>
      </div>

      <!-- Title (real, from RSS) -->
      <h3 class="font-bold text-base leading-snug text-gray-900 break-words">
        {{ video.titulo }}
      </h3>

      <!-- Description (REAL text the uploader wrote — no LLM inference) -->
      <p v-if="video.descricao_preview"
         class="text-sm text-gray-700 leading-relaxed pt-1 border-t border-gray-100 whitespace-pre-line break-words">
        {{ video.descricao_preview }}
      </p>

      <!-- Actions: Share + Things + Watch -->
      <div class="flex items-center justify-end gap-2 pt-2 mt-auto flex-wrap">
        <ShareButton :item="video" type="video" />
        <SendToThingsButton :item="video" type="video" />
        <a
          :href="video.video_url"
          target="_blank"
          rel="noopener noreferrer"
          class="inline-flex items-center gap-1 text-xs font-semibold text-red-600 hover:text-red-800 hover:underline whitespace-nowrap"
          @click.stop="handleExternalLinkClick($event, video.video_url)"
        >
          ▶ Assistir no YouTube →
        </a>
      </div>
    </div>
  </article>
</template>

<script setup>
import { computed } from 'vue'
import SendToThingsButton from './SendToThingsButton.vue'
import ShareButton from './ShareButton.vue'
import { handleExternalLinkClick } from '../utils/openLink'

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
