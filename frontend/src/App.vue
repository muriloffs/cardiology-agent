<!-- frontend/src/App.vue -->
<template>
  <div class="min-h-screen bg-white">
    <!-- Header -->
    <HeaderStats
      :report-date="report?.relatorio_data"
      :reading-time="report?.resumo?.tempo_leitura_minutos || 0"
      :has-prev="currentDateIndex < availableDates.length - 1"
      :has-next="currentDateIndex > 0"
      @prev="navigateDate(1)"
      @next="navigateDate(-1)"
    />

    <!-- Congress banner (acontecendo agora + próximos 14 dias) -->
    <CongressBanner />

    <!-- View Toggle (also serves as primary counter — replaces HeaderStats grid) -->
    <div class="bg-gray-50 border-b border-gray-200">
      <div class="max-w-6xl mx-auto px-4 py-3 flex gap-2 md:gap-3 flex-wrap">
        <button
          @click="currentView = 'artigos'"
          :class="['px-2.5 md:px-5 py-1.5 md:py-3 rounded-lg text-sm md:text-lg font-semibold transition-all flex items-center gap-1.5 md:gap-2.5',
                   currentView === 'artigos'
                     ? 'bg-purple-600 text-white shadow-md'
                     : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-200']"
        >
          📚 Artigos
          <span v-if="report?.artigos?.length"
                :class="['px-1.5 md:px-2 py-0.5 rounded-full text-xs md:text-sm font-bold',
                         currentView === 'artigos' ? 'bg-white text-purple-700' : 'bg-purple-100 text-purple-700']">
            {{ report.artigos.length }}
          </span>
        </button>
        <button
          @click="currentView = 'noticias'"
          :class="['px-2.5 md:px-5 py-1.5 md:py-3 rounded-lg text-sm md:text-lg font-semibold transition-all flex items-center gap-1.5 md:gap-2.5',
                   currentView === 'noticias'
                     ? 'bg-orange-600 text-white shadow-md'
                     : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-200']"
        >
          📰 Notícias
          <span v-if="report?.noticias?.length"
                :class="['px-1.5 md:px-2 py-0.5 rounded-full text-xs md:text-sm font-bold',
                         currentView === 'noticias' ? 'bg-white text-orange-700' : 'bg-orange-100 text-orange-700']">
            {{ report.noticias.length }}
          </span>
        </button>
        <button
          @click="currentView = 'discussoes'"
          :class="['px-2.5 md:px-5 py-1.5 md:py-3 rounded-lg text-sm md:text-lg font-semibold transition-all flex items-center gap-1.5 md:gap-2.5',
                   currentView === 'discussoes'
                     ? 'bg-gray-800 text-white shadow-md'
                     : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-200']"
        >
          𝕏 Discussões
          <span v-if="report?.discussoes_x?.length"
                :class="['px-1.5 md:px-2 py-0.5 rounded-full text-xs md:text-sm font-bold',
                         currentView === 'discussoes' ? 'bg-white text-gray-800' : 'bg-gray-200 text-gray-800']">
            {{ report.discussoes_x.length }}
          </span>
        </button>
        <button
          @click="currentView = 'pulso'"
          :class="['px-2.5 md:px-5 py-1.5 md:py-3 rounded-lg text-sm md:text-lg font-semibold transition-all flex items-center gap-1.5 md:gap-2.5',
                   currentView === 'pulso'
                     ? 'bg-amber-600 text-white shadow-md'
                     : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-200']"
        >
          🌍 Pulso
          <span v-if="report?.pulso?.length"
                :class="['px-1.5 md:px-2 py-0.5 rounded-full text-xs md:text-sm font-bold',
                         currentView === 'pulso' ? 'bg-white text-amber-700' : 'bg-amber-100 text-amber-700']">
            {{ report.pulso.length }}
          </span>
        </button>
        <button
          @click="currentView = 'substacks'"
          :class="['px-2.5 md:px-5 py-1.5 md:py-3 rounded-lg text-sm md:text-lg font-semibold transition-all flex items-center gap-1.5 md:gap-2.5',
                   currentView === 'substacks'
                     ? 'bg-fuchsia-700 text-white shadow-md'
                     : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-200']"
        >
          📝 Substacks
          <span v-if="report?.substacks?.length"
                :class="['px-1.5 md:px-2 py-0.5 rounded-full text-xs md:text-sm font-bold',
                         currentView === 'substacks' ? 'bg-white text-fuchsia-700' : 'bg-fuchsia-100 text-fuchsia-700']">
            {{ report.substacks.length }}
          </span>
        </button>
        <button
          @click="currentView = 'videos'"
          :class="['px-2.5 md:px-5 py-1.5 md:py-3 rounded-lg text-sm md:text-lg font-semibold transition-all flex items-center gap-1.5 md:gap-2.5',
                   currentView === 'videos'
                     ? 'bg-red-600 text-white shadow-md'
                     : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-200']"
        >
          📺 Vídeos
          <span v-if="report?.videos_youtube?.length"
                :class="['px-1.5 md:px-2 py-0.5 rounded-full text-xs md:text-sm font-bold',
                         currentView === 'videos' ? 'bg-white text-red-600' : 'bg-red-100 text-red-700']">
            {{ report.videos_youtube.length }}
          </span>
        </button>
        <button
          @click="currentView = 'podcasts'"
          :class="['px-2.5 md:px-5 py-1.5 md:py-3 rounded-lg text-sm md:text-lg font-semibold transition-all flex items-center gap-1.5 md:gap-2.5',
                   currentView === 'podcasts'
                     ? 'bg-purple-700 text-white shadow-md'
                     : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-200']"
        >
          🎙️ Podcasts
          <span v-if="report?.podcasts?.length"
                :class="['px-1.5 md:px-2 py-0.5 rounded-full text-xs md:text-sm font-bold',
                         currentView === 'podcasts' ? 'bg-white text-purple-700' : 'bg-purple-100 text-purple-700']">
            {{ report.podcasts.length }}
          </span>
        </button>
        <button
          @click="currentView = 'ideas'"
          :class="['px-2.5 md:px-5 py-1.5 md:py-3 rounded-lg text-sm md:text-lg font-semibold transition-all flex items-center gap-1.5 md:gap-2.5',
                   currentView === 'ideas'
                     ? 'bg-pink-600 text-white shadow-md'
                     : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-200']"
        >
          💡 Ideias
          <span v-if="report?.post_ideas?.length"
                :class="['px-1.5 md:px-2 py-0.5 rounded-full text-xs md:text-sm font-bold',
                         currentView === 'ideas' ? 'bg-white text-pink-600' : 'bg-pink-100 text-pink-700']">
            {{ report.post_ideas.length }}
          </span>
        </button>
      </div>
    </div>

    <!-- ============================================================ -->
    <!-- VIEW 1: ARTIGOS -->
    <!-- ============================================================ -->
    <template v-if="currentView === 'artigos'">
      <FilterBar
        :selected-class="selectedClass"
        @update:selected-class="selectedClass = $event"
        @refresh="loadReport"
      />
      <section class="px-4 py-8 max-w-6xl mx-auto">
        <h2 class="text-2xl md:text-3xl font-bold mb-2">📚 Artigos Científicos</h2>
        <p class="text-sm text-gray-500 mb-6">
          {{ filteredArticles.length }} de {{ report?.artigos?.length || 0 }} artigos{{ selectedClass !== 'all' ? ' (Classe ' + selectedClass + ')' : '' }}
        </p>

        <template v-for="classe in ['A', 'B', 'C']" :key="classe">
          <div v-if="articlesByClass[classe]?.length" class="mb-6">
            <h3 class="text-sm font-semibold uppercase tracking-wide text-gray-400 mb-2">
              Classe {{ classe }} — {{ articlesByClass[classe].length }} artigos
            </h3>
            <div class="space-y-3">
              <ArticleCard
                v-for="article in articlesByClass[classe]"
                :key="article.id"
                :article="article"
                @click="openArticle(article)"
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
    <!-- VIEW 2: NOTÍCIAS -->
    <!-- ============================================================ -->
    <template v-else-if="currentView === 'noticias'">
      <FilterBar
        :selected-class="selectedClass"
        @update:selected-class="selectedClass = $event"
        @refresh="loadReport"
      />
      <section class="px-4 py-8 max-w-6xl mx-auto">
        <h2 class="text-2xl md:text-3xl font-bold mb-2">📰 Notícias Clínicas</h2>
        <p class="text-sm text-gray-500 mb-6">
          {{ filteredNoticias.length }} de {{ report?.noticias?.length || 0 }} notícias das últimas 24h{{ selectedClass !== 'all' ? ' (Classe ' + selectedClass + ')' : '' }}
        </p>

        <div v-if="filteredNoticias.length" class="space-y-3">
          <NoticiaCard
            v-for="article in filteredNoticias"
            :key="article.id"
            :noticia="article"
            @click="openArticle(article)"
          />
        </div>
        <p v-else-if="!report" class="text-center text-gray-500 py-12">
          Carregando relatório...
        </p>
        <p v-else-if="!report.noticias?.length" class="text-center text-gray-500 py-12">
          📭 Sem notícias neste relatório.
        </p>
        <p v-else class="text-center text-gray-500 py-8">
          Nenhuma notícia Classe {{ selectedClass }} hoje.
        </p>
      </section>
    </template>


    <!-- ============================================================ -->
    <!-- VIEW 3: DISCUSSÕES X -->
    <!-- ============================================================ -->
    <template v-else-if="currentView === 'discussoes'">
      <FilterBar
        :selected-class="selectedClass"
        @update:selected-class="selectedClass = $event"
        @refresh="loadReport"
      />
      <section class="px-4 py-8 max-w-6xl mx-auto">
        <h2 class="text-2xl md:text-3xl font-bold mb-2">𝕏 Discussões no X</h2>
        <p class="text-sm text-gray-500 mb-4">
          {{ filteredDiscussoes.length }} de {{ report?.discussoes_x?.length || 0 }} discussões das últimas 24h{{ selectedClass !== 'all' ? ' (Classe ' + selectedClass + ')' : '' }}
        </p>

        <!-- Banner: Grok indisponível, exibindo cache do dia anterior -->
        <div v-if="discussoesCacheBanner" class="mb-4 p-3 rounded-lg bg-amber-50 border border-amber-300 flex items-start gap-3">
          <span class="text-2xl flex-shrink-0">📦</span>
          <div class="text-sm text-amber-900 flex-1">
            <p class="font-semibold mb-0.5">Grok (X) indisponível hoje</p>
            <p class="text-xs leading-relaxed">
              Estas discussões são do relatório de <strong>{{ formatBannerDate(discussoesCacheBanner) }}</strong> — usadas como fallback para você não ficar sem essa fonte. xAI estava com sobrecarga (HTTP 429) no horário de coleta. Próxima coleta amanhã às 3:00 UTC.
            </p>
          </div>
        </div>

        <div v-if="report?.discussoes_x?.length" class="flex gap-2 flex-wrap mb-6">
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

        <div v-if="filteredDiscussoes.length" class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <XDiscussionCard
            v-for="discussion in filteredDiscussoes"
            :key="discussion.id"
            :discussion="discussion"
            @click="selectedDiscussion = discussion"
          />
        </div>
        <p v-else-if="!report" class="text-center text-gray-500 py-12">
          Carregando relatório...
        </p>
        <p v-else-if="!report.discussoes_x?.length" class="text-center text-gray-500 py-12">
          📭 Sem discussões neste relatório.
        </p>
        <p v-else class="text-center text-gray-500 py-8">
          Nenhuma discussão com este filtro.
        </p>
      </section>
    </template>


    <!-- ============================================================ -->
    <!-- VIEW 2: PULSO DO DIA -->
    <!-- ============================================================ -->
    <template v-else-if="currentView === 'pulso'">
      <section class="px-4 py-8 max-w-6xl mx-auto">
        <div class="mb-6">
          <h2 class="text-2xl md:text-3xl font-bold mb-2">🌍 Pulso do Dia</h2>
          <p class="text-sm text-gray-600 mb-1">
            <strong>O que fez diferença hoje na cardiologia.</strong> Síntese multi-fonte de 5-10 destaques com cruzamento de artigos, podcasts, vídeos e discussões da comunidade.
          </p>
          <p v-if="report?.pulso?.length" class="text-xs text-gray-500">
            {{ report.pulso.length }} destaque{{ report.pulso.length > 1 ? 's' : '' }} · Leitura ~{{ Math.ceil((report.pulso.length || 0) * 1.5) }} min
          </p>
        </div>

        <!-- Pulso cards -->
        <div v-if="report?.pulso?.length" class="space-y-4">
          <PulsoCard
            v-for="item in report.pulso"
            :key="item.id"
            :item="item"
            :report="report"
            @navigate-to-date="navigateToHistoricalReport"
          />
        </div>

        <!-- Empty / loading state -->
        <div v-else-if="!report" class="text-center py-12 text-gray-500">
          Carregando relatório...
        </div>
        <div v-else class="text-center py-12 text-gray-500">
          <p class="text-lg mb-2">📭 Pulso ainda não gerado para este dia</p>
          <p class="text-sm">A síntese multi-fonte aparece a partir do próximo run automático (3 UTC = meia-noite Brasília).</p>
        </div>
      </section>
    </template>


    <!-- ============================================================ -->
    <!-- VIEW 3: SUBSTACKS -->
    <!-- ============================================================ -->
    <template v-else-if="currentView === 'substacks'">
      <section class="px-4 py-8 max-w-6xl mx-auto">
        <div class="mb-6">
          <h2 class="text-2xl md:text-3xl font-bold mb-2">📝 Substacks de Cardiologia</h2>
          <p class="text-sm text-gray-600 mb-1">
            <strong>Análise crítica e curadoria especializada.</strong> Posts recentes (últimos 7 dias) de 12 newsletters lideradas por cardiologistas — voz da comunidade fora dos journals tradicionais.
          </p>
          <p v-if="report?.substacks?.length" class="text-xs text-gray-500">
            {{ report.substacks.length }} post{{ report.substacks.length > 1 ? 's' : '' }} · {{ uniqueSubstackPubs }} fonte{{ uniqueSubstackPubs > 1 ? 's' : '' }}
          </p>
        </div>

        <!-- Filter by publication -->
        <div v-if="substackPubFilters.length > 1" class="flex gap-2 flex-wrap mb-6">
          <button
            v-for="f in substackPubFilters"
            :key="f.key"
            @click="selectedSubstackPub = f.key"
            :class="['px-3 py-1.5 rounded-full text-xs font-medium transition-all flex items-center gap-1.5',
                     selectedSubstackPub === f.key
                       ? 'bg-purple-700 text-white shadow-sm'
                       : 'bg-gray-100 text-gray-700 hover:bg-gray-200']"
          >
            <span>{{ f.label }}</span>
            <span class="opacity-70">({{ f.count }})</span>
          </button>
        </div>

        <!-- Cards grid -->
        <div v-if="filteredSubstacks.length" class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <SubstackCard
            v-for="post in filteredSubstacks"
            :key="post.id || post.url"
            :post="post"
          />
        </div>

        <!-- Empty / loading -->
        <div v-else-if="!report" class="text-center py-12 text-gray-500">
          Carregando relatório...
        </div>
        <div v-else-if="!report.substacks?.length" class="text-center py-12 text-gray-500">
          <p class="text-lg mb-2">📭 Sem posts de Substacks neste relatório</p>
          <p class="text-sm">Newsletters publicam 1-3x por semana. Próxima coleta: meia-noite Brasília.</p>
        </div>
        <div v-else class="text-center py-12 text-gray-500">
          Nenhum post encontrado para esta fonte.
        </div>
      </section>
    </template>


    <!-- ============================================================ -->
    <!-- VIEW 4: VÍDEOS -->
    <!-- ============================================================ -->
    <template v-else-if="currentView === 'videos'">
      <section class="px-4 py-8 max-w-6xl mx-auto">
        <div class="mb-6">
          <h2 class="text-2xl md:text-3xl font-bold mb-2">📺 Vídeos de Cardiologia</h2>
          <p class="text-sm text-gray-600 mb-1">
            <strong>Vídeos enriquecidos com tema, bullets e resumo em português.</strong> Últimas 72h de canais de sociedades, journals e hospitais — Gemini gera o resumo clínico, mas o vídeo continua original no canal.
          </p>
          <p v-if="report?.videos_youtube?.length" class="text-xs text-gray-500">
            {{ report.videos_youtube.length }} vídeo{{ report.videos_youtube.length > 1 ? 's' : '' }} ·
            {{ enrichedVideoCount }} enriquecido{{ enrichedVideoCount !== 1 ? 's' : '' }} pelo Gemini
          </p>
        </div>

        <!-- Tier filter -->
        <div v-if="report?.videos_youtube?.length" class="flex gap-2 flex-wrap mb-6">
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

        <!-- Cards grid -->
        <div v-if="filteredVideos.length" class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <VideoCardEnriched
            v-for="video in filteredVideos"
            :key="video.video_url"
            :video="video"
          />
        </div>

        <!-- Empty / loading -->
        <div v-else-if="!report" class="text-center py-12 text-gray-500">
          Carregando relatório...
        </div>
        <div v-else-if="!report.videos_youtube?.length" class="text-center py-12 text-gray-500">
          <p class="text-lg mb-2">📭 Sem vídeos neste relatório</p>
          <p class="text-sm">Próxima coleta: meia-noite Brasília.</p>
        </div>
        <div v-else class="text-center py-12 text-gray-500">
          Nenhum vídeo encontrado para este filtro.
        </div>
      </section>
    </template>


    <!-- ============================================================ -->
    <!-- VIEW: PODCASTS -->
    <!-- ============================================================ -->
    <template v-else-if="currentView === 'podcasts'">
      <FilterBar
        :selected-class="selectedClass"
        @update:selected-class="selectedClass = $event"
        @refresh="loadReport"
      />
      <section class="px-4 py-8 max-w-6xl mx-auto">
        <div class="mb-6">
          <h2 class="text-2xl md:text-3xl font-bold mb-2">🎙️ Podcasts de Cardiologia</h2>
          <p class="text-sm text-gray-600 mb-1">
            Episódios recentes com resumo baseado nos <strong>show notes oficiais</strong> de cada podcast. Chip de fidelidade indica quão completos eram os show notes — em alguns casos só o título está disponível.
          </p>
          <p v-if="report?.podcasts?.length" class="text-xs text-gray-500">
            {{ filteredPodcasts.length }} de {{ report.podcasts.length }} episódio{{ report.podcasts.length > 1 ? 's' : '' }}{{ selectedClass !== 'all' ? ' (Classe ' + selectedClass + ')' : '' }} ·
            {{ richPodcastsCount }} com show notes completos
          </p>
        </div>

        <div v-if="filteredPodcasts.length" class="space-y-3">
          <PodcastCard
            v-for="podcast in filteredPodcasts"
            :key="podcast.id"
            :podcast="podcast"
            @click="openPodcast(podcast)"
          />
        </div>
        <p v-else-if="!report" class="text-center text-gray-500 py-12">
          Carregando relatório...
        </p>
        <p v-else-if="!report.podcasts?.length" class="text-center text-gray-500 py-12">
          📭 Sem podcasts neste relatório.
        </p>
        <p v-else class="text-center text-gray-500 py-8">
          Nenhum podcast Classe {{ selectedClass }} hoje.
        </p>
      </section>
    </template>


    <!-- ============================================================ -->
    <!-- VIEW 5: IDEIAS DO DIA -->
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


    <!-- X Discussion Detail Modal (only modal left — cards have all article info) -->
    <XDiscussionDetail
      v-if="selectedDiscussion"
      :discussion="selectedDiscussion"
      @close="selectedDiscussion = null"
    />

    <!-- Floating "back to top" button — visible after 400px scroll -->
    <BackToTopButton />

    <!-- Reader modal (singleton) — mobile/tablet only; opens via useReader().open() -->
    <ReaderModal />

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import HeaderStats from './components/HeaderStats.vue'
import FilterBar from './components/FilterBar.vue'
import ArticleCard from './components/ArticleCard.vue'
import NoticiaCard from './components/NoticiaCard.vue'
import PodcastCard from './components/PodcastCard.vue'
import XDiscussionCard from './components/XDiscussionCard.vue'
import XDiscussionDetail from './components/XDiscussionDetail.vue'
import BackToTopButton from './components/BackToTopButton.vue'
import ReaderModal from './components/ReaderModal.vue'
import PostIdeaCard from './components/PostIdeaCard.vue'
import PulsoCard from './components/PulsoCard.vue'
import SubstackCard from './components/SubstackCard.vue'
import VideoCardEnriched from './components/VideoCardEnriched.vue'
import CongressBanner from './components/CongressBanner.vue'
import { fetchLatestReport, fetchIndex, fetchReportByDate } from './utils/api'
import { openInBrowser } from './utils/openLink'

