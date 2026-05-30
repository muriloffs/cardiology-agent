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
        <h3 class="font-semibold text-gray-900 text-sm leading-snug mb-1">{{ discussion.titulo_pt || discussion.titulo }}</h3>
        <p v-if="discussion.titulo_pt && discussion.titulo && discussion.titulo_pt !== discussion.titulo"
           class="text-[10px] text-gray-400 italic font-normal mb-1 break-words">
          {{ discussion.titulo }}
        </p>
        <p class="text-gray-600 text-xs line-clamp-2">{{ discussion.resumo }}</p>

        <!-- X media (thumbnails + download). Grid 2x2 (até 4 imgs). -->
        <div v-if="mediaUrls.length" class="mt-2 grid grid-cols-2 gap-1.5">
          <div
            v-for="(m, i) in mediaUrls.slice(0, 4)"
            :key="i"
            class="relative group/img"
          >
            <img
              :src="m"
              :alt="`X media ${i + 1}`"
              loading="lazy"
              referrerpolicy="no-referrer"
              @error="onMediaError"
              class="w-full h-24 object-cover rounded border border-gray-200 bg-gray-50"
            />
            <a
              :href="downloadUrl(m, i)"
              @click.stop
              class="absolute bottom-1 right-1 px-1.5 py-0.5 bg-black/70 text-white text-[10px] rounded opacity-0 group-hover/img:opacity-100 transition-opacity"
              title="Baixar imagem"
            >
              ⬇
            </a>
          </div>
        </div>

        <div class="flex items-center gap-3 mt-2">
          <a
            v-if="postUrl || profileUrl"
            :href="postUrl || profileUrl"
            class="text-xs text-blue-500 hover:text-blue-700 font-medium"
            target="_blank"
            rel="noopener noreferrer"
            @click.stop="handleExternalLinkClick($event, postUrl || profileUrl)"
          >
            𝕏 {{ postUrl ? 'Ver post' : 'Ver perfil' }}
          </a>
          <a
            v-if="articleUrl"
            :href="articleUrl"
            class="text-xs text-green-600 hover:text-green-800 font-medium"
            target="_blank"
            rel="noopener noreferrer"
            @click.stop="handleExternalLinkClick($event, articleUrl)"
          >
            🔗 Artigo
          </a>
          <span v-if="!profileUrl && !articleUrl" class="text-xs text-gray-400">Sem link disponível</span>
          <div class="ml-auto flex items-center gap-2 flex-wrap">
            <ShareButton :item="discussion" type="discussao" />
            <SendToThingsButton :item="discussion" type="discussao" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import SendToThingsButton from './SendToThingsButton.vue'
import ShareButton from './ShareButton.vue'
import { handleExternalLinkClick } from '../utils/openLink'

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

const mediaUrls = computed(() => {
  const m = props.discussion?.media
  return Array.isArray(m) ? m.filter((u) => typeof u === 'string') : []
})

function downloadUrl(url, index) {
  const id = props.discussion?.id || 'x'
  const ext = (url.match(/\.([a-z0-9]{3,4})(?:\?|$)/i)?.[1] || 'jpg').toLowerCase()
  const filename = `${id}_media${index + 1}.${ext}`
  const params = new URLSearchParams({ url, filename })
  return `/api/proxy-image?${params.toString()}`
}

function onMediaError(evt) {
  const container = evt?.target?.closest('.group\\/img') || evt?.target?.parentElement
  if (container) container.style.display = 'none'
}
</script>
