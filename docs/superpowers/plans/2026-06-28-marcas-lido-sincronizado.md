# Marcas "já li / já estudei" sincronizadas — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Marcar qualquer item do dashboard como lido/estudado, com a marca sincronizada entre aparelhos via um KV na Vercel.

**Architecture:** Uma função serverless `/api/marcas` guarda um SET de IDs no Redis (Upstash/KV da Vercel); o frontend lê o conjunto (composable singleton `useReadMarks`) e marca os itens (componente `ReadToggle` + classe de esmaecido). Ler é aberto; escrever exige uma senha (env `MARCAS_SECRET`).

**Tech Stack:** Vue 3 + Vite (frontend/), Vitest (testes), função serverless Node (ESM) na Vercel, Upstash Redis REST.

## Global Constraints

- Frontend vive em `frontend/`; testes Vitest em `frontend/src/**/__tests__/`.
- Função serverless em `/api/` na raiz do repo (Vercel detecta automaticamente).
- Lógica pura compartilhada entre função e testes vive em `frontend/src/lib/` (ESM), importada pela função por caminho relativo (o bundler da Vercel inclui).
- Sem dependências novas no código: a função usa `fetch` nativo (Node 18+) contra a REST do Upstash.
- IDs sempre com prefixo de tipo: `estudo:<slug>`, `revisao:<url>`, `video:<video_url>`, `noticia:<id>`, `imagem:<image_url>`, etc.
- Chave única no Redis: `marcas:lidos`.
- Header da senha na escrita: `x-marcas-token`. localStorage key: `marcas_token`.

---

## Pré-requisitos (setup do usuário na Vercel — feito uma vez)

Estes passos não são código; são necessários para o teste ponta-a-ponta (Task 4+).
O usuário executa (guiado):

1. No painel da Vercel → projeto → **Storage** → adicionar um **KV (Upstash Redis)** e conectar ao projeto. Isso injeta `KV_REST_API_URL` e `KV_REST_API_TOKEN` como variáveis de ambiente.
2. Em **Settings → Environment Variables**, criar `MARCAS_SECRET` com uma senha à escolha (ex.: uma frase). Aplicar a Production + Preview.

As Tasks 1–3 são testáveis sem isso (com mocks). A Task 4 valida ponta-a-ponta.

---

## File Structure

- `vercel.json` (modificar) — excluir `/api` do rewrite catch-all.
- `frontend/src/lib/marcasCore.js` (criar) — lógica pura: `authorize`, `redisPlan`.
- `frontend/src/lib/__tests__/marcasCore.spec.js` (criar) — testes da lógica pura.
- `api/marcas.mjs` (criar) — handler serverless: env + REST do Upstash.
- `frontend/src/composables/useReadMarks.js` (criar) — estado singleton + isRead/toggle/senha + recarrega ao focar.
- `frontend/src/composables/__tests__/useReadMarks.spec.js` (criar) — testes do composable.
- `frontend/src/components/ReadToggle.vue` (criar) — botão ✓ por item.
- `frontend/src/components/StudyReader.vue` (modificar) — trocar botão Things por ReadToggle.
- `frontend/src/App.vue` (modificar) — senha no cabeçalho + integrar ReadToggle/esmaecido nas abas.

---

### Task 1: Função `/api/marcas` (backend) + lógica pura

**Files:**
- Create: `frontend/src/lib/marcasCore.js`
- Test: `frontend/src/lib/__tests__/marcasCore.spec.js`
- Create: `api/marcas.mjs`
- Modify: `vercel.json`

**Interfaces:**
- Produces: `authorize(token, secret) -> boolean`; `redisPlan(method, body) -> { cmd: 'smembers' } | { cmd: 'sadd'|'srem', member: string } | { error: string }`
- Produces (HTTP): `GET /api/marcas -> { ids: string[] }`; `POST /api/marcas {id, lido}` com header `x-marcas-token` -> `{ ok: true }` | 401 | 400.

- [ ] **Step 1: Escrever o teste da lógica pura (falhando)**

