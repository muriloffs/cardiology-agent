<!-- frontend/src/components/VideoCard.vue -->
<template>
  <a
    :href="video.video_url"
    target="_blank"
    rel="noopener"
    class="card group block hover:shadow-lg transition-shadow"
  >
    <div class="flex gap-3">
      <!-- Thumbnail (links out, no embed) -->
      <div class="relative flex-shrink-0 w-32 sm:w-40 aspect-video rounded-md overflow-hidden bg-gray-100">
        <img
          v-if="video.thumbnail"
          :src="video.thumbnail"
          :alt="video.titulo"
          loading="lazy"
          class="w-full h-full object-cover"
          @error="onImgError"
        />
        <div class="absolute inset-0 flex items-center justify-center bg-black/30 opacity-0 group-hover:opacity-100 transition-opacity">
          <span class="text-white text-2xl">▶</span>
        </div>
      </div>

      <div class="flex-1 min-w-0">
        <div class="flex items-start justify-between gap-2 mb-1">
          <h3 class="font-bold text-sm md:text-base group-hover:text-purple-600 transition-colors line-clamp-2">
            {{ video.titulo }}
          </h3>
          <span
            v-if="video.tier === 0"
            class="flex-shrink-0 text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-800"
            title="Canal pinned (BR)"
          >
            ★ Pinned
          </span>
        </div>

        <p class="text-xs text-gray-600 mb-2">
          <span class="font-medium">{{ video.canal }}</span>
          <span class="text-gray-400"> · {{ video.data_publicacao }}</span>
        </p>

        <p
          v-if="video.descricao_preview"
          class="text-xs text-gray-700 line-clamp-2"
        >
          {{ video.descricao_preview }}
        </p>

        <div class="flex items-center gap-2 mt-2">
          <span class="text-[10px] text-gray-500">📺 YouTube</span>
        </div>
      </div>
    </div>
  </a>
</template>

<script setup>
defineProps({
  video: Object
})

function onImgError(e) {
  e.target.style.display = 'none'
}
</script>
