<!-- frontend/src/App.vue -->
<template>
  <div class="min-h-screen bg-white">
    <!-- Sticky search bar (acima de tudo; carrega histórico lazy no focus) -->
    <SearchBar />

    <!-- Quando há busca ativa, substitui todo o conteúdo por resultados -->
    <SearchResults v-if="searchActive" />

    <template v-else>
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

    <!-- Áudio briefing: copia o dia estruturado para colar no NotebookLM -->
    <div v-if="!searchActive && report" class="bg-indigo-50 border-b border-indigo-100">
      <div class="max-w-6xl mx-auto px-4 py-2 flex items-center justify-between gap-2 flex-wrap">
        <span class="text-xs text-indigo-700">
          🎧 Ouvir o dia: copie o briefing e cole no NotebookLM ("criar podcast")
        </span>
        <button
          @click="onCopyBriefing"
          class="text-xs px-3 py-1.5 rounded-full bg-indigo-600 text-white hover:bg-indigo-700 font-medium transition-colors flex-shrink-0"
        >
          {{ briefingCopied ? '✓ Copiado!' : '📋 Copiar briefing' }}
        </button>
      </div>
    </div>

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
        <!-- Acumulador mensal de revisões/diretrizes (estilo amber = selo de revisão) -->
        <button
          @click="openRevisoesMes"
          :class="['px-2.5 md:px-5 py-1.5 md:py-3 rounded-lg text-sm md:text-lg font-semibold transition-all flex items-center gap-1.5 md:gap-2.5',
                   currentView === 'revisoes'
                     ? 'bg-amber-500 text-white shadow-md'
                     : 'bg-white text-amber-700 hover:bg-amber-50 border border-amber-300']"
        >
          📖 Revisões do Mês
          <span v-if="reviewsCounts.total"
                :class="['px-1.5 md:px-2 py-0.5 rounded-full text-xs md:text-sm font-bold',
                         currentView === 'revisoes' ? 'bg-white text-amber-700' : 'bg-amber-100 text-amber-800']">
            {{ reviewsCounts.total }}
          </span>
        </button>
        <!-- Imagens do X (protótipo) -->
        <button
          @click="openXImages"
          :class="['px-2.5 md:px-5 py-1.5 md:py-3 rounded-lg text-sm md:text-lg font-semibold transition-all flex items-center gap-1.5 md:gap-2.5',
                   currentView === 'imagens'
                     ? 'bg-teal-600 text-white shadow-md'
                     : 'bg-white text-teal-700 hover:bg-teal-50 border border-teal-300']"
        >
          🖼️ Imagens
          <span v-if="xImagesData?.total"
                :class="['px-1.5 md:px-2 py-0.5 rounded-full text-xs md:text-sm font-bold',
                         currentView === 'imagens' ? 'bg-white text-teal-700' : 'bg-teal-100 text-teal-800']">
            {{ xImagesData.total }}
          </span>
        </button>
        <!-- Biblioteca de estudos (PDFs processados) -->
        <button
          @click="openStudies"
          :class="['px-2.5 md:px-5 py-1.5 md:py-3 rounded-lg text-sm md:text-lg font-semibold transition-all flex items-center gap-1.5 md:gap-2.5',
                   currentView === 'estudo'
                     ? 'bg-violet-600 text-white shadow-md'
                     : 'bg-white text-violet-700 hover:bg-violet-50 border border-violet-300']"
        >
          📚 Estudo
          <span v-if="studiesItems.length"
                :class="['px-1.5 md:px-2 py-0.5 rounded-full text-xs md:text-sm font-bold',
                         currentView === 'estudo' ? 'bg-white text-violet-700' : 'bg-violet-100 text-violet-800']">
            {{ studiesItems.length }}
          </span>
        </button>

        <!-- Senha de marcação "lido" — fica salva só neste aparelho -->
        <button
          @click="pedirSenhaMarcas"
          :title="hasMarcasToken() ? 'Senha de marcação definida neste aparelho' : 'Definir senha de marcação (para marcar itens como lidos)'"
          class="ml-auto self-center text-sm px-2.5 py-1.5 rounded-lg border border-gray-300 text-gray-500 hover:border-emerald-300 transition-colors flex-shrink-0"
        >
          {{ hasMarcasToken() ? '🔑 ✓' : '🔑' }}
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
        <div class="flex items-center justify-between gap-2 mb-3 flex-wrap">
          <p class="text-sm text-gray-500">
            {{ filteredArticles.length }} de {{ report?.artigos?.length || 0 }} artigos{{ selectedClass !== 'all' ? ' (Classe ' + selectedClass + ')' : '' }}{{ selectedTema !== 'all' ? ' · ' + selectedTema : '' }}
          </p>
          <button
            @click="toggleArticlesExpanded"
            class="text-xs px-3 py-1.5 rounded-full border border-gray-300 bg-white text-gray-600 hover:bg-gray-50 font-medium transition-colors flex-shrink-0"
          >
            {{ articlesExpanded ? '📖 Completo' : '📑 Compacto' }}
          </button>
        </div>

        <!-- Filtro por tema (patologia) -->
        <div v-if="temasDisponiveis.length" class="flex flex-wrap gap-1.5 mb-6">
          <button
            @click="selectedTema = 'all'"
            :class="['text-xs px-2.5 py-1 rounded-full border transition-colors',
                     selectedTema === 'all'
                       ? 'bg-teal-600 text-white border-teal-600'
                       : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50']"
          >Todos</button>
          <button
            v-for="t in temasDisponiveis"
            :key="t.tema"
            @click="selectedTema = (selectedTema === t.tema ? 'all' : t.tema)"
            :class="['text-xs px-2.5 py-1 rounded-full border transition-colors',
                     selectedTema === t.tema
                       ? 'bg-teal-600 text-white border-teal-600'
                       : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50']"
          >{{ t.tema }} <span class="opacity-70">{{ t.count }}</span></button>
        </div>

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
                :expanded-default="articlesExpanded"
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

    <!-- ============================================================ -->
    <!-- VIEW: REVISÕES E DIRETRIZES DO MÊS (acumulador) -->
    <!-- ============================================================ -->
    <template v-else-if="currentView === 'revisoes'">
      <section class="px-4 py-8 max-w-4xl mx-auto">
        <div class="mb-4">
          <h2 class="text-2xl md:text-3xl font-bold mb-2">📖 Revisões e Diretrizes</h2>
          <!-- Navegação de mês: abre no atual, ◄ volta para meses anteriores -->
          <div class="flex items-center gap-2 mb-2">
            <button
              @click="reviewsOlder" :disabled="!reviewsCanOlder"
              class="w-9 h-9 flex items-center justify-center rounded-lg border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed"
              aria-label="Mês anterior"
            >◄</button>
            <span class="font-semibold text-gray-800 text-center min-w-[11rem]">{{ reviewsMonthLabel }}</span>
            <button
              @click="reviewsNewer" :disabled="!reviewsCanNewer"
              class="w-9 h-9 flex items-center justify-center rounded-lg border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed"
              aria-label="Mês seguinte"
            >►</button>
          </div>
          <p class="text-sm text-gray-600">
            Tudo que saiu no mês para baixar e ler na íntegra. Abre no mês atual;
            use ◄ ► para meses anteriores. O histórico se acumula — nada é apagado.
          </p>
          <p v-if="reviewsCounts.total" class="text-sm text-gray-500 mt-1">
            {{ reviewsCounts.total }} no mês · {{ reviewsCounts.revisoes }} revisões · {{ reviewsCounts.diretrizes }} diretrizes
          </p>
        </div>

        <div v-if="reviewsLoading" class="text-center text-gray-500 py-10">
          Carregando revisões do mês…
        </div>
        <div v-else-if="reviewsLoadError" class="text-center text-red-600 py-10">
          Falha ao carregar: {{ reviewsLoadError }}
        </div>
        <div v-else-if="reviewsItems.length === 0" class="text-center text-gray-500 py-10">
          <p class="text-lg mb-1">Nenhuma revisão ou diretriz neste mês ainda.</p>
          <p class="text-sm">Elas vão se acumulando aqui conforme saem nos relatórios diários.</p>
        </div>

        <template v-else>
          <!-- Filtro por tema -->
          <div v-if="reviewsTemas.length > 1" class="flex flex-wrap gap-1.5 mb-5">
            <button
              @click="reviewsTemaFiltro = 'all'"
              :class="['text-xs px-2.5 py-1 rounded-full border transition-colors',
                       reviewsTemaFiltro === 'all' ? 'bg-amber-500 text-white border-amber-500'
                       : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50']"
            >Todos</button>
            <button
              v-for="t in reviewsTemas"
              :key="t.tema"
              @click="reviewsTemaFiltro = (reviewsTemaFiltro === t.tema ? 'all' : t.tema)"
              :class="['text-xs px-2.5 py-1 rounded-full border transition-colors',
                       reviewsTemaFiltro === t.tema ? 'bg-amber-500 text-white border-amber-500'
                       : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50']"
            >{{ t.tema }} <span class="opacity-70">{{ t.count }}</span></button>
          </div>

          <ul class="space-y-2">
            <li
              v-for="(it, i) in reviewsFiltrados"
              :key="i"
              class="border border-gray-200 rounded-lg p-3 bg-white hover:border-amber-300 transition-colors"
            >
              <div class="flex items-start gap-2 mb-1 flex-wrap">
                <span :class="['inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide flex-shrink-0',
                               it.tipo === 'diretriz' ? 'bg-blue-100 text-blue-800 border border-blue-300'
                               : 'bg-amber-100 text-amber-800 border border-amber-300']">
                  {{ it.tipo === 'diretriz' ? '📋 Diretriz' : '📖 Revisão' }}
                </span>
                <span v-if="it.article.tema_principal"
                      class="text-[10px] px-2 py-0.5 rounded-full bg-teal-50 text-teal-700 border border-teal-200 font-medium flex-shrink-0">
                  {{ it.article.tema_principal }}
                </span>
                <span class="text-[11px] text-gray-400 flex-shrink-0">{{ formatRevDate(it.date) }}</span>
              </div>
              <h3 class="font-semibold text-sm text-gray-900 leading-snug break-words">
                {{ it.article.titulo_pt || it.article.titulo }}
              </h3>
              <p v-if="it.article.titulo_pt && it.article.titulo && it.article.titulo_pt !== it.article.titulo"
                 class="text-[11px] text-gray-400 italic break-words">{{ it.article.titulo }}</p>
              <div class="flex items-center gap-3 mt-2">
                <a
                  v-if="revUrl(it.article)"
                  :href="revUrl(it.article)"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="text-xs text-blue-600 hover:text-blue-800 font-medium"
                  @click.stop="handleExternalLinkClick($event, revUrl(it.article))"
                >🔗 Abrir / baixar</a>
                <span class="text-[11px] text-gray-400">{{ it.article.publicacao }}</span>
              </div>
            </li>
          </ul>
        </template>
      </section>
    </template>

    <!-- ============================================================ -->
    <!-- VIEW: IMAGENS DO X (protótipo) -->
    <!-- ============================================================ -->
    <template v-else-if="currentView === 'imagens'">
      <section class="px-4 py-8 max-w-6xl mx-auto">
        <div class="mb-4">
          <h2 class="text-2xl md:text-3xl font-bold mb-1">🖼️ Imagens do X — figuras de trabalhos</h2>
          <p class="text-sm text-gray-600">
            Gráficos, tabelas, graphical abstracts e slides de congresso colhidos do X.
            Visualize, abra o post original ou salve a imagem.
          </p>
          <p v-if="xImagesData?.total" class="text-sm text-gray-500 mt-1">
            {{ xImagesData.total }} imagens · {{ formatXImgStats(xImagesData.por_tipo) }}
          </p>
        </div>

        <!-- Navegação por dia (histórico) -->
        <div class="flex items-center justify-center gap-3 mb-5">
          <button
            class="w-9 h-9 rounded-lg bg-teal-50 text-teal-700 disabled:opacity-30 disabled:cursor-not-allowed"
            :disabled="!xImagesCanPrev" @click="xImagesPrevDay" aria-label="Dia anterior">◄</button>
          <span class="font-semibold text-gray-700 min-w-[12rem] text-center">{{ xImagesDateLabel || '—' }}</span>
          <button
            class="w-9 h-9 rounded-lg bg-teal-50 text-teal-700 disabled:opacity-30 disabled:cursor-not-allowed"
            :disabled="!xImagesCanNext" @click="xImagesNextDay" aria-label="Dia seguinte">►</button>
        </div>

        <div v-if="xImagesLoading" class="text-center text-gray-500 py-10">Carregando imagens…</div>
        <div v-else-if="xImagesLoadError" class="text-center text-gray-500 py-10">
          <p class="text-lg mb-1">Não consegui carregar as imagens deste dia.</p>
          <p class="text-sm">Tente outro dia nas setas acima.</p>
        </div>
        <div v-else-if="!xImagesData?.imagens?.length" class="text-center text-gray-500 py-10">
          Nenhuma imagem neste dia.
        </div>

        <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <div
            v-for="(im, i) in xImagesData.imagens"
            :key="i"
            class="border border-gray-200 rounded-lg overflow-hidden bg-white flex flex-col"
          >
            <!-- Imagem "nua" (sem wrapper de link): toque abre o lightbox; long-press
                 do iOS oferece "Adicionar às Fotos". Os dois gestos não conflitam. -->
            <img :src="im.image_url" :alt="im.descricao" loading="lazy" referrerpolicy="no-referrer"
                 @error="onXImgError"
                 @click="lightboxImage = im"
                 class="w-full h-48 object-contain bg-gray-50 cursor-zoom-in" />
            <div class="p-3 flex-1 flex flex-col gap-1.5">
              <div class="flex items-center gap-1.5 flex-wrap">
                <span class="text-[10px] px-1.5 py-0.5 rounded bg-teal-100 text-teal-800 font-bold uppercase">{{ im.tipo }}</span>
                <span v-if="im.assunto" class="text-[10px] px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-600">{{ im.assunto }}</span>
                <span class="text-[11px] text-gray-400">{{ im.fonte }}</span>
              </div>
              <p class="text-xs text-gray-700 leading-snug break-words flex-1">{{ im.descricao }}</p>
              <p class="text-[10px] text-gray-400">📲 Segure a imagem → "Adicionar às Fotos"</p>
              <div class="flex items-center gap-3 pt-1">
                <a v-if="im.post_url" :href="im.post_url" target="_blank" rel="noopener noreferrer"
                   @click.stop="handleExternalLinkClick($event, im.post_url)"
                   class="text-xs text-blue-600 hover:text-blue-800 font-medium">𝕏 Ver post</a>
                <a :href="im.image_url" target="_blank" rel="noopener noreferrer"
                   @click.stop="handleExternalLinkClick($event, im.image_url)"
                   class="text-xs text-teal-700 hover:text-teal-900 font-medium">⬇ Abrir imagem</a>
              </div>
            </div>
          </div>
        </div>
      </section>
    </template>


    <!-- ============================================================ -->
    <!-- VIEW: ESTUDO (biblioteca de PDFs processados por mes) -->
    <!-- ============================================================ -->
    <template v-else-if="currentView === 'estudo'">
      <section class="px-4 py-8 max-w-4xl mx-auto">
        <!-- Leitor aberto -->
        <StudyReader v-if="selectedStudySlug" :slug="selectedStudySlug" :titulo="selectedStudyTitulo" @close="selectedStudySlug = null" />

        <!-- Biblioteca do mes -->
        <div v-else>
          <div class="mb-4">
            <h2 class="text-2xl md:text-3xl font-bold mb-2">📚 Estudos do Mês</h2>
            <!-- Navegacao de mes: abre no atual, ◄ volta para meses anteriores -->
            <div class="flex items-center gap-2 mb-2">
              <button
                @click="studiesOlderMonth" :disabled="!studiesCanOlder"
                class="w-9 h-9 flex items-center justify-center rounded-lg border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed"
                aria-label="Mês anterior"
              >◄</button>
              <span class="font-semibold text-gray-800 text-center min-w-[11rem]">{{ studiesMonthLabel }}</span>
              <button
                @click="studiesNewerMonth" :disabled="!studiesCanNewer"
                class="w-9 h-9 flex items-center justify-center rounded-lg border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed"
                aria-label="Mês seguinte"
              >►</button>
            </div>
            <p class="text-sm text-gray-600">
              PDFs processados e comprimidos para leitura rápida. Use ◄ ► para navegar entre meses.
            </p>
          </div>

          <div v-if="studiesLoading" class="text-center text-gray-500 py-10">
            Carregando estudos do mês…
          </div>
          <div v-else-if="studiesLoadError" class="text-center text-red-600 py-10">
            Falha ao carregar: {{ studiesLoadError }}
          </div>
          <div v-else-if="studiesItems.length === 0" class="text-center text-gray-500 py-10">
            <p class="text-lg mb-1">Nenhum estudo neste mês ainda.</p>
            <p class="text-sm">
              Solte um PDF em <code class="bg-gray-100 px-1 rounded">study-inbox/</code> e rode
              <code class="bg-gray-100 px-1 rounded">processar.bat</code>.
            </p>
          </div>

          <ul v-else class="space-y-2">
            <li
              v-for="it in studiesItems"
              :key="it.slug"
              class="border border-gray-200 rounded-lg bg-white hover:border-violet-300 transition-colors"
            >
              <button
                class="w-full text-left p-3 flex flex-col gap-1"
                @click="selectedStudySlug = it.slug"
              >
                <span class="font-semibold text-sm text-gray-900 leading-snug break-words">{{ it.titulo }}</span>
                <span class="text-[11px] text-gray-500">{{ it.fonte }} · {{ it.tipo }} · {{ it.data }}</span>
              </button>
            </li>
          </ul>
        </div>
      </section>
    </template>


    <!-- Lightbox de imagem do X — abre ao tocar na figura -->
    <Teleport to="body">
      <div
        v-if="lightboxImage"
        class="fixed inset-0 z-[9999] bg-black/90 flex flex-col items-center justify-center p-4"
        @click.self="lightboxImage = null"
      >
        <button
          @click="lightboxImage = null"
          class="absolute top-3 right-3 text-white/80 hover:text-white text-2xl w-11 h-11 flex items-center justify-center rounded-full bg-white/10"
          aria-label="Fechar"
        >✕</button>
        <!-- Imagem grande "nua" — long-press salva nas Fotos -->
        <img
          :src="lightboxImage.image_url"
          :alt="lightboxImage.descricao"
          referrerpolicy="no-referrer"
          class="max-w-full max-h-[80vh] object-contain rounded shadow-2xl"
        />
        <div class="mt-3 max-w-2xl text-center px-2">
          <p class="text-white/90 text-sm leading-snug">{{ lightboxImage.descricao }}</p>
          <p class="text-white/50 text-xs mt-1">
            {{ lightboxImage.fonte }} · 📲 segure a imagem para "Adicionar às Fotos"
          </p>
          <div class="flex items-center justify-center gap-5 mt-3">
            <a v-if="lightboxImage.post_url" :href="lightboxImage.post_url" target="_blank" rel="noopener noreferrer"
               @click.stop="handleExternalLinkClick($event, lightboxImage.post_url)"
               class="text-blue-300 hover:text-blue-200 text-sm font-medium">𝕏 Ver post</a>
            <a :href="lightboxImage.image_url" target="_blank" rel="noopener noreferrer"
               @click.stop="handleExternalLinkClick($event, lightboxImage.image_url)"
               class="text-teal-300 hover:text-teal-200 text-sm font-medium">⬇ Abrir imagem</a>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- X Discussion Detail Modal (only modal left — cards have all article info) -->
    <XDiscussionDetail
      v-if="selectedDiscussion"
      :discussion="selectedDiscussion"
      @close="selectedDiscussion = null"
    />
    </template>
    <!-- /v-else (modo normal, não busca) -->

    <!-- Floating "back to top" button — visible after 400px scroll -->
    <BackToTopButton />

    <!-- Reader modal (singleton) — mobile/tablet only; opens via useReader().open() -->
    <ReaderModal />

  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import HeaderStats from './components/HeaderStats.vue'