const report = ref(null)
const selectedDiscussion = ref(null)
const selectedClass = ref('all')
const loading = ref(false)
const selectedXCategoria = ref('all')
const selectedVideoTier = ref(-1)  // -1 = all
const currentView = ref('artigos')  // 'artigos'|'noticias'|'discussoes'|'pulso'|'substacks'|'videos'|'podcasts'|'ideas'
const selectedIdeaType = ref('all')
const selectedSubstackPub = ref('all')
const availableDates = ref([])
const currentDateIndex = ref(0)

// Click on an article card opens the source URL directly in a new tab.
// Modal was removed — card already shows resumo + conclusao + pontos_chave +
// impacto_clinico (everything that was in the modal and more).
//
// openInBrowser escapes the iOS SFSafariViewController in-app sheet by routing
// HTTPS through Chrome's googlechromes:// scheme on iOS devices. Other platforms
// keep standard window.open behavior.
function openArticle(article) {
  const url = article?.links?.url
    || (article?.links?.doi ? `https://doi.org/${article.links.doi}` : null)
    || (article?.links?.pubmed ? `https://pubmed.ncbi.nlm.nih.gov/${article.links.pubmed}/` : null)
  if (url) openInBrowser(url)
}

async function navigateDate(direction) {
  const newIndex = currentDateIndex.value + direction
  if (newIndex < 0 || newIndex >= availableDates.value.length) return
  currentDateIndex.value = newIndex
  const date = availableDates.value[newIndex]
  report.value = await fetchReportByDate(date)
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

// Jump directly to a specific historical date — triggered when user clicks
// on a "📅 Histórico relacionado" pulso reference. For non-pulso refs (artigo/
// noticia/substack), PulsoCard renders as <a href> directly — no JS needed.
async function navigateToHistoricalReport(targetDate) {
  if (!targetDate || typeof targetDate !== 'string') return
  const idx = availableDates.value.indexOf(targetDate)
  if (idx < 0) {
    console.warn(`Pulso historical reference points to ${targetDate} but report not in index`)
    return
  }
  currentDateIndex.value = idx
  loading.value = true
  try {
    report.value = await fetchReportByDate(targetDate)
    currentView.value = 'pulso'  // surface the historical pulso aba directly
  } finally {
    loading.value = false
  }
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

// Filtered news — applies the class filter (A/B/C) when user picks one.
// Without this, clicking 'Classe A' filtered artigos but Notícias kept showing
// all items, making the filter feel broken.
const filteredNoticias = computed(() => {
  const list = report.value?.noticias || []
  if (selectedClass.value === 'all') return list
  return list.filter(n => n.classe === selectedClass.value)
})

// Filtered podcasts — same class filter pattern
const filteredPodcasts = computed(() => {
  const list = report.value?.podcasts || []
  if (selectedClass.value === 'all') return list
  return list.filter(p => p.classe === selectedClass.value)
})

// How many podcasts have rich show notes (used in the header subtitle)
const richPodcastsCount = computed(() => {
  return (report.value?.podcasts || []).filter(p => p.show_notes_quality === 'rich').length
})

// Open podcast — prefer episode_url over audio_url (page tem mais contexto)
function openPodcast(podcast) {
  const url = podcast?.links?.episode_url || podcast?.links?.audio_url
  if (url) openInBrowser(url)
}

// Discussions get both filters: class (A/B/C) AND categoria (especialista/revista/etc).
const filteredDiscussoes = computed(() => {
  let list = report.value?.discussoes_x || []
  if (selectedClass.value !== 'all') {
    list = list.filter(d => d.classe === selectedClass.value)
  }
  if (selectedXCategoria.value !== 'all') {
    list = list.filter(d => d.categoria === selectedXCategoria.value)
  }
  return list
})

// Cache fallback detection — when Grok hits rate limit / outage, backend
// reuses yesterday's discussoes_x and tags each item with `_cache_fallback: true`
// plus `_cache_source_date` ('YYYY-MM-DD'). Banner only shows when ALL items
// are cached (partial cache shouldn't happen but defensive: if mixed, dont
// confuse users with banner). Returns the source date string or null.
const discussoesCacheBanner = computed(() => {
  const list = report.value?.discussoes_x || []
  if (!list.length) return null
  const allCached = list.every(d => d._cache_fallback === true)
  if (!allCached) return null
  const dates = list.map(d => d._cache_source_date).filter(Boolean)
  if (!dates.length) return null
  return dates[0]
})

function formatBannerDate(dateStr) {
  if (!dateStr || typeof dateStr !== 'string') return dateStr
  const m = dateStr.match(/^(\d{4})-(\d{2})-(\d{2})/)
  return m ? `${m[3]}/${m[2]}/${m[1]}` : dateStr
}

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

const enrichedVideoCount = computed(() => {
  const list = report.value?.videos_youtube || []
  return list.filter(v => v._enriched).length
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

// Substack filters: by publication name. Always show "Todas" first.
const substackPubFilters = computed(() => {
  const posts = report.value?.substacks || []
  if (!posts.length) return []
  const counts = new Map()
  for (const p of posts) {
    const pub = p.publicacao || '(sem nome)'
    counts.set(pub, (counts.get(pub) || 0) + 1)
  }
  const filters = [{ key: 'all', label: 'Todas', count: posts.length }]
  for (const [pub, count] of [...counts.entries()].sort((a, b) => b[1] - a[1])) {
    filters.push({ key: pub, label: pub, count })
  }
  return filters
})

const filteredSubstacks = computed(() => {
  const posts = report.value?.substacks || []
  if (selectedSubstackPub.value === 'all') return posts
  return posts.filter(p => p.publicacao === selectedSubstackPub.value)
})

const uniqueSubstackPubs = computed(() => {
  const posts = report.value?.substacks || []
  return new Set(posts.map(p => p.publicacao)).size
})

const filteredArticles = computed(() => {
  if (!report.value?.artigos) return []
  if (selectedClass.value === 'all') return report.value.artigos
  return report.value.artigos.filter(a => a.classe === selectedClass.value)
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