`frontend/src/lib/__tests__/marcasCore.spec.js`:
```js
import { describe, it, expect } from 'vitest'
import { authorize, redisPlan } from '../marcasCore'

describe('marcasCore', () => {
  it('authorize só aceita token igual ao secret não-vazio', () => {
    expect(authorize('abc', 'abc')).toBe(true)
    expect(authorize('abc', 'xyz')).toBe(false)
    expect(authorize('', '')).toBe(false)
    expect(authorize(undefined, 'abc')).toBe(false)
  })
  it('redisPlan: GET lista', () => {
    expect(redisPlan('GET', null)).toEqual({ cmd: 'smembers' })
  })
  it('redisPlan: POST adiciona/remove pelo campo lido', () => {
    expect(redisPlan('POST', { id: 'estudo:x', lido: true })).toEqual({ cmd: 'sadd', member: 'estudo:x' })
    expect(redisPlan('POST', { id: 'estudo:x', lido: false })).toEqual({ cmd: 'srem', member: 'estudo:x' })
  })
  it('redisPlan: POST sem id é erro', () => {
    expect(redisPlan('POST', {}).error).toBeTruthy()
  })
  it('redisPlan: método não suportado é erro', () => {
    expect(redisPlan('PUT', {}).error).toBeTruthy()
  })
})
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd frontend && npx vitest run src/lib/__tests__/marcasCore.spec.js`
Expected: FAIL (módulo `../marcasCore` não existe).

- [ ] **Step 3: Implementar a lógica pura**

`frontend/src/lib/marcasCore.js`:
```js
// Lógica pura da função /api/marcas — sem I/O, testável e compartilhada.
export function authorize(token, secret) {
  return Boolean(secret) && token === secret
}

export function redisPlan(method, body) {
  if (method === 'GET') return { cmd: 'smembers' }
  if (method === 'POST') {
    const id = body && body.id
    if (!id || typeof id !== 'string') return { error: 'id obrigatório' }
    return { cmd: body.lido ? 'sadd' : 'srem', member: id }
  }
  return { error: 'método não suportado' }
}
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd frontend && npx vitest run src/lib/__tests__/marcasCore.spec.js`
Expected: PASS (5 testes).

- [ ] **Step 5: Implementar o handler serverless**

`api/marcas.mjs`:
```js
import { authorize, redisPlan } from '../frontend/src/lib/marcasCore.js'

const KEY = 'marcas:lidos'

// REST do Upstash: POST com corpo ["CMD","arg1",...] -> { result }
async function redis(args) {
  const base = process.env.KV_REST_API_URL
  const token = process.env.KV_REST_API_TOKEN
  const r = await fetch(base, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(args),
  })
  if (!r.ok) throw new Error(`KV ${r.status}`)
  return r.json()
}

export default async function handler(req, res) {
  try {
    if (req.method === 'GET') {
      const out = await redis(['SMEMBERS', KEY])
      return res.status(200).json({ ids: out.result || [] })
    }
    if (req.method === 'POST') {
      if (!authorize(req.headers['x-marcas-token'], process.env.MARCAS_SECRET)) {
        return res.status(401).json({ error: 'senha inválida' })
      }
      const body = typeof req.body === 'string' ? JSON.parse(req.body) : req.body
      const plan = redisPlan('POST', body)
      if (plan.error) return res.status(400).json({ error: plan.error })
      await redis([plan.cmd.toUpperCase(), KEY, plan.member])
      return res.status(200).json({ ok: true })
    }
    return res.status(405).json({ error: 'método não suportado' })
  } catch (e) {
    return res.status(500).json({ error: String(e) })
  }
}
```

- [ ] **Step 6: Liberar `/api` no rewrite do Vercel**

`vercel.json` — trocar o rewrite catch-all para não capturar `/api`:
```json
{
  "buildCommand": "cd frontend && npm install && npm run build",
  "outputDirectory": "frontend/dist",
  "rewrites": [
    { "source": "/((?!api/).*)", "destination": "/index.html" }
  ]
}
```

- [ ] **Step 7: Commit**

```bash
git add frontend/src/lib/marcasCore.js frontend/src/lib/__tests__/marcasCore.spec.js api/marcas.mjs vercel.json
git commit -m "feat(marcas): funcao /api/marcas (KV) + logica pura testada + libera /api no vercel.json"
```

---

### Task 2: Composable `useReadMarks` (estado + sync)