import FilterBar from './components/FilterBar.vue'
import ArticleCard from './components/ArticleCard.vue'
import NoticiaCard from './components/NoticiaCard.vue'
import PodcastCard from './components/PodcastCard.vue'
import XDiscussionCard from './components/XDiscussionCard.vue'
import XDiscussionDetail from './components/XDiscussionDetail.vue'
import BackToTopButton from './components/BackToTopButton.vue'
import ReaderModal from './components/ReaderModal.vue'
import SearchBar from './components/SearchBar.vue'
import SearchResults from './components/SearchResults.vue'
import { useSearch } from './composables/useSearch'
import { copyAudioBriefing } from './composables/useAudioBriefing'
import { useMonthlyReviews } from './composables/useMonthlyReviews'
import { useDailyXImages } from './composables/useDailyXImages'
import StudyReader from './components/StudyReader.vue'
import ReadToggle from './components/ReadToggle.vue'
import { useReadMarks } from './composables/useReadMarks'
import { useMonthlyStudies } from './composables/useMonthlyStudies'

const { isActive: searchActive } = useSearch()

// Revisões/diretrizes do mês (acumulador)
const {
  loading: reviewsLoading,
  loadError: reviewsLoadError,
  items: reviewsItems,
  monthLabelText: reviewsMonthLabel,
  temas: reviewsTemas,
  counts: reviewsCounts,
  canOlder: reviewsCanOlder,
  canNewer: reviewsCanNewer,
  olderMonth: reviewsOlderMonth,
  newerMonth: reviewsNewerMonth,
  open: openReviews,
} = useMonthlyReviews()
const reviewsTemaFiltro = ref('all')

