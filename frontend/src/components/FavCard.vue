<script setup>
// Renderiza um favorito (snapshot) com o card certo conforme o tipo.
import ArticleCard from './ArticleCard.vue'
import NoticiaCard from './NoticiaCard.vue'
import VideoCardEnriched from './VideoCardEnriched.vue'
import PulsoCard from './PulsoCard.vue'
import SubstackCard from './SubstackCard.vue'
import XDiscussionCard from './XDiscussionCard.vue'

defineProps({ fav: { type: Object, required: true } })
</script>

<template>
  <ArticleCard v-if="fav.type === 'artigo'" :article="fav.item" />
  <NoticiaCard v-else-if="fav.type === 'noticia'" :noticia="fav.item" />
  <VideoCardEnriched v-else-if="fav.type === 'video'" :video="fav.item" />
  <PulsoCard v-else-if="fav.type === 'pulso'" :item="fav.item" />
  <SubstackCard v-else-if="fav.type === 'substack'" :post="fav.item" />
  <XDiscussionCard v-else-if="fav.type === 'discussao'" :discussion="fav.item" />
  <div v-else class="border border-gray-200 rounded-lg p-3 bg-white text-sm text-gray-700">
    {{ fav.item.titulo || fav.id }}
  </div>
</template>
