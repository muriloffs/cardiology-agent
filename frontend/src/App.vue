<!-- frontend/src/App.vue -->
<template>
  <div class="min-h-screen bg-white">
    <!-- Header -->
    <HeaderStats
      :report-date="report?.relatorio_data"
      :total-articles="report?.resumo?.total_artigos || 0"
      :reading-time="report?.resumo?.tempo_leitura_minutos || 0"
      :has-prev="currentDateIndex < availableDates.length - 1"
      :has-next="currentDateIndex > 0"
      @prev="navigateDate(1)"
      @next="navigateDate(-1)"
    />

    <!-- Filters -->
    <FilterBar
      :selected-class="selectedClass"
      :selected-source="selectedSource"
      :search-query="searchQuery"
      @update:selected-class="selectedClass = $event"
      :available-sources="availableSources"
      @update:selected-source="selectedSource = $event"
      @update:search-query="searchQuery = $event"
      @refresh="loadReport"
    />


    <!-- News Section -->
    <section v-if="report?.noticias?.length" class="px-4 py-8 max-w-6xl mx-auto border-t border-gray-100">
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

    <!-- X/Twitter Discussions -->
    <section v-if="report?.discussoes_x?.length" class="px-4 py-8 max-w-6xl mx-auto border-t border-gray-100">
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
    <section class="px-4 py-8 max-w-6xl mx-auto border-t border-gray-100">
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
import { fetchLatestReport, fetchIndex, fetchReportByDate } from './utils/api'

const report = ref(null)
const selectedArticle = ref(null)
const selectedDiscussion = ref(null)
const selectedClass = ref('all')
const selectedSource = ref('all')
const searchQuery = ref('')
const loading = ref(false)
const selectedXCategoria = ref('all')
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

const filteredArticles = computed(() => {
  if (!report.value?.artigos) return []

  return report.value.artigos.filter(article => {
    const matchClass = selectedClass.value === 'all' || article.classe === selectedClass.value
    const matchSource = selectedSource.value === 'all' || article.categoria_fonte === selectedSource.value
    const matchSearch = !searchQuery.value ||
      article.titulo.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      article.publicacao.toLowerCase().includes(searchQuery.value.toLowerCase())

    return matchClass && matchSource && matchSearch
  })
})

const availableSources = computed(() => {
  if (!report.value?.artigos) return ['all', 'revista']
  const found = new Set(report.value.artigos.map(a => a.categoria_fonte).filter(Boolean))
  const order = ['all', 'revista', 'noticias', 'substack']
  return order.filter(s => s === 'all' || found.has(s))
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
