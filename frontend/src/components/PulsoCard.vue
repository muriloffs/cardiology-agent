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
        <div class="flex flex-col items-end gap-1 flex-shrink-0">
          <span v-if="!item.is_destaque_do_dia" class="text-xs text-gray-400">
            {{ item.fontes_cobertura?.length || 0 }} fontes
          </span>
          <button
            @click.stop="reader.open(item, 'pulso')"
            class="lg:hidden inline-flex items-center text-[11px] px-2 py-1 rounded-full bg-stone-50 border border-stone-300 text-stone-700 hover:bg-stone-100 font-medium transition-colors"
            aria-label="Abrir modo leitura"
          >📖 Ler</button>
        </div>
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

      <!-- Histórico relacionado (só aparece se 2+ refs OU se ref tem comment rico) -->
      <div v-if="showHistoricalSection" class="pt-2 border-t border-gray-100">
        <p class="text-[11px] font-bold uppercase tracking-wider text-amber-700 mb-2">
          📅 Histórico relacionado (90 dias)
        </p>
        <ul class="space-y-1.5">
          <li
            v-for="(ref, i) in item.historical_references"
            :key="i"
            class="text-sm text-gray-700 flex gap-2 items-start"
          >
            <span class="text-amber-500 font-bold flex-shrink-0 mt-0.5">▸</span>
            <span class="break-words min-w-0">
              <!-- Date + type prefix -->
              <span class="font-medium text-gray-900">{{ formatHistoricalDate(ref.date) }}</span>
              <span class="text-gray-500"> ({{ ref.type }}):</span>

              <!-- Title as clickable link when accessible -->
              <component
                :is="historicalLinkTag(ref)"
                :href="ref.url || null"
                :target="ref.url ? '_blank' : null"
                :rel="ref.url ? 'noopener noreferrer' : null"
                @click="onHistRefClick($event, ref)"
                :class="[
                  'italic',
                  isClickable(ref)
                    ? 'text-amber-700 hover:text-amber-900 underline decoration-amber-400 hover:decoration-amber-700 cursor-pointer transition-colors'
                    : 'text-gray-700'
                ]"
              >
                {{ ' ' + ref.titulo }}
                <span v-if="isClickable(ref)" class="text-[10px] ml-0.5">↗</span>
              </component>

              <span v-if="ref.comment" class="block text-xs text-gray-600 mt-0.5">{{ ref.comment }}</span>
            </span>
          </li>
        </ul>
      </div>

      <!-- Fontes de cobertura -->
      <div v-if="item.fontes_cobertura?.length" class="pt-2 border-t border-gray-100">
        <p class="text-[11px] font-bold uppercase tracking-wider text-gray-500 mb-2">
          🔗 Cobertura cruzada ({{ item.fontes_cobertura.length }} fonte{{ item.fontes_cobertura.length > 1 ? 's' : '' }})
        </p>
        <div class="flex flex-wrap gap-1.5">
          <component
            v-for="(fonte, i) in item.fontes_cobertura"
            :is="fonteUrl(fonte) ? 'a' : 'span'"
            :href="fonteUrl(fonte) || null"
            :target="fonteUrl(fonte) ? '_blank' : null"
            :rel="fonteUrl(fonte) ? 'noopener noreferrer' : null"
            :key="i"
            @click="onFonteClick($event, fonte)"
            :class="['inline-flex items-center gap-1 px-2 py-1 rounded text-xs',
                     fonteBadgeColor(fonte.tipo),
                     fonteUrl(fonte) ? 'hover:underline hover:opacity-80 transition cursor-pointer' : '']"
          >
            <span>{{ fonteEmoji(fonte.tipo) }}</span>
            <span class="font-medium">{{ fonte.publicacao || fonte.autor || fonte.tipo }}</span>
          </component>
        </div>
      </div>

      <!-- Actions: Share + Things -->
      <div class="flex justify-end gap-2 pt-2 flex-wrap">
        <ShareButton :item="item" type="pulso" />
        <SendToThingsButton :item="item" type="pulso" />
      </div>
    </div>
  </article>
</template>

<script setup>
import { computed } from 'vue'
import SendToThingsButton from './SendToThingsButton.vue'
import ShareButton from './ShareButton.vue'
import { handleExternalLinkClick } from '../utils/openLink'
import { useReader } from '../composables/useReader'

const reader = useReader()