**Files:**
- Create: `frontend/src/composables/useReadMarks.js`
- Test: `frontend/src/composables/__tests__/useReadMarks.spec.js`

**Interfaces:**
- Consumes: `GET/POST /api/marcas` (Task 1).
- Produces: `useReadMarks() -> { isRead(id)->bool, toggle(id)->Promise, hasToken()->bool, setToken(t), reload() }` (singleton).

- [ ] **Step 1: Escrever os testes (falhando)**

`frontend/src/composables/__tests__/useReadMarks.spec.js`:
```js
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useReadMarks } from '../useReadMarks'

function mockFetch(getIds = []) {
  return vi.fn((url, opts) => {
    if (!opts || opts.method !== 'POST') {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ ids: getIds }) })
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve({ ok: true }) })
  })
}

describe('useReadMarks', () => {
  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem('marcas_token', 'senha')
  })

  it('carrega os ids do GET e isRead reflete', async () => {
    global.fetch = mockFetch(['estudo:a'])
    const m = useReadMarks()
    await m.reload()
    expect(m.isRead('estudo:a')).toBe(true)
    expect(m.isRead('estudo:b')).toBe(false)
  })

  it('toggle marca otimista e chama POST com token', async () => {
    global.fetch = mockFetch([])
    const m = useReadMarks()
    await m.reload()
    await m.toggle('estudo:b')
    expect(m.isRead('estudo:b')).toBe(true)
    const call = global.fetch.mock.calls.find(c => c[1] && c[1].method === 'POST')
    expect(call[1].headers['x-marcas-token']).toBe('senha')
    expect(JSON.parse(call[1].body)).toEqual({ id: 'estudo:b', lido: true })
  })

  it('reverte a marca se o POST falhar', async () => {
    global.fetch = vi.fn((url, opts) => {
      if (opts && opts.method === 'POST') return Promise.resolve({ ok: false })
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ ids: [] }) })
    })
    const m = useReadMarks()
    await m.reload()
    await expect(m.toggle('estudo:c')).rejects.toThrow()
    expect(m.isRead('estudo:c')).toBe(false)
  })
})
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd frontend && npx vitest run src/composables/__tests__/useReadMarks.spec.js`
Expected: FAIL (módulo não existe).

- [ ] **Step 3: Implementar o composable**

`frontend/src/composables/useReadMarks.js`:
```js
import { ref } from 'vue'

const TOKEN_KEY = 'marcas_token'
const ids = ref(new Set())   // singleton
let started = false

async function reload() {
  try {
    const r = await fetch('/api/marcas')
    if (r.ok) ids.value = new Set((await r.json()).ids || [])
  } catch { /* mantém o que tem; nunca quebra a tela */ }
}

export function useReadMarks() {
  if (!started) {
    started = true
    reload()
    if (typeof document !== 'undefined') {
      document.addEventListener('visibilitychange', () => {
        if (!document.hidden) reload()   // recarrega ao voltar pra aba
      })
    }
  }

  function isRead(id) { return ids.value.has(id) }
  function hasToken() { return Boolean(localStorage.getItem(TOKEN_KEY)) }
  function setToken(t) { if (t) localStorage.setItem(TOKEN_KEY, t) }

  async function toggle(id) {
    const novo = !ids.value.has(id)
    const otim = new Set(ids.value)
    novo ? otim.add(id) : otim.delete(id)
    ids.value = otim                       // otimista
    try {
      const r = await fetch('/api/marcas', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-marcas-token': localStorage.getItem(TOKEN_KEY) || '' },
        body: JSON.stringify({ id, lido: novo }),
      })
      if (!r.ok) throw new Error('falha ao salvar')
    } catch (e) {
      const rev = new Set(ids.value)
      novo ? rev.delete(id) : rev.add(id)
      ids.value = rev                      // reverte
      throw e
    }
  }

  return { isRead, toggle, hasToken, setToken, reload }
}
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd frontend && npx vitest run src/composables/__tests__/useReadMarks.spec.js`
Expected: PASS (3 testes).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/composables/useReadMarks.js frontend/src/composables/__tests__/useReadMarks.spec.js
git commit -m "feat(marcas): composable useReadMarks (sync otimista + recarrega ao focar)"
```

---

### Task 3: Componente `ReadToggle` + entrada de senha

**Files:**
- Create: `frontend/src/components/ReadToggle.vue`
- Modify: `frontend/src/App.vue` (botão 🔑 de senha no cabeçalho)

**Interfaces:**
- Consumes: `useReadMarks()` (Task 2).
- Produces: `<ReadToggle :id="string" />` — botão que mostra/inverte o estado de um ID.

- [ ] **Step 1: Implementar o componente**

`frontend/src/components/ReadToggle.vue`:
```vue
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
```

- [ ] **Step 2: Adicionar o botão de senha 🔑 no cabeçalho do App.vue**

Em `frontend/src/App.vue`, no `<script setup>` (perto dos outros `import`):
```js
import { useReadMarks } from './composables/useReadMarks'
const { setToken: setMarcasToken, hasToken: hasMarcasToken } = useReadMarks()
function pedirSenhaMarcas() {
  const t = window.prompt('Sua senha de marcação (definida na Vercel). Fica salva só neste aparelho.')
  if (t) { setMarcasToken(t); location.reload() }
}
```
No template, dentro do cabeçalho (ao lado de outros controles globais do topo), adicionar:
```html
<button class="text-xs px-2 py-1 rounded-md border border-gray-300 text-gray-500 hover:border-emerald-300"
        :title="hasMarcasToken() ? 'Senha de marcação definida neste aparelho' : 'Definir senha de marcação'"
        @click="pedirSenhaMarcas">
  {{ hasMarcasToken() ? '🔑 ✓' : '🔑' }}
