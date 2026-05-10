<!-- frontend/src/App.vue -->
<template>
  <div class="min-h-screen bg-white">
    <!-- Header -->
    <HeaderStats
      :report-date="report?.relatorio_data"
      :total-articles="report?.artigos?.length || 0"
      :total-noticias="report?.noticias?.length || 0"
      :total-discussoes="report?.discussoes_x?.length || 0"
      :total-podcasts="report?.podcasts?.length || 0"
      :total-videos="report?.videos_youtube?.length || 0"
      :reading-time="report?.resumo?.tempo_leitura_minutos || 0"
      :has-prev="currentDateIndex < availableDates.length - 1"
      :has-next="currentDateIndex > 0"
      @prev="navigateDate(1)"
      @next="navigateDate(-1)"
    />

    <!-- View Toggle: Relatório vs Ideias do Dia -->
    <div class="bg-gray-50 border-b border-gray-200">
      <div class="max-w-6xl mx-auto px-4 py-2 flex gap-2">
        <button
          @click="currentView = 'report'"
          :class="['px-4 py-2 rounded-lg text-sm font-medium transition-all',
                   currentView === 'report'
                     ? 'bg-purple-600 text-white shadow-sm'
                     : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-200']"
        >
          📰 Relatório
        </button>
        <button
          @click="currentView = 'ideas'"
          :class="['px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2',
                   currentView === 'ideas'
                     ? 'bg-pink-600 text-white shadow-sm'
                     : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-200']"
        >
          💡 Ideias do Dia
          <span v-if="report?.post_ideas?.length"
                :class="['px-1.5 py-0.5 rounded-full text-xs font-bold',
                         currentView === 'ideas' ? 'bg-white text-pink-600' : 'bg-pink-100 text-pink-700']">
            {{ report.post_ideas.length }}
          </span>
        </button>
      </div>
    </div>

    <!-- ============================================================ -->
    <!-- VIEW 1: RELATÓRIO (default) -->
    <!-- ============================================================ -->
    <template v-if="currentView === 'report'">

    <!-- Filters & Section Navigation -->
    <FilterBar
      :selected-class="selectedClass"
      :search-query="searchQuery"
      :total-artigos="report?.artigos?.length || 0"
      :total-noticias="report?.noticias?.length || 0"
      :total-discussoes="report?.discussoes_x?.length || 0"
      :total-podcasts="report?.podcasts?.length || 0"
      :total-videos="report?.videos_youtube?.length || 0"
      @update:selected-class="selectedClass = $event"
      @update:search-query="searchQuery = $event"
      @refresh="loadReport"
    />


    <!-- News Section -->
    <section id="section-noticias" v-if="report?.noticias?.length" class="px-4 py-8 max-w-6xl mx-auto border-t border-gray-100 scroll-mt-4">
      <h2 class="text-2xl font-bold mb-1">📰 Notícias Clínicas</h2>
      <p class="text-sm text-gray-500 mb-4">{{ report.noticias.length }} notícias selecionadas das últimas 24h</p>
      <div class="space-y-3">
        <ArticleCard
          v-for="article in report.noticias"
          :key="article.id"
          :article="article"
          @click="selectedArticle = article"
        />
      </div>
    </section>

    <!-- Podcasts Section -->
    <section id="section-podcasts" v-if="report?.podcasts?.length" class="px-4 py-8 max-w-6xl mx-auto border-t border-gray-100 scroll-mt-4">
      <h2 class="text-2xl font-bold mb-1">🎙️ Podcasts da Semana</h2>
      <p class="text-sm text-gray-500 mb-4">{{ report.podcasts.length }} episódios recentes de cardiologia</p>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
        <PodcastCard
          v-for="podcast in report.podcasts"
          :key="podcast.id"
          :podcast="podcast"
          @click="selectedPodcast = podcast"
        />
      </div>
    </section>

    <!-- YouTube Videos Section -->
    <section id="section-videos" v-if="report?.videos_youtube?.length" class="px-4 py-8 max-w-6xl mx-auto border-t border-gray-100 scroll-mt-4">
      <h2 class="text-2xl font-bold mb-1">📺 Vídeos</h2>
      <p class="text-sm text-gray-500 mb-3">{{ report.videos_youtube.length }} vídeos de canais cardiológicos das últimas 48h</p>
      <div class="flex gap-2 flex-wrap mb-4">
        <button
          v-for="t in [-1, 0, 1, 2]"
          :key="t"
          @click="selectedVideoTier = t"
          :class="[
            'px-3 py-1.5 rounded-full text-xs font-medium transition-all',
            selectedVideoTier === t
              ? t === 0 ? 'bg-yellow-500 text-white'
              : t === 1 ? 'bg-purple-600 text-white'
              : t === 2 ? 'bg-blue-600 text-white'
              : 'bg-gray-800 text-white'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          ]"
        >
          {{ { '-1': 'Todos', '0': '★ BR Pinned', '1': 'Sociedades/Journals', '2': 'Hospitais/Subesp.' }[t] }}
          <span class="ml-1 opacity-70">({{ videoTierCounts[t] || 0 }})</span>
        </button>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
        <VideoCard
          v-for="video in filteredVideos"
          :key="video.video_url"
          :video="video"
        />
      </div>
    </section>

    <!-- X/Twitter Discussions -->
    <section id="section-discussoes" v-if="report?.discussoes_x?.length" class="px-4 py-8 max-w-6xl mx-auto border-t border-gray-100 scroll-mt-4">
      <h2 class="text-2xl font-bold mb-1">𝕏 Discussões no X</h2>
      <p class="text-sm text-gray-500 mb-3">{{ report.discussoes_x.length }} discussões selecionadas das últimas 24h</p>
      <div class="flex gap-2 flex-wrap mb-4">
        <button
          v-for="cat in ['all', 'especialista', 'revista', 'sociedade']"
          :key="cat"
          @click="selectedXCategoria = cat"
          :class="[
            'px-3 py-1.5 rounded-full text-xs font-medium transition-all',
            selectedXCategoria === cat
              ? cat === 'especialista' ? 'bg-blue-600 text-white'
              : cat === 'revista' ? 'bg-purple-600 text-white'
              : cat === 'sociedade' ? 'bg-green-600 text-white'
              : 'bg-gray-800 text-white'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          ]"
        >
          {{ { all: 'Todas', especialista: '👤 Especialistas', revista: '📄 Revistas', sociedade: '🏛️ Sociedades' }[cat] }}
        </button>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
        <XDiscussionCard
          v-for="discussion in filteredDiscussoes"
          :key="discussion.id"
          :discussion="discussion"
          @click="selectedDiscussion = discussion"
        />
      </div>
    </section>

    <!-- Main Article List -->
    <section id="section-artigos" class="px-4 py-8 max-w-6xl mx-auto border-t border-gray-100 scroll-mt-4">
      <h2 class="text-2xl font-bold mb-4">
        📚 Todos os Artigos
        <span class="text-base font-normal text-gray-500 ml-2">
          {{ filteredArticles.length }} de {{ report?.artigos?.length || 0 }}
        </span>
      </h2>

      <!-- Group by class -->
      <template v-for="classe in ['A', 'B', 'C']" :key="classe">
        <div v-if="articlesByClass[classe]?.length">
          <h3 class="text-sm font-semibold uppercase tracking-wide text-gray-400 mt-6 mb-2">
            Classe {{ classe }} — {{ articlesByClass[classe].length }} artigos
          </h3>
          <div class="space-y-3">
            <ArticleCard
              v-for="article in articlesByClass[classe]"
              :key="article.id"
              :article="article"
              @click="selectedArticle = article"
            />
          </div>
        </div>
      </template>

      <p v-if="filteredArticles.length === 0" class="text-center text-gray-500 py-8">
        Nenhum artigo encontrado para os filtros selecionados.
      </p>
    </section>

    </template>
    <!-- ============================================================ -->
    <!-- END VIEW 1: RELATÓRIO -->
    <!-- ============================================================ -->


    <!-- ============================================================ -->
    <!-- VIEW 2: IDEIAS DO DIA -->
    <!-- ============================================================ -->
    <template v-else-if="currentView === 'ideas'">
      <section class="px-4 py-8 max-w-6xl mx-auto">
        <div class="mb-6">
          <h2 class="text-2xl md:text-3xl font-bold mb-2">💡 Ideias de Posts para Hoje</h2>
          <p class="text-sm text-gray-600">
            Geradas a partir do relatório do dia para o público leigo. Use como inspiração + skeleton — desenvolva o post final em outro app.
          </p>
        </div>

        <!-- Type filter -->
        <div v-if="report?.post_ideas?.length" class="flex gap-2 flex-wrap mb-6">
          <button
            v-for="t in availableTypes"
            :key="t.key"
            @click="selectedIdeaType = t.key"
            :class="['px-3 py-1.5 rounded-full text-xs font-medium transition-all flex items-center gap-1.5',
                     selectedIdeaType === t.key
                       ? 'bg-pink-600 text-white shadow-sm'
                       : 'bg-gray-100 text-gray-700 hover:bg-gray-200']"
          >
            <span>{{ t.emoji }}</span>
            <span>{{ t.label }}</span>
            <span class="opacity-70">({{ t.count }})</span>
          </button>
        </div>

        <!-- Ideas grid -->
        <div v-if="filteredIdeas.length" class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <PostIdeaCard
            v-for="idea in filteredIdeas"
            :key="idea.id || idea.ideia"
            :idea="idea"
          />
        </div>

        <!-- Empty / loading state -->
        <div v-else-if="!report" class="text-center py-12 text-gray-500">
          Carregando relatório...
        </div>
        <div v-else-if="!report.post_ideas?.length" class="text-center py-12 text-gray-500">
          <p class="text-lg mb-2">📭 Sem ideias geradas hoje</p>
          <p class="text-sm">As ideias começarão a aparecer no próximo run automático (3 UTC = meia-noite Brasília).</p>
        </div>
        <div v-else class="text-center py-12 text-gray-500">
          Nenhuma ideia do tipo selecionado.
        </div>
      </section>
    </template>


    <!-- Article Detail Modal -->
    <ArticleDetail
      v-if="selectedArticle"
      :article="selectedArticle"
      @close="selectedArticle = null"
    />

    <!-- X Discussion Detail Modal -->
    <XDiscussionDetail
      v-if="selectedDiscussion"
      :discussion="selectedDiscussion"
      @close="selectedDiscussion = null"
    />

    <!-- Podcast Detail Modal -->
    <PodcastDetail
      v-if="selectedPodcast"
      :podcast="selectedPodcast"
      @close="selectedPodcast = null"
    />

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import HeaderStats from './components/HeaderStats.vue'
import FilterBar from './components/FilterBar.vue'
import ArticleCard from './components/ArticleCard.vue'
import ArticleDetail from './components/ArticleDetail.vue'
import XDiscussionCard from './components/XDiscussionCard.vue'
import XDiscussionDetail from './components/XDiscussionDetail.vue'
import PodcastCard from './components/PodcastCard.vue'
import PodcastDetail from './components/PodcastDetail.vue'
import VideoCard from './components/VideoCard.vue'
import PostIdeaCard from './components/PostIdeaCard.vue'
import { fetchLatestReport, fetchIndex, fetchReportByDate } from './utils/api'

