<!--
  ReaderModal — Singleton de "modo leitura" para cards editoriais densos.

  Renderizado UMA vez em App.vue. Reage a `useReader().currentItem`. Abrir
  outro card simplesmente troca `currentItem`; o modal não empilha.

  4 modos correspondem aos 4 tipos de card editorial do cardiology-agent:
   - "artigo"   : ArticleCard
   - "noticia"  : NoticiaCard
   - "pulso"    : PulsoCard
   - "substack" : SubstackCard
-->
<template>
  <Teleport to="body">
    <div
      v-if="currentItem"
      class="reader-overlay"
      @click.self="reader.close()"
      :style="{ '--reader-font-size': fontSize + 'px' }"
    >
      <article class="reader-panel" role="dialog" aria-modal="true" aria-label="Modo leitura">
        <!-- Header sticky: título + controles + fechar -->
        <header class="reader-header">
          <div class="reader-title-row">
            <span v-if="currentItem.emoji" class="reader-emoji">{{ currentItem.emoji }}</span>
            <h2 class="reader-title">{{ currentItem.titulo_pt || currentItem.titulo }}</h2>
          </div>
          <div class="reader-controls">
            <button
              class="reader-btn-icon"
              :disabled="!reader.canDecrease()"
              @click="reader.decFont()"
              aria-label="Diminuir fonte"
            >A−</button>
            <span class="reader-font-size">{{ fontSize }}</span>
            <button
              class="reader-btn-icon"
              :disabled="!reader.canIncrease()"
              @click="reader.incFont()"
              aria-label="Aumentar fonte"
            >A+</button>
            <button
              ref="closeBtn"
              class="reader-btn-close"
              @click="reader.close()"
              aria-label="Fechar"
            >✕</button>
          </div>
        </header>

        <!-- Body — renderização condicional por modo -->
        <div class="reader-body">
          <!-- Metadata mínima (publicação + badges) -->
          <div v-if="metadata" class="reader-meta">{{ metadata }}</div>

          <!-- =================== ARTIGO =================== -->
          <template v-if="mode === 'artigo'">
            <section v-if="currentItem.contexto_clinico" class="reader-section">
              <p class="reader-section-label">🩺 Contexto clínico</p>
              <p>{{ currentItem.contexto_clinico }}</p>
            </section>
            <section v-if="currentItem.pergunta_principal" class="reader-section">
              <p class="reader-section-label">❓ Pergunta principal</p>
              <p>{{ currentItem.pergunta_principal }}</p>
            </section>
            <section v-if="hasDesenho" class="reader-section">
              <p class="reader-section-label">🔬 Desenho do estudo</p>
              <dl class="reader-dl">
                <template v-for="(value, key) in desenhoFields" :key="key">
                  <dt>{{ desenhoLabels[key] }}</dt>
                  <dd>{{ value }}</dd>
                </template>
              </dl>
            </section>
            <section v-if="currentItem.pontos_chave?.length" class="reader-section">
              <p class="reader-section-label">📊 Pontos-chave</p>
              <ul class="reader-ul">
                <li v-for="(p, i) in currentItem.pontos_chave" :key="i">{{ p }}</li>
              </ul>
            </section>
            <section v-if="currentItem.principais_resultados" class="reader-section">
              <p class="reader-section-label">🎯 Principais resultados</p>
              <p class="reader-prose">{{ currentItem.principais_resultados }}</p>
            </section>
            <section v-if="currentItem.interpretacao_pratica" class="reader-section">
              <p class="reader-section-label">💡 Interpretação prática</p>
              <p>{{ currentItem.interpretacao_pratica }}</p>
            </section>
            <section v-if="currentItem.limitacoes?.length" class="reader-section">
              <p class="reader-section-label">⚠️ Limitações</p>
              <ul class="reader-ul">
                <li v-for="(l, i) in currentItem.limitacoes" :key="i">{{ l }}</li>
              </ul>
            </section>
            <section v-if="currentItem.conclusao_uma_frase" class="reader-section reader-verdict">
              <p class="reader-section-label">⚡ Veredito</p>
              <p>{{ currentItem.conclusao_uma_frase }}</p>
            </section>
          </template>

          <!-- =================== NOTÍCIA =================== -->
          <template v-else-if="mode === 'noticia'">
            <section v-if="currentItem.contexto" class="reader-section">
              <p class="reader-section-label">📰 Contexto</p>
              <p>{{ currentItem.contexto }}</p>
            </section>
            <section v-if="currentItem.insights" class="reader-section">
              <p class="reader-section-label">💡 Insights</p>
              <p>{{ currentItem.insights }}</p>
            </section>
            <section v-if="currentItem.por_que_importa" class="reader-section">
              <p class="reader-section-label">⚡ Por que importa</p>
              <p>{{ currentItem.por_que_importa }}</p>
            </section>
            <section v-if="currentItem.pontos_principais?.length" class="reader-section">
              <p class="reader-section-label">📌 Pontos principais</p>
              <ul class="reader-ul">
                <li v-for="(p, i) in currentItem.pontos_principais" :key="i">{{ p }}</li>
              </ul>
            </section>
            <section v-if="currentItem.falas?.length" class="reader-section">
              <p class="reader-section-label">💬 Falas</p>
              <ul class="reader-ul">
                <li v-for="(f, i) in currentItem.falas" :key="i">{{ f }}</li>
              </ul>
            </section>
            <section v-if="!currentItem.contexto && currentItem.resumo" class="reader-section">
              <p>{{ currentItem.resumo }}</p>
            </section>
          </template>

          <!-- =================== PULSO =================== -->
          <template v-else-if="mode === 'pulso'">
            <section v-if="currentItem.razao_destaque" class="reader-section">
              <p class="reader-section-label">🎯 Por que importou hoje</p>
              <p>{{ currentItem.razao_destaque }}</p>
            </section>
            <section v-if="currentItem.o_que_paper_diz" class="reader-section">
              <p class="reader-section-label">📄 O que o paper diz</p>
              <p>{{ currentItem.o_que_paper_diz }}</p>
            </section>
            <section v-if="currentItem.interpretacao_comunidade" class="reader-section">
              <p class="reader-section-label">🗣️ Interpretação da comunidade</p>
              <p>{{ currentItem.interpretacao_comunidade }}</p>
            </section>
            <section v-if="currentItem.o_que_muda" class="reader-section">
              <p class="reader-section-label">✅ O que muda</p>
              <p>{{ currentItem.o_que_muda }}</p>
            </section>
            <section v-if="currentItem.o_que_nao_muda_ainda" class="reader-section">
              <p class="reader-section-label">⏸️ O que não muda ainda</p>
              <p>{{ currentItem.o_que_nao_muda_ainda }}</p>
            </section>
          </template>

          <!-- =================== SUBSTACK =================== -->
          <template v-else-if="mode === 'substack'">
            <section v-if="currentItem.resumo" class="reader-section">
              <p class="reader-section-label">📝 Resumo</p>
              <p class="reader-prose">{{ currentItem.resumo }}</p>
            </section>
            <section v-if="currentItem.bullets?.length" class="reader-section">
              <p class="reader-section-label">📌 Pontos</p>
              <ul class="reader-ul">
                <li v-for="(b, i) in currentItem.bullets" :key="i">{{ b }}</li>
              </ul>
            </section>
            <section v-if="currentItem.quem_se_aplica" class="reader-section">
              <p class="reader-section-label">👥 Para quem</p>
              <p>{{ currentItem.quem_se_aplica }}</p>
            </section>
            <section v-if="currentItem.evidencia_chave" class="reader-section">
              <p class="reader-section-label">📊 Evidência-chave</p>
              <p>{{ currentItem.evidencia_chave }}</p>
            </section>
            <section v-if="currentItem.contraponto" class="reader-section">
              <p class="reader-section-label">⚠️ Contraponto</p>
              <p>{{ currentItem.contraponto }}</p>
            </section>
          </template>
        </div>
      </article>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useReader } from '../composables/useReader'

