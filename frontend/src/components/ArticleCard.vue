<!-- frontend/src/components/ArticleCard.vue -->
<!--
  Article card — Framework 8 Seções (2026-05-11):
  1. Header (emoji, título, classe/score, publicação)
  2. Contexto clínico (problema + motivação)
  3. Pergunta principal
  4. Desenho do estudo (tabela compacta 2x6)
  5. Pontos-chave (chips numéricos N/HR/NNT)
  6. Principais resultados (narrativa clínica longa)
  7. Interpretação prática (muda conduta?)
  8. Limitações
  9. Conclusão em uma frase (veredito)
  10. Link "Ler" no rodapé

  Fallback gracioso: cada seção tem v-if. Artigos antigos (sem framework)
  mostram só o que têm.
-->
<template>
  <div
    @click="expanded = !expanded"
    class="card cursor-pointer group"
    :class="{ 'opacity-60': isRead(markId) }"
  >
    <!-- Header -->
    <div class="flex items-start gap-3 mb-3">
      <span class="text-2xl flex-shrink-0">{{ article.emoji }}</span>
      <div class="flex-1 min-w-0">
        <div class="flex items-start justify-between gap-2">
          <div class="min-w-0">
            <span
              v-if="studyTypeBadge"
              :class="['inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide mb-1', studyTypeBadge.classes]"
              :title="article.desenho_estudo?.tipo || ''"
            >
              <span>{{ studyTypeBadge.emoji }}</span>
              <span>{{ studyTypeBadge.label }}</span>
            </span>
            <h3 class="font-bold text-base md:text-lg group-hover:text-purple-600 transition-colors break-words">
              {{ article.titulo_pt || article.titulo }}
            </h3>
            <p v-if="article.titulo_pt && article.titulo && article.titulo_pt !== article.titulo"
               class="text-[11px] text-gray-400 italic font-normal mt-0.5 break-words">
              {{ article.titulo }}
            </p>
          </div>
          <div class="flex flex-col items-end gap-1 flex-shrink-0">
            <span :class="[
              'badge',
              article.classe === 'A' ? 'badge-a' : article.classe === 'B' ? 'badge-b' : 'badge-c'
            ]">
              Classe {{ article.classe }}
            </span>
            <span class="text-xs font-bold text-gray-700">{{ article.score }}/10</span>
            <button
              @click.stop="reader.open(article, 'artigo')"
              class="lg:hidden inline-flex items-center text-[11px] px-2 py-1 rounded-full bg-stone-50 border border-stone-300 text-stone-700 hover:bg-stone-100 font-medium transition-colors"
              aria-label="Abrir modo leitura"
            >📖 Ler</button>
          </div>
        </div>
        <p class="text-sm text-gray-600 break-words">{{ article.publicacao }}</p>
      </div>
    </div>

    <!-- Seções detalhadas — ocultas no modo compacto, visíveis ao expandir -->
    <template v-if="expanded">
    <!-- 1. Contexto clínico -->
    <div v-if="article.contexto_clinico" class="mb-3 p-2.5 bg-slate-50 border-l-2 border-slate-400 rounded-r">
      <p class="text-[10px] font-bold uppercase tracking-wider text-slate-700 mb-0.5">🩺 Contexto clínico</p>
      <p class="text-sm text-gray-800 leading-relaxed break-words">{{ article.contexto_clinico }}</p>
    </div>

    <!-- 2. Pergunta principal -->
    <div v-if="article.pergunta_principal" class="mb-3 p-2.5 bg-indigo-50 border-l-2 border-indigo-400 rounded-r">
      <p class="text-[10px] font-bold uppercase tracking-wider text-indigo-700 mb-0.5">❓ Pergunta principal</p>
      <p class="text-sm text-gray-800 leading-relaxed break-words">{{ article.pergunta_principal }}</p>
    </div>

    <!-- 3. Desenho do estudo (tabela 2 colunas) -->
    <div v-if="hasDesenho" class="mb-3 p-2.5 bg-amber-50 border-l-2 border-amber-400 rounded-r">
      <p class="text-[10px] font-bold uppercase tracking-wider text-amber-800 mb-1.5">🔬 Desenho do estudo</p>
      <dl class="grid grid-cols-[auto,1fr] gap-x-3 gap-y-0.5 text-sm">
        <template v-for="(value, key) in desenhoFields" :key="key">
          <dt class="font-semibold text-amber-900 whitespace-nowrap">{{ desenhoLabels[key] }}</dt>
          <dd class="text-gray-800 break-words">{{ value }}</dd>
        </template>
      </dl>
    </div>

    <!-- 4. Pontos-chave (chips numéricos) -->
    <div v-if="article.pontos_chave?.length" class="mb-3 p-2.5 bg-blue-50 border-l-2 border-blue-400 rounded-r">
      <p class="text-[10px] font-bold uppercase tracking-wider text-blue-700 mb-1">📊 Pontos-chave</p>
      <ul class="space-y-0.5">
        <li
          v-for="(ponto, i) in article.pontos_chave"
          :key="i"
          class="text-sm text-gray-800 leading-snug flex gap-1.5"
        >
          <span class="text-blue-500 font-bold flex-shrink-0">▸</span>
          <span class="break-words min-w-0">{{ ponto }}</span>
        </li>
      </ul>
    </div>

    <!-- 5. Principais resultados (parte MAIS importante — sem cap) -->
    <div v-if="article.principais_resultados" class="mb-3 p-3 bg-emerald-50 border-l-2 border-emerald-500 rounded-r">
      <p class="text-[10px] font-bold uppercase tracking-wider text-emerald-700 mb-1">🎯 Principais resultados</p>
      <p class="text-sm text-gray-900 leading-relaxed break-words whitespace-pre-line">{{ article.principais_resultados }}</p>
    </div>

    <!-- 6. Interpretação prática (muda conduta?) -->
    <div v-if="article.interpretacao_pratica" class="mb-3 p-2.5 bg-purple-50 border-l-2 border-purple-400 rounded-r">
      <p class="text-[10px] font-bold uppercase tracking-wider text-purple-700 mb-0.5">💡 Interpretação prática</p>
      <p class="text-sm text-gray-800 leading-relaxed break-words">{{ article.interpretacao_pratica }}</p>
    </div>

    <!-- Fallback legacy: impacto_clinico (apenas se não houver interpretacao_pratica) -->
    <p v-else-if="article.impacto_clinico" class="text-sm text-gray-600 mb-3 italic break-words">💡 {{ article.impacto_clinico }}</p>

    <!-- 7. Limitações -->
    <div v-if="article.limitacoes?.length" class="mb-3 p-2.5 bg-orange-50 border-l-2 border-orange-400 rounded-r">
      <p class="text-[10px] font-bold uppercase tracking-wider text-orange-700 mb-1">⚠️ Limitações</p>
      <ul class="space-y-0.5">
        <li
          v-for="(lim, i) in article.limitacoes"
          :key="i"
          class="text-sm text-gray-800 leading-snug flex gap-1.5"
        >
          <span class="text-orange-500 font-bold flex-shrink-0">▸</span>
          <span class="break-words min-w-0">{{ lim }}</span>
        </li>
      </ul>
    </div>

    </template>
    <!-- /seções detalhadas -->

    <!-- 8. Conclusão em uma frase (veredito final) — SEMPRE visível, mesmo compacto -->
    <div v-if="article.conclusao_uma_frase" class="mb-3 p-3 bg-gradient-to-r from-rose-50 to-pink-50 border-2 border-rose-300 rounded">
      <p class="text-[10px] font-bold uppercase tracking-wider text-rose-700 mb-0.5">⚡ Veredito</p>
      <p class="text-sm font-semibold text-gray-900 leading-relaxed break-words">{{ article.conclusao_uma_frase }}</p>
    </div>

    <!-- Affordance de expandir/recolher (só faz sentido se há seções a mostrar) -->
    <button
      v-if="hasDetails"
      @click.stop="expanded = !expanded"
      class="w-full text-center text-xs text-gray-400 hover:text-gray-600 py-1 mb-2 transition-colors"
    >
      {{ expanded ? '▲ recolher' : '▼ ver análise completa' }}
    </button>

    <!-- Figuras open-access do PMC (preview, ações no modal) -->
    <div v-if="expanded && article.figures?.length" class="mb-3">
      <p class="text-[10px] font-bold uppercase tracking-wider text-gray-600 mb-1.5">
        🖼️ {{ article.figures.length }} {{ article.figures.length === 1 ? 'figura' : 'figuras' }} open-access
      </p>
      <div class="flex gap-2 overflow-x-auto pb-1">
        <img
          v-for="(fig, i) in article.figures.slice(0, 3)"
          :key="i"
          :src="fig.url"
          :alt="fig.caption || `Figura ${i + 1}`"
          loading="lazy"
          referrerpolicy="no-referrer"
          @error="onFigureError($event, i)"
          class="h-20 w-auto rounded border border-gray-200 flex-shrink-0 bg-gray-50 object-cover"
        />
        <div
          v-if="article.figures.length > 3"
          class="h-20 px-3 flex items-center justify-center bg-gray-100 rounded border border-gray-200 text-xs text-gray-600 flex-shrink-0"
        >
          +{{ article.figures.length - 3 }}
        </div>
      </div>
    </div>

    <!-- Footer: source + actions.
         @click.stop no container INTEIRO: o rodapé é uma "barra de controle"
         isolada do toggle do card. Sem isso, no mobile um toque a poucos px do
         botão "Ler" acerta o gap do flex, vaza pro card root e expande por engano
         (as duas funções colidiam na mesma região). -->
    <div class="flex items-center justify-between gap-2 flex-wrap" @click.stop>
      <div class="flex items-center gap-2 flex-wrap">
        <span class="text-xs text-gray-500">
          {{ { revista: '📰 Revista', noticias: '📡 Notícias', substack: '📝 Substack', podcast: '🎙️ Podcast' }[article.categoria_fonte] || '📰 Revista' }}
        </span>
        <span v-if="article.tema_principal"
              class="text-[11px] px-2 py-0.5 rounded-full bg-teal-50 text-teal-700 border border-teal-200 font-medium">
          {{ article.tema_principal }}
        </span>
      </div>
      <div class="flex items-center gap-2 flex-wrap">
        <ShareButton :item="article" type="artigo" />
        <ReadToggle :id="markId" />
        <a
          v-if="article.links?.url"
          :href="article.links.url"
          target="_blank"
          rel="noopener noreferrer"
          class="inline-flex items-center gap-2 px-3 py-2 bg-blue-100 text-blue-700 rounded-lg text-sm font-medium hover:bg-blue-200 transition-all"
          @click.stop="handleExternalLinkClick($event, article.links.url)"
        >
          🔗 Ler
        </a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import ReadToggle from './ReadToggle.vue'
