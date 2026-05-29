<!--
  SearchBar — sticky no topo, busca textual em TODO o histórico.

  Carrega os JSONs do histórico de forma lazy: só ao primeiro focus do input.
  Debounce de 200ms no input pra não filtrar a cada tecla.
-->
<template>
  <div class="sticky top-0 z-40 bg-white/95 backdrop-blur border-b border-gray-200 px-3 py-2">
    <div class="max-w-4xl mx-auto flex items-center gap-2">
      <!-- ícone lupa -->
      <span class="text-gray-400 text-sm select-none" aria-hidden="true">🔍</span>

      <input
        ref="inputRef"
        type="search"
        :value="query"
        @input="onInput"
        @focus="onFocus"
        placeholder="Buscar em todo o histórico (ex: TAVR, ticagrelor, Mandrola)"
        class="flex-1 min-w-0 bg-transparent border-none outline-none text-sm placeholder-gray-400 focus:ring-0"
        aria-label="Buscar no histórico"
      />

      <!-- contador / status -->
      <span v-if="loading" class="text-xs text-gray-500 whitespace-nowrap">carregando…</span>
      <span
        v-else-if="isActive"
        class="text-xs text-gray-600 whitespace-nowrap"
        aria-live="polite"
      >
        {{ results.length }} {{ results.length === 1 ? 'resultado' : 'resultados' }}
      </span>
      <span
        v-else-if="loaded"
        class="hidden sm:inline text-[11px] text-gray-400 whitespace-nowrap"
      >
        {{ allReportsCount }} dias indexados
      </span>

      <!-- limpar -->
      <button
        v-if="query"
        @click="clear"
        class="text-gray-400 hover:text-gray-700 text-lg leading-none px-1"
        aria-label="Limpar busca"
      >×</button>
    </div>

    <!-- erro de load -->
    <div v-if="loadError" class="max-w-4xl mx-auto text-xs text-red-600 mt-1">
      Erro ao carregar histórico: {{ loadError }}
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useSearch } from '../composables/useSearch'

const {
  query,
  loading,
  loaded,
  loadError,
  isActive,
  results,
  daysIndexed,
  loadAllReports,
  clear,
} = useSearch()

const inputRef = ref(null)

// Debounce 200ms — atualiza query só quando o usuário pausa de digitar.
// Evita re-filtrar a cada tecla em ~30 relatórios × dezenas de items.
let debounceTimer = null
function onInput(e) {
  const val = e.target.value
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    query.value = val
  }, 200)
}

function onFocus() {
  // Lazy load no primeiro focus do input
  if (!loaded.value && !loading.value) loadAllReports()
}
const allReportsCount = daysIndexed
</script>