const reader = useReader()
const { currentItem, mode, fontSize } = reader
const closeBtn = ref(null)

const desenhoLabels = {
  tipo: 'Tipo',
  populacao: 'População',
  n: 'N',
  intervencao: 'Intervenção',
  comparador: 'Comparador',
  seguimento: 'Seguimento',
}

const desenhoFields = computed(() => {
  const d = currentItem.value?.desenho_estudo
  if (!d || typeof d !== 'object') return {}
  const out = {}
  for (const k of Object.keys(desenhoLabels)) {
    if (d[k] && typeof d[k] === 'string' && d[k].trim()) out[k] = d[k]
  }
  return out
})

const hasDesenho = computed(() => Object.keys(desenhoFields.value).length > 0)

// Linha de metadata acima do conteúdo: publicação + classe/score quando existem.
const metadata = computed(() => {
  const it = currentItem.value
  if (!it) return ''
  const parts = []
  if (it.publicacao) parts.push(it.publicacao)
  if (it.classe) parts.push(`Classe ${it.classe}`)
  if (typeof it.score === 'number') parts.push(`${it.score}/10`)
  if (it.autor && !it.publicacao) parts.push(it.autor)
  return parts.join(' · ')
})

function onKey(e) {
  if (e.key === 'Escape') reader.close()
}