import { useReadMarks } from '../composables/useReadMarks'
import ShareButton from './ShareButton.vue'
import { handleExternalLinkClick } from '../utils/openLink'
import { useReader } from '../composables/useReader'

const reader = useReader()
const { isRead } = useReadMarks()

const props = defineProps({
  article: Object,
  // Estado inicial vindo do toggle global (Compacto/Completo) no App.vue.
  expandedDefault: { type: Boolean, default: false },
})

defineEmits(['click'])

const markId = computed(() => 'artigo:' + (props.article.id || props.article.links?.url || props.article.titulo))

// Estado de expansão local (cada card pode ser aberto/fechado individualmente).
// Inicializa do default global; quando o global muda, segue o global.
const expanded = ref(props.expandedDefault)
watch(() => props.expandedDefault, (v) => { expanded.value = v })

// Só mostra o botão "ver análise" se o artigo tem alguma seção detalhada além
// do veredito (artigos antigos/finos podem só ter título + veredito).
const hasDetails = computed(() => {
  const a = props.article
  return Boolean(
    a?.contexto_clinico || a?.pergunta_principal || a?.principais_resultados ||
    a?.interpretacao_pratica || a?.impacto_clinico ||
    (a?.pontos_chave?.length) || (a?.limitacoes?.length) ||
    hasDesenho.value || (a?.figures?.length)
  )
})

