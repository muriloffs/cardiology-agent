<!-- frontend/src/components/XDiscussionCard.vue -->
<template>
  <div
    class="bg-white border border-gray-200 rounded-lg p-4 hover:border-blue-300 hover:shadow-sm transition-all cursor-pointer"
    @click="$emit('click')"
  >
    <div class="flex items-start gap-3">
      <span class="text-2xl flex-shrink-0">{{ discussion.emoji }}</span>
      <div class="min-w-0 flex-1">
        <div class="flex items-center gap-2 mb-1 flex-wrap">
          <span :class="['badge', discussion.classe === 'A' ? 'badge-a' : discussion.classe === 'B' ? 'badge-b' : 'badge-c']">
            Classe {{ discussion.classe }}
          </span>
          <span class="text-xs text-gray-500 font-medium">{{ discussion.autor }}</span>
        </div>
        <h3 class="font-semibold text-gray-900 text-sm leading-snug mb-1">{{ discussion.titulo }}</h3>
        <p class="text-gray-600 text-xs line-clamp-2">{{ discussion.resumo }}</p>
        <div class="flex items-center gap-3 mt-2">
          <a
            v-if="discussion.links?.post_url"
            :href="discussion.links.post_url"
            class="text-xs text-blue-500 hover:text-blue-700 flex items-center gap-1"
            @click.stop
          >
            𝕏 Ver post
          </a>
          <a
            v-if="articleUrl"
            :href="articleUrl"
            class="text-xs text-green-600 hover:text-green-800 flex items-center gap-1"
            @click.stop
          >
            🔗 Artigo
          </a>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  discussion: Object
})

defineEmits(['click'])

const articleUrl = computed(() => {
  const l = props.discussion?.links
  if (l?.url) return l.url
  if (l?.pubmed) return `https://pubmed.ncbi.nlm.nih.gov/${l.pubmed}/`
  if (l?.doi) return `https://doi.org/${l.doi}`
  return null
})
</script>