</button>
```

- [ ] **Step 3: Build de sanidade**

Run: `cd frontend && npm run build`
Expected: build conclui sem erro.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ReadToggle.vue frontend/src/App.vue
git commit -m "feat(marcas): componente ReadToggle + entrada de senha no cabecalho"
```

---

### Task 4: Integrar no Estudo (lista + leitor) e remover o Things

**Files:**
- Modify: `frontend/src/App.vue` (lista de estudos, ~linha 834-844)
- Modify: `frontend/src/components/StudyReader.vue` (trocar Things por ReadToggle)

**Interfaces:**
- Consumes: `useReadMarks()`, `<ReadToggle>`.
- ID do estudo: `estudo:<slug>`.

- [ ] **Step 1: Importar ReadToggle e isRead no App.vue**

No `<script setup>` do `frontend/src/App.vue`:
```js
import ReadToggle from './components/ReadToggle.vue'
```
E reaproveitar o `useReadMarks` já importado na Task 3, expondo `isRead`:
```js
const { setToken: setMarcasToken, hasToken: hasMarcasToken, isRead: isReadMark } = useReadMarks()
```

- [ ] **Step 2: Esmaecer + ✓ na lista de estudos**

Em `frontend/src/App.vue`, no `<li v-for="it in studiesItems" :key="it.slug" ...>` (~834):
- adicionar no `<li>`: `:class="{ 'opacity-50': isReadMark('estudo:' + it.slug) }"`
- logo após o `<button ...>` que abre o estudo (dentro do `<li>`), adicionar uma linha de ação:
```html
<div class="px-3 pb-2">
  <ReadToggle :id="'estudo:' + it.slug" />
</div>
```

- [ ] **Step 3: Trocar o botão do Things por ReadToggle no leitor**

Em `frontend/src/components/StudyReader.vue`:
- remover o `thingsUrl` (computed) do `<script setup>` e os elementos `.things-mark` / `.things-hint` do template e os estilos correspondentes.
- importar e usar o ReadToggle. No `<script setup>`:
```js
import ReadToggle from './ReadToggle.vue'
```
- no template, no lugar onde estava o botão do Things (após `<article>`):
```html
<div class="mark-row">
  <ReadToggle :id="'estudo:' + slug" />
</div>
```
- estilo:
```css
.mark-row { margin-top: 2.5rem; }
```

- [ ] **Step 4: Build de sanidade**

Run: `cd frontend && npm run build`
Expected: build conclui sem erro; nenhuma referência restante a `thingsUrl`/`things-mark`.

- [ ] **Step 5: Validação ponta-a-ponta (requer setup do KV)**

