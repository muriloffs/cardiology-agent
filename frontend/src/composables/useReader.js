/**
 * Reader mode for editorial cards on mobile/tablet.
 *
 * Module-level refs make this a singleton: any component that imports
 * `useReader()` gets the same `currentItem`, `mode`, and `fontSize`. A single
 * <ReaderModal> rendered in App.vue listens to `currentItem` and shows/hides.
 *
 * Adapted from culture-agent's manual (commit ec6f1d9, 2026-05-23). The four
 * `mode` values map to four card types in cardiology-agent:
 *   - "artigo"   : ArticleCard (RCTs, meta-analyses, guidelines)
 *   - "noticia"  : NoticiaCard (Gemini-enriched news)
 *   - "pulso"    : PulsoCard ("Pulso do Dia" highlights)
 *   - "substack" : SubstackCard (newsletter posts)
 *
 * Other card types (XDiscussion, Podcast, Video) are short or redirect to an
 * external source — they don't need a reader mode.
 */
import { ref, watch } from "vue"

const STORAGE_KEY = "reader.fontSize"
const FONT_DEFAULT = 22
const FONT_MIN = 16
const FONT_MAX = 36
const FONT_STEP = 2

// Module-level refs — mesma instância em qualquer import.
const currentItem = ref(null)
const mode = ref("artigo") // "artigo" | "noticia" | "pulso" | "substack"
const fontSize = ref(_loadFontSize())

function _loadFontSize() {
  if (typeof localStorage === "undefined") return FONT_DEFAULT
  const raw = parseInt(localStorage.getItem(STORAGE_KEY), 10)
  if (!Number.isFinite(raw)) return FONT_DEFAULT
  return Math.min(FONT_MAX, Math.max(FONT_MIN, raw))
}

watch(fontSize, (v) => {
  if (typeof localStorage !== "undefined") {
    localStorage.setItem(STORAGE_KEY, String(v))
  }
})

export function useReader() {
  return {
    currentItem,
    mode,
    fontSize,
    open(item, m = "artigo") {
      mode.value = m
      currentItem.value = item
    },
    close() {
      currentItem.value = null
    },
    incFont() {
      fontSize.value = Math.min(FONT_MAX, fontSize.value + FONT_STEP)
    },
    decFont() {
      fontSize.value = Math.max(FONT_MIN, fontSize.value - FONT_STEP)
    },
    canIncrease: () => fontSize.value < FONT_MAX,
    canDecrease: () => fontSize.value > FONT_MIN,
  }
}