watch(currentItem, async (it) => {
  if (it) {
    document.body.style.overflow = 'hidden'
    document.addEventListener('keydown', onKey)
    await nextTick()
    closeBtn.value?.focus()
  } else {
    document.body.style.overflow = ''
    document.removeEventListener('keydown', onKey)
  }
})

// Defesa em profundidade: restaura overflow se modal for desmontado de forma estranha
onBeforeUnmount(() => {
  document.body.style.overflow = ''
  document.removeEventListener('keydown', onKey)
})
</script>

<style scoped>
.reader-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  overflow-y: auto;
}

.reader-panel {
  background: #fff;
  width: 100%;
  max-width: 720px;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

@media (min-width: 640px) {
  .reader-overlay {
    padding: 2rem 1rem;
  }
  .reader-panel {
    min-height: auto;
    max-height: calc(100vh - 4rem);
    border-radius: 0.5rem;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4);
    overflow: hidden;
  }
}

.reader-header {
  position: sticky;
  top: 0;
  z-index: 2;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  background: #fff;
  border-bottom: 1px solid #e7e5e4;
  padding: 0.9rem 1rem;
}

.reader-title-row {
  display: flex;
  gap: 0.55rem;
  flex: 1;
  min-width: 0;
}

.reader-emoji {
  flex-shrink: 0;
  font-size: 1.4rem;
  line-height: 1.5;
}

.reader-title {
  font-size: 1rem;
  font-weight: 700;
  color: #292524;
  line-height: 1.4;
  margin: 0;
  flex: 1;
  /* trunca em 2 linhas no header (título completo aparece dentro do body) */
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.reader-controls {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  flex-shrink: 0;
}

.reader-font-size {
  font-size: 0.75rem;
  color: #78716c;
  min-width: 1.5rem;
  text-align: center;
  font-variant-numeric: tabular-nums;
}

.reader-btn-icon,
.reader-btn-close {
  min-width: 36px;
  min-height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #fafaf9;
  border: 1px solid #e7e5e4;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
  color: #44403c;
  font-weight: 600;
}

.reader-btn-icon:hover:not(:disabled),
.reader-btn-close:hover {
  background: #f5f5f4;
}

.reader-btn-icon:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.reader-btn-close {
  font-size: 1.1rem;
}

.reader-body {
  flex: 1;
  overflow-y: auto;
  padding: 1.25rem 1.25rem 2.5rem;
  font-family: Charter, 'Bitstream Charter', 'Sitka Text', Cambria, Georgia, serif;
  font-size: var(--reader-font-size, 22px);
  line-height: 1.8;
  color: #44403c;
}

.reader-meta {
  font-size: 0.55em;
  color: #78716c;
  margin-bottom: 1.5em;
  font-style: italic;
}

.reader-section {
  margin-bottom: 1.5em;
}

/* Labels escalam JUNTO com o body — usar em, não px */
.reader-section-label {
  font-size: 0.55em;
  text-transform: uppercase;
  letter-spacing: 0.13em;
  font-weight: 600;
  color: #92400e;
  margin: 0 0 0.45em 0;
}

.reader-section p {
  margin: 0 0 0.7em 0;
}

.reader-section p:last-child {
  margin-bottom: 0;
}

.reader-prose {
  white-space: pre-line;
}

.reader-ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.reader-ul li {
  position: relative;
  padding-left: 1.2em;
  margin-bottom: 0.5em;
}

.reader-ul li::before {
  content: '▸';
  position: absolute;
  left: 0;
  color: #a8a29e;
}

.reader-dl {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.2em 0.9em;
  margin: 0;
}

.reader-dl dt {
  font-weight: 600;
  color: #57534e;
  white-space: nowrap;
}

.reader-dl dd {
  margin: 0;
}

.reader-verdict {
  border-top: 1px solid #fde2c9;
  border-bottom: 1px solid #fde2c9;
  padding: 0.9em 0;
  background: linear-gradient(to right, #fffbeb, #fdf2f8);
  border-radius: 4px;
  padding-left: 0.9em;
  padding-right: 0.9em;
}
</style>