Após deploy (push → Vercel): no aparelho, clicar 🔑 e digitar a senha; abrir um estudo; clicar "○ Marcar lido" → vira "✓ Lido"; recarregar a página → continua ✓; abrir em outro aparelho → aparece ✓ e esmaecido.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/App.vue frontend/src/components/StudyReader.vue
git commit -m "feat(marcas): ReadToggle no Estudo (lista+leitor) e remove o botao Things"
```

---

### Task 5: Estender às demais abas

**Files:**
- Modify: `frontend/src/App.vue` (vários `v-for`)

**Interfaces:**
- Consumes: `useReadMarks()` (`isReadMark`), `<ReadToggle>`.
- IDs por tipo (campo estável confirmado na inspeção):

| Aba/lista        | `v-for` (App.vue ~linha) | ID                               |
|------------------|--------------------------|----------------------------------|
| Revisões         | `(it,i) in reviewsFiltrados` (680) | `'revisao:' + (revUrl(it.article) || it.article.titulo)` |
| Notícias         | `article in filteredNoticias` (285) | `'noticia:' + article.id`        |
| Vídeos           | `video in filteredVideos` (503)     | `'video:' + video.video_url`     |
| Imagens          | `(im,i) in xImagesData.imagens` (756) | `'imagem:' + im.image_url`      |
| Pulso            | `item in report.pulso` (388)        | `'pulso:' + item.id`             |
| Discussões (X)   | `discussion in filteredDiscussoes` (351) | `'discussao:' + discussion.id` |
| Substacks        | `post in filteredSubstacks` (442)   | `'substack:' + (post.id || post.url)` |
| Podcasts         | `podcast in filteredPodcasts` (547) | `'podcast:' + podcast.id`        |
| Ideias           | `idea in filteredIdeas` (598)       | `'ideia:' + (idea.id || idea.ideia)` |

- [ ] **Step 1: Para cada lista da tabela acima, aplicar o mesmo padrão**

No `<li>`/cartão de cada `v-for`:
- esmaecer: adicionar `:class="{ 'opacity-50': isReadMark(<ID>) }"` (combinar com classes existentes).
- ação: adicionar `<ReadToggle :id="<ID>" />` num canto do cartão (ex.: junto aos links/ações do item).

Exemplo concreto (Notícias, ~285):
```html
<li v-for="article in filteredNoticias" :key="article.id"
    :class="['...classes atuais...', { 'opacity-50': isReadMark('noticia:' + article.id) }]">
  <!-- ...conteúdo atual... -->
  <div class="mt-2"><ReadToggle :id="'noticia:' + article.id" /></div>
</li>
```
Repetir, trocando o ID conforme a tabela, em: Revisões, Vídeos, Imagens, Pulso, Discussões, Substacks, Podcasts, Ideias.

- [ ] **Step 2: Build de sanidade**

Run: `cd frontend && npm run build`
Expected: build conclui sem erro.

- [ ] **Step 3: Validação visual (após deploy)**

Em cada aba: o ✓ aparece em cada item; marcar esmaece; recarregar mantém; outro aparelho reflete.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.vue
git commit -m "feat(marcas): ReadToggle + esmaecido em todas as abas do dashboard"
```

---

## Self-Review (preenchido)

**Cobertura da spec:** escopo todas as abas → Task 4 (Estudo) + Task 5 (demais). ✓ manual → ReadToggle. Esmaecido → classe `opacity-50`. Sync instantâneo → toggle otimista + POST. Recarrega ao focar → `visibilitychange` no useReadMarks. Senha 1x/aparelho → localStorage `marcas_token` + 🔑. KV/função → Task 1. Vercel rewrite → Task 1 Step 6. Substitui Things → Task 4 Step 3. Degradação graciosa → try/catch no reload/toggle. Testes → Tasks 1 e 2. Tudo coberto.

**Placeholders:** nenhum — todo passo tem código/comando reais.

**Consistência de tipos:** `isRead/toggle/hasToken/setToken/reload` idênticos entre Task 2 (definição), Task 3 e Task 4 (uso). IDs sempre `tipo:valor`. Header `x-marcas-token` e key `marcas_token` consistentes entre função (Task 1) e composable (Task 2).
