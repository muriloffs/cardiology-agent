<!-- frontend/src/components/CongressBanner.vue -->
<!--
  Surfaces "acontecendo agora" and "próximo congresso" badges based on the
  static CONGRESSES_2026 list and the user's local date. When a major congress
  is active, the dashboard's content landscape shifts (late-breaking trials,
  more X buzz, more press releases) — this banner contextualizes that.

  Renders nothing if there's nothing active or upcoming in the next 14 days.
-->
<template>
  <div v-if="active.length || upcoming.length || recentlyEnded.length" class="border-b border-gray-200">
    <div class="max-w-6xl mx-auto px-4 py-2.5 flex items-center gap-2 md:gap-3 flex-wrap">
      <!-- Active congresses -->
      <div
        v-for="c in active"
        :key="c.slug"
        :class="['inline-flex items-center gap-1.5 md:gap-2 px-2.5 md:px-3 py-1.5 rounded-full text-xs md:text-sm font-medium ring-1',
                 colorFor(c).bg, colorFor(c).text, colorFor(c).ring]"
      >
        <span class="text-sm md:text-base">{{ c.emoji }}</span>
        <span class="font-bold">🎪 <span class="hidden md:inline">Acontecendo agora · </span>{{ c.shortName }}</span>
        <span class="hidden md:inline opacity-75 text-xs">
          Dia {{ dayOf(c).current }} de {{ dayOf(c).total }} · {{ c.city }}
        </span>
        <span class="md:hidden opacity-75 text-[10px]">D{{ dayOf(c).current }}/{{ dayOf(c).total }}</span>
      </div>

      <!-- Recently ended (last 3 days) — retrospective analyses peak here -->
      <div
        v-for="item in recentlyEnded"
        :key="item.c.slug"
        :class="['inline-flex items-center gap-1.5 md:gap-2 px-2.5 md:px-3 py-1 rounded-full text-xs font-medium opacity-90',
                 colorFor(item.c).bg, colorFor(item.c).text]"
      >
        <span>{{ item.c.emoji }}</span>
        <span class="font-semibold">📍 {{ item.c.shortName }} acabou</span>
        <span class="opacity-75">
          {{ item.daysSince === 1 ? 'ontem' : `há ${item.daysSince}d` }}<span class="hidden md:inline"> · análises retrospectivas em alta</span>
        </span>
      </div>

      <!-- Upcoming (next 14 days) -->
      <div
        v-for="item in upcoming"
        :key="item.c.slug"
        :class="['inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium',
                 colorFor(item.c).bg, colorFor(item.c).text]"
      >
        <span>{{ item.c.emoji }}</span>
        <span class="font-semibold">⏳ {{ item.c.shortName }}</span>
        <span class="opacity-75">em {{ item.daysAway }} dia{{ item.daysAway !== 1 ? 's' : '' }} · {{ item.c.city }}</span>
      </div>

      <!-- Focus context (only when there's an active congress) -->
      <p v-if="active.length === 1" class="hidden md:block text-xs text-gray-500 ml-auto">
        Atenção da comunidade focada em: <strong>{{ active[0].focus }}</strong>
      </p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { CONGRESSES_2026, CATEGORY_COLORS, classifyCongresses, dayOfCongress } from '../data/congresses'

const classified = computed(() => classifyCongresses(new Date()))
const active = computed(() => classified.value.active)
const upcoming = computed(() => classified.value.upcoming)
const recentlyEnded = computed(() => classified.value.recentlyEnded)

function colorFor(c) {
  return CATEGORY_COLORS[c.category]
}
function dayOf(c) {
  return dayOfCongress(c, new Date())
}
</script>
