<!-- frontend/src/components/PodcastCard.vue -->
<template>
  <div class="card group">
    <div class="flex items-start gap-3 mb-3">
      <span class="text-2xl flex-shrink-0">🎙️</span>
      <div class="flex-1 min-w-0">
        <div class="flex items-start justify-between gap-2">
          <h3 class="font-bold text-base md:text-lg group-hover:text-purple-600 transition-colors">
            {{ podcast.titulo }}
          </h3>
          <div class="flex flex-col items-end gap-1 flex-shrink-0">
            <span :class="[
              'badge',
              podcast.classe === 'A' ? 'badge-a' : podcast.classe === 'B' ? 'badge-b' : 'badge-c'
            ]">
              Classe {{ podcast.classe }}
            </span>
            <span class="text-xs font-bold text-gray-700">{{ podcast.score }}/10</span>
          </div>
        </div>
        <p class="text-sm text-gray-600">
          <span class="font-medium">{{ podcast.publicacao }}</span>
          <span v-if="podcast.host" class="text-gray-500"> · {{ podcast.host }}</span>
        </p>
      </div>
    </div>

    <p class="text-gray-700 text-sm mb-3 line-clamp-2">{{ podcast.resumo }}</p>

    <ul v-if="podcast.bullet_points?.length" class="space-y-1 mb-4 ml-1">
      <li
        v-for="(bullet, i) in podcast.bullet_points"
        :key="i"
        class="text-sm text-gray-700 flex items-start gap-2"
      >
        <span class="text-purple-500 flex-shrink-0 mt-0.5">▸</span>
        <span>{{ bullet }}</span>
      </li>
    </ul>

    <p v-if="podcast.impacto_clinico" class="text-sm text-gray-600 mb-4 italic">
      💡 {{ podcast.impacto_clinico }}
    </p>

    <div class="flex items-center justify-between gap-2 flex-wrap">
      <span class="text-xs text-gray-500">🎙️ Podcast</span>
      <div class="flex gap-2">
        <a
          v-if="podcast.links?.audio_url"
          :href="podcast.links.audio_url"
          target="_blank"
          rel="noopener"
          class="inline-flex items-center gap-2 px-3 py-2 bg-purple-100 text-purple-700 rounded-lg text-sm font-medium hover:bg-purple-200 transition-all"
          @click.stop
        >
          ▶ Ouvir
        </a>
        <a
          v-if="podcast.links?.episode_url"
          :href="podcast.links.episode_url"
          target="_blank"
          rel="noopener"
          class="inline-flex items-center gap-2 px-3 py-2 bg-blue-100 text-blue-700 rounded-lg text-sm font-medium hover:bg-blue-200 transition-all"
          @click.stop
        >
          📋 Show notes
        </a>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  podcast: Object
})
</script>