function openRevisoesMes() {
  currentView.value = 'revisoes'
  reviewsTemaFiltro.value = 'all'
  openReviews()  // lazy — vai pro mês atual (ou o mais recente com dados)
}
async function reviewsOlder() { reviewsTemaFiltro.value = 'all'; await reviewsOlderMonth() }
async function reviewsNewer() { reviewsTemaFiltro.value = 'all'; await reviewsNewerMonth() }

const reviewsFiltrados = computed(() => {
  if (reviewsTemaFiltro.value === 'all') return reviewsItems.value
  return reviewsItems.value.filter(it => (it.article.tema_principal || 'Outros temas') === reviewsTemaFiltro.value)
})

function revUrl(a) {
  return a?.links?.url
    || (a?.links?.doi ? `https://doi.org/${a.links.doi}` : null)
    || (a?.links?.pubmed ? `https://pubmed.ncbi.nlm.nih.gov/${a.links.pubmed}/` : null)
    || null
}

// Imagens do X — navegáveis por dia (histórico)
const {
  loading: xImagesLoading,
  loadError: xImagesLoadError,
  data: xImagesData,
  selectedDate: xImagesDate,
  dateLabel: xImagesDateLabel,
  canPrev: xImagesCanPrev,
  canNext: xImagesCanNext,
  prevDay: xImagesPrevDay,
  nextDay: xImagesNextDay,
  open: openXImagesLib,
} = useDailyXImages()

