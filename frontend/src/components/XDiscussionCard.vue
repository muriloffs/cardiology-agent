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
          <span :class="['text-xs font-medium px-2 py-0.5 rounded-full', categoriaStyle]">
            {{ categoriaLabel }}
          </span>
          <span class="text-xs text-gray-500 font-medium">{{ discussion.autor }}</span>
        </div>
        <h3 class="font-semibold text-gray-900 text-sm leading-snug mb-1">{{ discussion.titulo }}</h3>
        <p class="text-gray-600 text-xs line-clamp-2">{{ discussion.resumo }}</p>
        <div class="flex items-center gap-3 mt-2">
          <a
            v-if="postUrl || profileUrl"
            :href="postUrl || profileUrl"
            class="text-xs text-blue-500 hover:text-blue-700 font-medium"
            target="_blank"
            rel="noopener"
            @click.stop
          >
            𝕏 {{ postUrl ? 'Ver post' : 'Ver perfil' }}
          </a>
          <a
            v-if="articleUrl"
            :href="articleUrl"
            class="text-xs text-green-600 hover:text-green-800 font-medium"
            target="_blank"
            rel="noopener"
            @click.stop
          >
            🔗 Artigo
          </a>
          <span v-if="!profileUrl && !articleUrl" class="text-xs text-gray-400">Sem link disponível</span>
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

const postUrl = computed(() => props.discussion?.links?.post_url || null)

const categoriaLabel = computed(() => ({
  especialista: '👤 Especialista',
  revista: '📄 Revista',
  sociedade: '🏛️ Sociedade'
}[props.discussion?.categoria] || '𝕏'))

const categoriaStyle = computed(() => ({
  especialista: 'bg-blue-100 text-blue-700',
  revista: 'bg-purple-100 text-purple-700',
  sociedade: 'bg-green-100 text-green-700'
}[props.discussion?.categoria] || 'bg-gray-100 text-gray-600'))

const profileUrl = computed(() => {
  const autor = props.discussion?.autor || ''
  const handle = autor.startsWith('@') ? autor.slice(1) : null
  return handle ? `https://x.com/${handle}` : null
})

const articleUrl = computed(() => {
  const l = props.discussion?.links
  if (l?.url) return l.url
  if (l?.pubmed) return `https://pubmed.ncbi.nlm.nih.gov/${l.pubmed}/`
  if (l?.doi) return `https://doi.org/${l.doi}`
  return null
})
</script>