const props = defineProps({
  item: { type: Object, required: true },
  report: { type: Object, default: null }
})

// Emit allows parent (App.vue) to handle clicks on historical pulso refs
// that don't have an external URL — navigates to the historical report.
const emit = defineEmits(['navigate-to-date'])

function isClickable(ref) {
  if (!ref) return false
  // External URL (artigo/noticia/substack) — clickable
  if (ref.url && typeof ref.url === 'string' && ref.url.startsWith('http')) return true
  // Internal pulso reference — clickable if date is valid (navigates to that day's report)
  if (ref.type === 'pulso' && ref.date) return true
  return false
}

function historicalLinkTag(ref) {
  if (!ref) return 'span'
  if (ref.url) return 'a'
  if (ref.type === 'pulso') return 'button'
  return 'span'
}

function onHistoricalClick(ref) {
  if (!ref) return
  if (ref.type === 'pulso' && ref.date) {
    emit('navigate-to-date', ref.date)
  }
}

// Combined click handler for historical refs: route external URLs through
// the iOS-aware helper, fall back to internal navigation for pulso refs.
function onHistRefClick(event, ref) {
  if (ref?.url) {
    handleExternalLinkClick(event, ref.url)
  } else {
    onHistoricalClick(ref)
  }
}

// fontes_cobertura click: only acts if the source has an external URL.
function onFonteClick(event, fonte) {
  const url = fonteUrl(fonte)
  if (url) handleExternalLinkClick(event, url)
}

// Show dedicated historical section when there are 2+ references OR when single
// reference has a rich comment. Single reference without comment usually means
// Sonnet already cited it naturally in razao_destaque/interpretacao_comunidade —
// no need to duplicate visually.
const showHistoricalSection = computed(() => {
  const refs = props.item?.historical_references
  if (!Array.isArray(refs) || refs.length === 0) return false
  if (refs.length >= 2) return true
  return Boolean(refs[0]?.comment && refs[0].comment.length > 20)
})

function formatHistoricalDate(dateStr) {
  if (!dateStr || typeof dateStr !== 'string') return dateStr
  const m = dateStr.match(/^(\d{4})-(\d{2})-(\d{2})/)
  return m ? `${m[3]}/${m[2]}/${m[1]}` : dateStr
}

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
    bluesky: '🦋',
    substack: '📝'
  }[tipo] || '📎'
}

function fonteBadgeColor(tipo) {
  return {
    artigo:   'bg-purple-100 text-purple-800',
    noticia:  'bg-orange-100 text-orange-800',
    podcast:  'bg-indigo-100 text-indigo-800',
    video:    'bg-red-100 text-red-800',
    x:        'bg-gray-200 text-gray-800',
    bluesky:  'bg-sky-100 text-sky-800',
    substack: 'bg-fuchsia-100 text-fuchsia-800'
  }[tipo] || 'bg-gray-100 text-gray-700'
}

// Resolve a clickable URL for a fonte by looking it up in the parent report.
// Videos use video_url as their id; everything else looks up by id in the
// matching source array and pulls a URL from links{}. Returns null when no
// URL can be resolved — caller renders as <span> in that case.
function fonteUrl(fonte) {
  if (!fonte || !fonte.tipo) return null

  if (fonte.tipo === 'video' || fonte.tipo === 'youtube') {
    return fonte.id || null
  }

  if (!props.report || !fonte.id) return null

  const sourceMap = {
    artigo:   props.report.artigos,
    noticia:  props.report.noticias,
    podcast:  props.report.podcasts,
    x:        props.report.discussoes_x,
    bluesky:  props.report.discussoes_bluesky || props.report.discussoes_x,
    substack: props.report.substacks
  }
  const list = sourceMap[fonte.tipo]
  if (!Array.isArray(list)) return null
  const match = list.find(s => s.id === fonte.id)
  if (!match) return null

  // Substack posts store URL at top level (no links{} wrapper)
  if (fonte.tipo === 'substack' && match.url) return match.url
  if (!match.links) return null

  const links = match.links
  if (links.url)         return links.url
  if (links.post_url)    return links.post_url
  if (links.episode_url) return links.episode_url
  if (links.doi)         return `https://doi.org/${links.doi}`
  if (links.pubmed)      return `https://pubmed.ncbi.nlm.nih.gov/${links.pubmed}`
  return null
}
</script>