function openXImages() {
  currentView.value = 'imagens'
  openXImagesLib()
}

// Estudos do mes (biblioteca de PDFs processados)
const {
  loading: studiesLoading,
  loadError: studiesLoadError,
  items: studiesItems,
  monthLabelText: studiesMonthLabel,
  canOlder: studiesCanOlder,
  canNewer: studiesCanNewer,
  olderMonth: studiesOlderMonth,
  newerMonth: studiesNewerMonth,
  open: openStudiesLib,
} = useMonthlyStudies()

const selectedStudySlug = ref(null)
const selectedStudyTitulo = computed(
  () => studiesItems.value.find((it) => it.slug === selectedStudySlug.value)?.titulo || ''
)

// Marcas "lido" sincronizadas (KV). isReadMark p/ esmaecer; senha 1x por aparelho.
const { isRead: isReadMark, setToken: setMarcasToken, hasToken: hasMarcasToken } = useReadMarks()
function pedirSenhaMarcas() {
  const t = window.prompt('Sua senha de marcação (a mesma definida na Vercel). Fica salva só neste aparelho.')
  if (t) { setMarcasToken(t); location.reload() }
}

function openStudies() {
  currentView.value = 'estudo'
  selectedStudySlug.value = null
  openStudiesLib()
}

function formatXImgStats(porTipo) {
  if (!porTipo) return ''
  return Object.entries(porTipo).map(([t, n]) => `${n} ${t}`).join(' · ')
}

