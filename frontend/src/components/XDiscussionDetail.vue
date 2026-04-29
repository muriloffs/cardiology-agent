<!-- frontend/src/components/XDiscussionDetail.vue -->
<template>
  <div
    v-if="discussion"
    class="fixed inset-0 z-50 pointer-events-none flex items-start justify-center p-4 pt-12"
  >
    <div class="absolute inset-0 bg-black bg-opacity-50 pointer-events-auto cursor-pointer" @click="$emit('close')"></div>
    <div class="relative bg-white rounded-lg max-w-2xl w-full max-h-[85dvh] flex flex-col md:block md:overflow-y-auto pointer-events-auto">

      <!-- Header -->
      <div class="flex-shrink-0 bg-white border-b border-gray-200 p-4 md:p-6 flex items-start justify-between gap-3 rounded-t-lg">
        <div class="flex items-start gap-3 min-w-0">
          <span class="text-3xl md:text-4xl flex-shrink-0">{{ discussion.emoji }}</span>
          <div class="min-w-0">
            <h2 class="text-lg md:text-2xl font-bold leading-tight">{{ discussion.titulo }}</h2>
            <p class="text-gray-600 text-sm md:text-base">{{ discussion.autor }}</p>
          </div>
        </div>
        <button
          @click="$emit('close')"
          class="flex-shrink-0 text-gray-500 hover:text-gray-700 font-bold text-2xl leading-none pt-1"
        >
          ✕
        </button>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto md:overflow-y-visible md:flex-none p-6 space-y-6">
        <div class="flex items-center gap-4">
          <span :class="['badge', discussion.classe === 'A' ? 'badge-a' : discussion.classe === 'B' ? 'badge-b' : 'badge-c']">
            Classe {{ discussion.classe }}
          </span>
          <span class="text-lg font-bold text-gray-700">Score: {{ discussion.score }}/10</span>
        </div>

        <div>
          <h3 class="text-lg font-bold mb-2">Resumo</h3>
          <p class="text-gray-700">{{ discussion.resumo }}</p>
        </div>

        <div>
          <h3 class="text-lg font-bold mb-2">💡 Impacto Clínico</h3>
          <p class="text-gray-700">{{ discussion.impacto_clinico }}</p>
        </div>

      </div>

      <!-- Footer -->
      <div class="flex-shrink-0 p-4 border-t border-gray-200 flex gap-3 flex-wrap rounded-b-lg" style="padding-bottom: calc(env(safe-area-inset-bottom, 0px) + 1rem)">
        <a
          v-if="discussion.links?.post_url"
          :href="discussion.links.post_url"
          class="inline-flex items-center gap-2 px-4 py-2 bg-gray-900 text-white rounded-lg font-medium hover:bg-gray-700 transition-all text-sm"
        >
          𝕏 Ver Post
        </a>
        <a
          v-if="articleUrl"
          :href="articleUrl"
          class="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-all text-sm"
        >
          🔗 Ver Artigo
        </a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  discussion: Object
})

defineEmits(['close'])

const articleUrl = computed(() => {
  const l = props.discussion?.links
  if (l?.url) return l.url
  if (l?.pubmed) return `https://pubmed.ncbi.nlm.nih.gov/${l.pubmed}/`
  if (l?.doi) return `https://doi.org/${l.doi}`
  return null
})
</script>
