<!-- frontend/src/components/PodcastDetail.vue -->
<template>
  <div
    v-if="podcast"
    class="fixed inset-0 z-50 pointer-events-none flex items-start justify-center p-4 pt-12"
  >
    <div class="absolute inset-0 bg-black bg-opacity-50 pointer-events-auto cursor-pointer" @click="$emit('close')"></div>
    <div class="relative bg-white rounded-lg max-w-2xl w-full max-h-[85dvh] flex flex-col md:block md:overflow-y-auto pointer-events-auto">

      <!-- Header -->
      <div class="flex-shrink-0 bg-white border-b border-gray-200 p-4 md:p-6 flex items-start justify-between gap-3 rounded-t-lg">
        <div class="flex items-start gap-3 min-w-0">
          <span class="text-3xl md:text-4xl flex-shrink-0">{{ podcast.emoji || '🎙️' }}</span>
          <div class="min-w-0">
            <h2 class="text-lg md:text-2xl font-bold leading-tight">{{ podcast.titulo }}</h2>
            <p class="text-gray-600 text-sm md:text-base">
              <span class="font-medium">{{ podcast.publicacao }}</span>
              <span v-if="podcast.host" class="text-gray-500"> · {{ podcast.host }}</span>
            </p>
          </div>
        </div>
        <button
          @click="$emit('close')"
          class="flex-shrink-0 text-gray-500 hover:text-gray-700 font-bold text-2xl leading-none pt-1"
        >
          ✕
        </button>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto md:overflow-y-visible md:flex-none p-6 space-y-6">
        <!-- Classe + Score -->
        <div class="flex items-center gap-4">
          <span :class="[
            'badge',
            podcast.classe === 'A' ? 'badge-a' : podcast.classe === 'B' ? 'badge-b' : 'badge-c'
          ]">
            Classe {{ podcast.classe }}
          </span>
          <span class="text-lg font-bold text-gray-700">Score: {{ podcast.score }}/10</span>
        </div>

        <!-- Resumo PT-BR completo (sem line-clamp) -->
        <div>
          <h3 class="text-lg font-bold mb-2">Resumo</h3>
          <p class="text-gray-700 whitespace-pre-wrap">{{ podcast.resumo }}</p>
        </div>

        <!-- Takeaways clínicos -->
        <div v-if="podcast.bullet_points?.length">
          <h3 class="text-lg font-bold mb-3">🎯 Takeaways Clínicos</h3>
          <ul class="space-y-2">
            <li
              v-for="(bullet, i) in podcast.bullet_points"
              :key="i"
              class="flex items-start gap-3 bg-purple-50 rounded-lg p-3"
            >
              <span class="flex-shrink-0 w-6 h-6 rounded-full bg-purple-600 text-white text-xs font-bold flex items-center justify-center">{{ i + 1 }}</span>
              <span class="text-gray-800 text-sm md:text-base leading-relaxed">{{ bullet }}</span>
            </li>
          </ul>
        </div>

        <!-- Impacto na prática (caixa highlight) -->
        <div v-if="podcast.impacto_clinico" class="bg-yellow-50 border-l-4 border-yellow-400 rounded-r-lg p-4">
          <h3 class="text-base font-bold mb-1 text-yellow-900">💡 Impacto na Prática</h3>
          <p class="text-gray-800 text-sm md:text-base">{{ podcast.impacto_clinico }}</p>
        </div>

        <!-- Show notes originais (collapsible, em EN, do RSS) -->
        <details
          v-if="podcast.show_notes_original"
          class="bg-gray-50 rounded-lg group"
        >
          <summary class="cursor-pointer p-4 text-sm font-semibold text-gray-700 flex items-center justify-between hover:bg-gray-100 rounded-lg transition-colors">
            <span>📋 Show notes originais (RSS, em inglês)</span>
            <span class="text-xs text-gray-500 group-open:rotate-180 transition-transform">▼</span>
          </summary>
          <div class="px-4 pb-4 pt-1">
            <p class="text-xs md:text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">{{ podcast.show_notes_original }}</p>
          </div>
        </details>
      </div>

      <!-- Footer -->
      <div class="flex-shrink-0 p-4 border-t border-gray-200 flex gap-3 flex-wrap rounded-b-lg" style="padding-bottom: calc(env(safe-area-inset-bottom, 0px) + 1rem)">
        <a
          v-if="podcast.links?.audio_url"
          :href="podcast.links.audio_url"
          target="_blank"
          rel="noopener"
          class="inline-flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg font-medium hover:bg-purple-700 transition-all text-sm"
        >
          ▶ Ouvir
        </a>
        <a
          v-if="podcast.links?.episode_url"
          :href="podcast.links.episode_url"
          target="_blank"
          rel="noopener"
          class="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-all text-sm"
        >
          📋 Show notes externos
        </a>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  podcast: Object
})

defineEmits(['close'])
</script>
