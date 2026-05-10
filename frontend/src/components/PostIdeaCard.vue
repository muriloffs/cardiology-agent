<!-- frontend/src/components/PostIdeaCard.vue -->
<template>
  <div :class="['rounded-lg border-l-4 bg-white shadow-sm hover:shadow-md transition-shadow p-4 md:p-5', borderClass]">
    <!-- Type badge -->
    <div class="flex items-start justify-between gap-3 mb-3">
      <span :class="['inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wide', badgeClass]">
        <span class="text-base">{{ idea.emoji }}</span>
        {{ tipoLabel }}
      </span>
      <button
        @click="copyToClipboard"
        :class="['flex-shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all',
                 copied ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700 hover:bg-gray-200']"
        :title="copied ? 'Copiado!' : 'Copiar texto formatado'"
      >
        {{ copied ? '✓ Copiado' : '📋 Copiar' }}
      </button>
    </div>

    <!-- Ideia -->
    <p class="text-base md:text-lg font-bold text-gray-900 leading-snug mb-3">
      {{ idea.ideia }}
    </p>

    <!-- Bullets -->
    <ul class="space-y-1.5 mb-4">
      <li
        v-for="(bullet, i) in idea.bullets"
        :key="i"
        class="text-sm text-gray-700 flex items-start gap-2 leading-relaxed"
      >
        <span :class="['flex-shrink-0 mt-0.5', accentTextClass]">▸</span>
        <span>{{ bullet }}</span>
      </li>
    </ul>

    <!-- Fonte -->
    <a
      v-if="idea.fonte?.url"
      :href="idea.fonte.url"
      target="_blank"
      rel="noopener"
      class="inline-flex items-start gap-1.5 text-xs text-gray-500 hover:text-gray-800 transition-colors group/fonte"
    >
      <span class="flex-shrink-0 mt-0.5">🔗</span>
      <span>
        <span class="font-semibold">{{ idea.fonte.publicacao || 'Fonte' }}</span>
        <span class="ml-1">— {{ truncate(idea.fonte.titulo_origem, 80) }}</span>
        <span class="block text-[10px] text-gray-400 group-hover/fonte:text-gray-600">{{ idea.fonte.tipo }} · ver original ↗</span>
      </span>
    </a>
    <div v-else class="text-xs text-gray-400">
      Fonte: {{ idea.fonte?.publicacao || 'Relatório' }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  idea: { type: Object, required: true }
})

const copied = ref(false)

const TIPO_CONFIG = {
  novidade:   { label: 'Novidade',   border: 'border-blue-500',    badge: 'bg-blue-100 text-blue-800',    accent: 'text-blue-500' },
  atencao:    { label: 'Atenção',    border: 'border-red-500',     badge: 'bg-red-100 text-red-800',      accent: 'text-red-500' },
  lifestyle:  { label: 'Lifestyle',  border: 'border-green-500',   badge: 'bg-green-100 text-green-800',  accent: 'text-green-500' },
  medicacao:  { label: 'Medicação',  border: 'border-indigo-500',  badge: 'bg-indigo-100 text-indigo-800',accent: 'text-indigo-500' },
  paradigma:  { label: 'Paradigma',  border: 'border-purple-500',  badge: 'bg-purple-100 text-purple-800',accent: 'text-purple-500' },
  mito:       { label: 'Mito',       border: 'border-orange-500',  badge: 'bg-orange-100 text-orange-800',accent: 'text-orange-500' },
  prevencao:  { label: 'Prevenção',  border: 'border-teal-500',    badge: 'bg-teal-100 text-teal-800',    accent: 'text-teal-500' },
}

const cfg = computed(() => TIPO_CONFIG[props.idea.tipo] || TIPO_CONFIG.novidade)
const tipoLabel = computed(() => cfg.value.label)
const borderClass = computed(() => cfg.value.border)
const badgeClass = computed(() => cfg.value.badge)
const accentTextClass = computed(() => cfg.value.accent)

function truncate(s, n) {
  if (!s) return ''
  return s.length > n ? s.slice(0, n - 1) + '…' : s
}

async function copyToClipboard() {
  const i = props.idea
  const lines = []
  lines.push(`${i.emoji} ${tipoLabel.value.toUpperCase()}`)
  lines.push('')
  lines.push(`IDEIA: ${i.ideia}`)
  lines.push('')
  lines.push('PONTOS-CHAVE:')
  for (const b of (i.bullets || [])) {
    lines.push(`• ${b}`)
  }
  lines.push('')
  if (i.fonte) {
    lines.push(`FONTE: ${i.fonte.publicacao || ''} — ${i.fonte.titulo_origem || ''}`)
    if (i.fonte.url) lines.push(i.fonte.url)
  }
  const text = lines.join('\n')
  try {
    await navigator.clipboard.writeText(text)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch (err) {
    console.error('Clipboard write failed:', err)
    alert('Não foi possível copiar. Selecione o texto manualmente.')
  }
}
</script>
