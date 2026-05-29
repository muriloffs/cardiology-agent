<!--
  SearchResults — substitui a view normal quando há query ativa em useSearch().

  Lista resultados agrupados por data (mais recente primeiro), com chip do
  tipo, título e snippet centrado no match. Click no resultado abre a fonte
  externa (não tenta replicar o card cheio — seria duplicação).
-->
<template>
  <div class="max-w-4xl mx-auto px-3 py-4">
    <div v-if="loading" class="text-center text-gray-500 py-8">
      <p>Carregando histórico…</p>
      <p class="text-xs mt-2">A primeira busca demora ~2-5s pra baixar todos os relatórios.</p>
    </div>

    <div v-else-if="loadError" class="text-center text-red-600 py-8">
      <p>Falha ao carregar histórico: {{ loadError }}</p>
    </div>

    <div v-else-if="results.length === 0" class="text-center text-gray-500 py-8">
      <p>Nenhum resultado para <span class="font-semibold">"{{ query }}"</span>.</p>
      <p class="text-xs mt-2">Tente um termo mais curto ou diferente.</p>
    </div>

    <template v-else>
      <!-- Sumário por tipo -->
      <div class="flex flex-wrap gap-2 mb-4 text-xs">
        <span
          v-for="(count, type) in resultsByType"
          :key="type"
          :class="['inline-flex items-center gap-1 px-2 py-0.5 rounded-full', chipColor(type)]"
        >
          <span>{{ typeEmoji(type) }}</span>
          <span class="font-medium">{{ typeLabel(type) }}: {{ count }}</span>
        </span>
      </div>

      <!-- Resultados agrupados por data -->
      <section v-for="[date, items] in resultsByDate" :key="date" class="mb-6">
        <h3 class="text-xs font-bold uppercase tracking-wider text-gray-500 mb-2">
          📅 {{ formatDate(date) }}
        </h3>
        <ul class="space-y-2">
          <li
            v-for="(r, i) in items"
            :key="i"
            class="border border-gray-200 rounded-lg p-3 bg-white hover:border-purple-300 transition-colors"
          >
            <div class="flex items-start gap-2 mb-1">
              <span :class="['inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold uppercase whitespace-nowrap flex-shrink-0', chipColor(r.type)]">
                {{ typeEmoji(r.type) }} {{ typeLabel(r.type) }}
              </span>
              <h4 class="font-semibold text-sm text-gray-900 leading-snug break-words">
                {{ r.item.titulo || r.item.ideia || '(sem título)' }}
              </h4>
            </div>
            <p
              v-if="r.snippet"
              class="text-xs text-gray-600 leading-relaxed break-words"
              v-html="highlightSnippet(r.snippet, query)"
            ></p>
            <div class="flex items-center gap-3 mt-2">
              <a
                v-if="getUrl(r)"
                :href="getUrl(r)"
                target="_blank"
                rel="noopener noreferrer"
                class="text-xs text-blue-600 hover:text-blue-800 font-medium"
                @click.stop="handleExternalLinkClick($event, getUrl(r))"
              >
                🔗 Abrir fonte
              </a>
              <span class="text-[11px] text-gray-400">
                {{ r.item.publicacao || r.item.autor || r.item.canal || '' }}
              </span>
            </div>
          </li>
        </ul>
      </section>
    </template>
  </div>
</template>

<script setup>
import { useSearch } from '../composables/useSearch'
import { handleExternalLinkClick } from '../utils/openLink'

const { query, loading, loadError, results, resultsByDate, resultsByType } = useSearch()

const TYPE_META = {
  artigo:    { emoji: '🔬', label: 'Artigo',   color: 'bg-blue-100 text-blue-800' },
  noticia:   { emoji: '📰', label: 'Notícia',  color: 'bg-orange-100 text-orange-800' },
  pulso:     { emoji: '⚡', label: 'Pulso',     color: 'bg-amber-100 text-amber-800' },
  substack:  { emoji: '📝', label: 'Substack', color: 'bg-purple-100 text-purple-800' },
  podcast:   { emoji: '🎙️', label: 'Podcast',  color: 'bg-pink-100 text-pink-800' },
  discussao: { emoji: '𝕏',  label: 'X',         color: 'bg-gray-200 text-gray-800' },
  video:     { emoji: '📺', label: 'Vídeo',    color: 'bg-red-100 text-red-800' },
  idea:      { emoji: '💡', label: 'Ideia',    color: 'bg-yellow-100 text-yellow-800' },
}

function typeEmoji(t) { return TYPE_META[t]?.emoji || '•' }
function typeLabel(t) { return TYPE_META[t]?.label || t }
function chipColor(t) { return TYPE_META[t]?.color || 'bg-gray-100 text-gray-700' }

function formatDate(dateStr) {
  // YYYY-MM-DD → DD/MM/YYYY com nome do dia
  try {
    const [y, m, d] = dateStr.split('-').map(Number)
    const dt = new Date(y, m - 1, d)
    const dia = dt.toLocaleDateString('pt-BR', { weekday: 'long' })
    return `${dia.charAt(0).toUpperCase() + dia.slice(1)} · ${String(d).padStart(2, '0')}/${String(m).padStart(2, '0')}/${y}`
  } catch {
    return dateStr
  }
}

function getUrl(r) {
  const it = r.item
  return (
    it.links?.url ||
    it.links?.episode_url ||
    it.links?.post_url ||
    it.url ||
    it.video_url ||
    (it.links?.doi ? `https://doi.org/${it.links.doi}` : null) ||
    (it.links?.pubmed ? `https://pubmed.ncbi.nlm.nih.gov/${it.links.pubmed}/` : null) ||
    null
  )
}

/**
 * Destaca o termo buscado no snippet (case + accent insensitive).
 * Escape HTML antes pra não permitir injeção.
 */
function highlightSnippet(snippet, q) {
  const term = (q || '').trim()
  if (!term) return escapeHtml(snippet)
  const escaped = escapeHtml(snippet)
  // Match accent/case-insensitive: usa regex Unicode flag + lookalikes via NFD-normalize
  try {
    const norm = term
      .normalize('NFD')
      .replace(/[̀-ͯ]/g, '')
      .toLowerCase()
    // Constrói regex que aceita variações acentuadas. Pra simplicidade: matches
    // sequências do tamanho do termo, comparando NFD-normalizado.
    const out = []
    const hay = snippet
    const lowNorm = hay.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
    let i = 0
    while (i < hay.length) {
      const idx = lowNorm.indexOf(norm, i)
      if (idx === -1) {
        out.push(escapeHtml(hay.slice(i)))
        break
      }
      out.push(escapeHtml(hay.slice(i, idx)))
      out.push('<mark class="bg-yellow-200 text-gray-900 rounded px-0.5">')
      out.push(escapeHtml(hay.slice(idx, idx + norm.length)))
      out.push('</mark>')
      i = idx + norm.length
    }
    return out.join('')
  } catch {
    return escaped
  }
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}
</script>