const report = ref(null)
const selectedArticle = ref(null)
const selectedDiscussion = ref(null)
const selectedPodcast = ref(null)
const selectedClass = ref('all')
const searchQuery = ref('')
const loading = ref(false)
const selectedXCategoria = ref('all')
const selectedVideoTier = ref(-1)  // -1 = all
const currentView = ref('report')  // 'report' | 'ideas'
const selectedIdeaType = ref('all')
const availableDates = ref([])
const currentDateIndex = ref(0)

async function navigateDate(direction) {
  const newIndex = currentDateIndex.value + direction
  if (newIndex < 0 || newIndex >= availableDates.value.length) return
  currentDateIndex.value = newIndex
  const date = availableDates.value[newIndex]
  report.value = await fetchReportByDate(date)
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const filteredDiscussoes = computed(() => {
  const list = report.value?.discussoes_x || []
  if (selectedXCategoria.value === 'all') return list
  return list.filter(d => d.categoria === selectedXCategoria.value)
})

const filteredVideos = computed(() => {
  const list = report.value?.videos_youtube || []
  if (selectedVideoTier.value === -1) return list
  return list.filter(v => v.tier === selectedVideoTier.value)
})

const videoTierCounts = computed(() => {
  const list = report.value?.videos_youtube || []
  const counts = { '-1': list.length, '0': 0, '1': 0, '2': 0 }
  for (const v of list) {
    counts[String(v.tier)] = (counts[String(v.tier)] || 0) + 1
  }
  return counts
})

const TIPO_META = [
  { key: 'all',         emoji: '📚', label: 'Todas' },
  { key: 'novidade',    emoji: '🆕', label: 'Novidade' },
  { key: 'alerta',      emoji: '🚨', label: 'Alerta' },
  { key: 'lifestyle',   emoji: '🥗', label: 'Lifestyle' },
  { key: 'medicacao',   emoji: '💊', label: 'Medicação' },
  { key: 'evolucao',    emoji: '🔄', label: 'Evolução' },
  { key: 'mito',        emoji: '🚫', label: 'Mito' },
  { key: 'prevencao',   emoji: '🛡️', label: 'Prevenção' },
  { key: 'dado',        emoji: '📊', label: 'Dado' },
  { key: 'faq',         emoji: '❓', label: 'FAQ' },
  { key: 'checklist',   emoji: '📋', label: 'Checklist' },
  { key: 'comparativo', emoji: '🆚', label: 'Comparativo' },
]

// Normalize legacy tipos for filtering/counting (older reports may have these):
// - 'paradigma' (v1) → 'evolucao'
// - 'atencao'   (v2) → 'alerta'
const normalizeTipo = (t) => {
  if (t === 'paradigma') return 'evolucao'
  if (t === 'atencao') return 'alerta'
  return t
}

const availableTypes = computed(() => {
  const ideas = report.value?.post_ideas || []
  return TIPO_META
    .map(t => ({
      ...t,
      count: t.key === 'all'
        ? ideas.length
        : ideas.filter(i => normalizeTipo(i.tipo) === t.key).length
    }))
    .filter(t => t.key === 'all' || t.count > 0)
})

// Update filteredIdeas to also normalize legacy 'paradigma' → 'evolucao'


const filteredIdeas = computed(() => {
  const ideas = report.value?.post_ideas || []
  if (selectedIdeaType.value === 'all') return ideas
  const target = selectedIdeaType.value
  return ideas.filter(i => normalizeTipo(i.tipo) === target)
})

const filteredArticles = computed(() => {
  if (!report.value?.artigos) return []

  return report.value.artigos.filter(article => {
    const matchClass = selectedClass.value === 'all' || article.classe === selectedClass.value
    const matchSearch = !searchQuery.value ||
      article.titulo.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      article.publicacao.toLowerCase().includes(searchQuery.value.toLowerCase())

    return matchClass && matchSearch
  })
})

const articlesByClass = computed(() => {
  const groups = { A: [], B: [], C: [] }
  for (const article of filteredArticles.value) {
    if (groups[article.classe]) groups[article.classe].push(article)
  }
  return groups
})

async function loadReport() {
  loading.value = true
  try {
    const [latestReport, dates] = await Promise.all([fetchLatestReport(), fetchIndex()])
    report.value = latestReport
    if (dates.length > 0) {
      availableDates.value = dates
      currentDateIndex.value = 0
    }
  } catch (error) {
    console.error('Failed to load report:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadReport()
})
</script>
