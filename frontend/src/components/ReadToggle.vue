<script setup>
import { useReadMarks } from '../composables/useReadMarks'

const props = defineProps({ id: { type: String, required: true } })
const { isRead, toggle, hasToken } = useReadMarks()

async function onClick() {
  try { await toggle(props.id) } catch { alert('Não consegui salvar a marca. Tente de novo.') }
}
</script>

<template>
  <button
    class="inline-flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded-md border transition-colors"
    :class="isRead(id)
      ? 'bg-emerald-50 text-emerald-700 border-emerald-300'
      : 'bg-white text-gray-500 border-gray-300 hover:border-emerald-300'"
    :disabled="!hasToken()"
    :title="hasToken() ? 'Marcar/desmarcar como lido' : 'Defina sua senha (🔑 no topo) para marcar'"
    @click.stop="onClick"
  >
    {{ isRead(id) ? '✓ Lido' : '○ Marcar lido' }}
  </button>
</template>
