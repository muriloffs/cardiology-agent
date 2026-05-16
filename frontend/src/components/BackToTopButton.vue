<!-- frontend/src/components/BackToTopButton.vue -->
<!--
  Floating action button (FAB) for "back to top" navigation.

  Pattern decisions:
  - Visible only after 400px of scroll (avoid clutter on short pages)
  - Bottom-right 24px (classic, doesn't conflict with mobile thumb zones)
  - Roxo (bg-purple-600) to match the "Artigos" tab visual identity
  - 48px circular — recognized "tap target" size on mobile (Material Design ≥44px)
  - Smooth fade in/out with cubic-bezier easing
  - Smooth scroll 600ms (não brusco, não lento demais)
  - aria-label for screen readers
-->
<template>
  <transition
    enter-active-class="transition-all duration-300 ease-out"
    enter-from-class="opacity-0 translate-y-2"
    enter-to-class="opacity-100 translate-y-0"
    leave-active-class="transition-all duration-300 ease-in"
    leave-from-class="opacity-100 translate-y-0"
    leave-to-class="opacity-0 translate-y-2"
  >
    <button
      v-show="visible"
      @click="scrollToTop"
      aria-label="Voltar ao topo da página"
      class="fixed bottom-6 right-6 z-50 w-12 h-12 rounded-full bg-purple-600 hover:bg-purple-700 active:bg-purple-800 text-white shadow-lg hover:shadow-xl transition-all flex items-center justify-center group focus:outline-none focus:ring-4 focus:ring-purple-300"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        class="w-6 h-6 transform group-hover:-translate-y-0.5 transition-transform"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        stroke-width="2.5"
      >
        <path stroke-linecap="round" stroke-linejoin="round" d="M5 15l7-7 7 7" />
      </svg>
    </button>
  </transition>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const visible = ref(false)
const SCROLL_THRESHOLD_PX = 400

function onScroll() {
  visible.value = window.scrollY > SCROLL_THRESHOLD_PX
}

function scrollToTop() {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

onMounted(() => {
  // passive: true para não bloquear o scroll do navegador (perf em mobile)
  window.addEventListener('scroll', onScroll, { passive: true })
  onScroll()  // sync initial state se a página já carregar scrolled
})

onUnmounted(() => {
  window.removeEventListener('scroll', onScroll)
})
</script>