function xImgDownloadUrl(im, index) {
  const ext = (im.image_url.match(/\.([a-z0-9]{3,4})(?:\?|$)/i)?.[1] || 'jpg').toLowerCase()
  const filename = `x-figura-${String(index + 1).padStart(2, '0')}.${ext}`
  const params = new URLSearchParams({ url: im.image_url, filename })
  return `/api/proxy-image?${params.toString()}`
}

function onXImgError(evt) {
  const card = evt?.target?.closest('.border')
  if (card) card.style.display = 'none'  // some media URLs expire/404 — esconde silenciosamente
}

// Lightbox de imagem (abre ao tocar na figura). Trava o scroll de fundo.
const lightboxImage = ref(null)
watch(lightboxImage, (v) => {
  if (typeof document !== 'undefined') document.body.style.overflow = v ? 'hidden' : ''
})

function formatRevDate(dateStr) {
  try {
    const [, m, d] = dateStr.split('-')
    return `${d}/${m}`
  } catch { return dateStr }
}

// Áudio briefing — copia o dia estruturado pro clipboard (cola no NotebookLM)
const briefingCopied = ref(false)
async function onCopyBriefing() {
  const { ok } = await copyAudioBriefing(report.value)
  if (ok) {
    briefingCopied.value = true
    setTimeout(() => { briefingCopied.value = false }, 2500)
  } else {
    alert('Não consegui copiar automaticamente. Tente de novo ou use outro navegador.')
  }
}
import PostIdeaCard from './components/PostIdeaCard.vue'
import PulsoCard from './components/PulsoCard.vue'
import SubstackCard from './components/SubstackCard.vue'
import VideoCardEnriched from './components/VideoCardEnriched.vue'
import CongressBanner from './components/CongressBanner.vue'
import { fetchLatestReport, fetchIndex, fetchReportByDate } from './utils/api'
import { openInBrowser, handleExternalLinkClick } from './utils/openLink'

