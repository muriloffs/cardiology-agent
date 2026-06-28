<script setup>
import { useFavoritos } from '../composables/useFavoritos'

const props = defineProps({
  id: { type: String, required: true },
  type: { type: String, required: true },
  item: { type: Object, required: true },
})
const { isFav, toggle, hasToken } = useFavoritos()

async function onClick() {
  try { await toggle(props.id, props.type, props.item) }
  catch { alert('Não consegui salvar o favorito. Tente de novo.') }
}
</script>

<template>
  <button
    @click.stop="onClick"
    :disabled="!hasToken()"
    :title="hasToken() ? 'Favoritar / desfavoritar' : 'Defina sua senha (🔑 no topo) para favoritar'"
    class="inline-flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded-md border transition-colors"
    :class="isFav(id)
      ? 'bg-amber-50 text-amber-700 border-amber-300'
      : 'bg-white text-gray-500 border-gray-300 hover:border-amber-300'"
  >
    {{ isFav(id) ? '★ Salvo' : '☆ Salvar' }}
  </button>
</template>
