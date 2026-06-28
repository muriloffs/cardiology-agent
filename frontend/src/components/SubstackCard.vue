<!-- frontend/src/components/SubstackCard.vue -->
<!--
  Substack post card. Rich layout: avatar (initials) + author + publication,
  title, theme badge, bullet points, summary, tags + read-more link.
  Categoria drives accent color; avatar color derived from publicacao hash.
-->
<template>
  <article
    class="rounded-lg border border-gray-200 bg-white shadow-sm hover:shadow-md transition-shadow overflow-hidden"
    :class="{ 'grayscale opacity-60': isRead(markId) }"
  >
    <!-- Header: avatar + author + publication + date -->
    <header class="px-4 md:px-5 pt-4 pb-2 flex items-start gap-3">
      <!-- Avatar with initials -->
      <div
        :class="['flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center text-white text-sm font-bold',
                 avatarColor]"
      >
        {{ authorInitials }}
      </div>

      <!-- Author + publication + date -->
      <div class="flex-1 min-w-0">
        <p class="text-sm font-semibold text-gray-900 truncate">
          {{ post.autor || 'Autor desconhecido' }}
        </p>
        <p class="text-xs text-gray-500 truncate">
          📝 {{ post.publicacao }}
          <span v-if="post.data_pub" class="ml-1">· {{ formattedDate }}</span>
        </p>
      </div>

      <!-- Category badge + reader trigger -->
      <div class="flex flex-col items-end gap-1 flex-shrink-0">
        <span
          v-if="post.tema"
          :class="['inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide',
                   categoriaBadgeColor]"
        >
          {{ post.tema }}
        </span>
        <button
          @click.stop="reader.open(post, 'substack')"
          class="lg:hidden inline-flex items-center text-[11px] px-2 py-1 rounded-full bg-stone-50 border border-stone-300 text-stone-700 hover:bg-stone-100 font-medium transition-colors"
          aria-label="Abrir modo leitura"
        >📖 Ler</button>
      </div>
    </header>

    <!-- Body -->
    <div class="px-4 md:px-5 pb-4 space-y-3">
      <!-- Title -->
      <div>
        <h3 class="font-bold text-base md:text-lg leading-snug text-gray-900">
          {{ post.titulo_pt || post.titulo }}
        </h3>
        <p v-if="post.titulo_pt && post.titulo && post.titulo_pt !== post.titulo"
           class="text-[11px] text-gray-400 italic font-normal mt-0.5 break-words">
          {{ post.titulo }}
        </p>
      </div>

      <!-- Bullets -->
      <ul v-if="post.bullets?.length" class="space-y-1.5">
        <li
          v-for="(bullet, i) in post.bullets"
          :key="i"
          class="text-sm text-gray-700 leading-relaxed flex gap-2"
        >
          <span class="flex-shrink-0 text-purple-500 font-bold mt-0.5">•</span>
          <span>{{ bullet }}</span>
        </li>
      </ul>

      <!-- Resumo -->
      <p v-if="post.resumo" class="text-sm text-gray-600 italic leading-relaxed pt-1 border-t border-gray-100">
        {{ post.resumo }}
      </p>

      <!-- Contextual fields (Combo Total) — only render when present -->
      <div v-if="post.quem_se_aplica || post.evidencia_chave || post.contraponto" class="space-y-2 pt-1 border-t border-gray-100">
        <div v-if="post.quem_se_aplica" class="text-xs">
          <span class="font-bold text-blue-700 uppercase tracking-wide">👥 Para quem </span>
          <span class="text-gray-700">{{ post.quem_se_aplica }}</span>
        </div>
        <div v-if="post.evidencia_chave" class="text-xs">
          <span class="font-bold text-emerald-700 uppercase tracking-wide">📊 Evidência </span>
          <span class="text-gray-700">{{ post.evidencia_chave }}</span>
        </div>
        <div v-if="post.contraponto" class="text-xs">
          <span class="font-bold text-amber-700 uppercase tracking-wide">⚠️ Contraponto </span>
          <span class="text-gray-700">{{ post.contraponto }}</span>
        </div>
      </div>

      <!-- Tags + Read more -->
      <div class="flex items-center justify-between gap-3 pt-1 flex-wrap">
        <div v-if="post.tags?.length" class="flex flex-wrap gap-1">
          <span
            v-for="(tag, i) in post.tags"
            :key="i"
            class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-gray-100 text-gray-600"
          >
            #{{ tag }}
          </span>
        </div>
        <div class="flex items-center gap-2 ml-auto flex-wrap">
          <ShareButton :item="post" type="substack" />
          <ReadToggle :id="markId" />
          <a
            :href="post.url"
            target="_blank"
            rel="noopener noreferrer"
            class="inline-flex items-center gap-1 text-xs font-semibold text-purple-700 hover:text-purple-900 hover:underline whitespace-nowrap"
            @click.stop="handleExternalLinkClick($event, post.url)"
          >
            Ler completo →
          </a>
        </div>
      </div>
    </div>
  </article>
</template>

<script setup>
import { computed } from 'vue'
import ReadToggle from './ReadToggle.vue'
import { useReadMarks } from '../composables/useReadMarks'
import ShareButton from './ShareButton.vue'
import { handleExternalLinkClick } from '../utils/openLink'
import { useReader } from '../composables/useReader'

const reader = useReader()
const { isRead } = useReadMarks()

const props = defineProps({
  post: { type: Object, required: true }
})

const markId = computed(() => 'substack:' + (props.post.id || props.post.url))

const authorInitials = computed(() => {
  const name = props.post.autor || props.post.publicacao || '?'
  const parts = name.trim().split(/\s+/).filter(Boolean)
  if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
  return name.substring(0, 2).toUpperCase()
})

// Deterministic color from publication name — keeps avatars stable across renders
const avatarColor = computed(() => {
  const palette = [
    'bg-purple-500', 'bg-blue-500', 'bg-emerald-500',
    'bg-amber-500',  'bg-rose-500',  'bg-indigo-500',
    'bg-teal-500',   'bg-orange-500',
  ]
  const key = props.post.publicacao || ''
  let hash = 0
  for (let i = 0; i < key.length; i++) hash = (hash * 31 + key.charCodeAt(i)) & 0xffff
  return palette[hash % palette.length]
})

// Categoria → tema-badge color
const categoriaBadgeColor = computed(() => {
  return {
    'tech-policy':            'bg-blue-100 text-blue-800',
    'trials-critique':        'bg-red-100 text-red-800',
    'consumer-tech':          'bg-amber-100 text-amber-800',
    'trials-summary':         'bg-purple-100 text-purple-800',
    'clinical-pearls':        'bg-emerald-100 text-emerald-800',
    'ai-genomics':            'bg-indigo-100 text-indigo-800',
    'prevention-philosophy':  'bg-teal-100 text-teal-800',
    'education':              'bg-pink-100 text-pink-800',
    'br-clinical':            'bg-green-100 text-green-800',
    'br-congress':            'bg-yellow-100 text-yellow-800',
  }[props.post.categoria] || 'bg-gray-100 text-gray-700'
})

const formattedDate = computed(() => {
  const raw = props.post.data_pub
  if (!raw) return ''
  const m = raw.match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (!m) return raw
  return `${m[3]}/${m[2]}`
})
</script>