const report = ref(null)
const selectedDiscussion = ref(null)
const selectedClass = ref('all')
const selectedTema = ref('all')

// Modo de densidade dos cards de artigo: compacto (default) vs completo.
// Persistido em localStorage para a preferência grudar entre sessões.
const articlesExpanded = ref(localStorage.getItem('articlesExpanded') === '1')
function toggleArticlesExpanded() {
  articlesExpanded.value = !articlesExpanded.value
  localStorage.setItem('articlesExpanded', articlesExpanded.value ? '1' : '0')
}
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
  selectedTema.value = 'all'  // reset tema ao trocar de dia (temas variam por dia)
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

// Temas (patologias) presentes nos artigos do dia, com contagem — para os chips
// de filtro. Respeita o filtro de classe ativo para os números baterem.
const temasDisponiveis = computed(() => {
  const base = (report.value?.artigos || []).filter(
    a => selectedClass.value === 'all' || a.classe === selectedClass.value
  )
  const counts = {}
  for (const a of base) {
    const t = a.tema_principal
    if (t) counts[t] = (counts[t] || 0) + 1
  }
  return Object.entries(counts)
    .map(([tema, count]) => ({ tema, count }))
    .sort((a, b) => b.count - a.count)
})

const filteredArticles = computed(() => {
  let list = report.value?.artigos || []
  if (selectedClass.value !== 'all') list = list.filter(a => a.classe === selectedClass.value)
  if (selectedTema.value !== 'all') list = list.filter(a => a.tema_principal === selectedTema.value)
  return list
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
  // Carrega os contadores das outras abas em segundo plano (nao trava a tela),
  // para o numero aparecer no botao sem precisar abrir cada aba.
  openReviews()
  openXImagesLib()
  openStudiesLib()
  // Esc fecha o lightbox de imagem
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && lightboxImage.value) lightboxImage.value = null
  })
})
</script>