const desenhoLabels = {
  tipo: 'Tipo',
  populacao: 'População',
  n: 'N',
  intervencao: 'Intervenção',
  comparador: 'Comparador',
  seguimento: 'Seguimento',
}

const desenhoFields = computed(() => {
  const d = props.article?.desenho_estudo
  if (!d || typeof d !== 'object') return {}
  const ordered = {}
  for (const k of Object.keys(desenhoLabels)) {
    if (d[k] && typeof d[k] === 'string' && d[k].trim()) {
      ordered[k] = d[k]
    }
  }
  return ordered
})

const hasDesenho = computed(() => Object.keys(desenhoFields.value).length > 0)

// Detecta se o artigo é uma REVISÃO (revisa uma patologia / estado da arte /
// narrative review / systematic review — inclui "revisão sistemática + MA"
// porque tem componente de revisão de literatura) ou uma DIRETRIZ (guideline /
// consenso / statement / posicionamento).
// Meta-análise PURA (sem componente de revisão) NÃO entra — mas na prática não
// aparece nos relatórios; o tipo registrado sempre traz "Revisão sistemática +
// MA" quando há MA, e aí o selo é apropriado. Validado contra 14 dias de dados:
// ~24% dos artigos ganham selo (69 review + 21 diretriz em 366 artigos).
const studyTypeBadge = computed(() => {
  const t = (props.article?.desenho_estudo?.tipo || '').toLowerCase()
  if (!t) return null

  if (/revis(ã|a)o\b|\breview\b|estado da arte|state[\s\-.]of[\s\-.]the[\s\-.]art/.test(t)) {
    return {
      emoji: '📖',
      label: 'Revisão',
      classes: 'bg-amber-100 text-amber-800 border border-amber-300',
    }
  }
  if (/diretriz|consenso|guideline|statement|posicionamento/.test(t)) {
    return {
      emoji: '📋',
      label: 'Diretriz',
      classes: 'bg-blue-100 text-blue-800 border border-blue-300',
    }
  }
  // Editorial / comentário / perspectiva / viewpoint / opinião — opinião de
  // especialista que contextualiza um estudo. Tipos observados nos dados:
  // "Editorial / Comentário", "Comentário", "Editorial / opinião".
  if (/editorial|coment[áa]rio|\bcomment\b|perspectiv|viewpoint|opini[ãa]o/.test(t)) {
    return {
      emoji: '✍️',
      label: 'Editorial',
      classes: 'bg-violet-100 text-violet-800 border border-violet-300',
    }
  }
  return null
})

// PMC figure URLs default to .jpg but some originals are .gif/.png. On
// 404 we just hide the thumbnail rather than show a broken-image icon.
function onFigureError(evt) {
  if (evt?.target) evt.target.style.display = 'none'
}
</script>
