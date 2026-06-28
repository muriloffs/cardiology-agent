# Marcas "já li / já estudei" sincronizadas — Design

**Data:** 2026-06-28
**Status:** aprovado no brainstorming, aguardando revisão da spec

## Objetivo

Permitir marcar qualquer item do dashboard como "lido/estudado" e ver essa
marca **sincronizada entre todos os aparelhos** (celular, iPad, etc.), num site
que é estático (sem backend nem login). Resolve a dor de não saber, num aparelho,
o que já foi visto em outro.

## Decisões (definidas com o usuário)

- **Escopo:** todas as abas — Estudo, Revisões, Notícias, Vídeos, Imagens.
- **Marcação:** botão **✓ manual** em cada cartão (sem auto-marcar ao abrir).
- **Visual do lido:** o item **continua na lista**, com ✓ e **esmaecido**.
- **Sincronização:** **instantânea** na gravação; os outros aparelhos veem ao
  abrir/atualizar a página (não segue o cron diário do conteúdo).
- **Recarregar ao focar:** quando a aba do site volta a ficar visível, as marcas
  são relidas (sensação de "sempre sincronizado").
- **Senha:** uma vez por aparelho (guardada no navegador); protege só a escrita.
- **Armazenamento:** KV (Redis via Upstash na Vercel) — rápido, sem commits.
- **Substitui o Things:** o botão "Marcar como estudado (Things)" do leitor era
  uma ponte temporária. Quando o ✓ sincronizado estiver validado no Estudo,
  **remover o botão do Things** (o usuário não vai usá-lo).

## Arquitetura

```
[Aparelho A] --tap ✓--> POST /api/marcas (com senha) --> SADD no Redis
[Aparelho B] --abrir/focar--> GET /api/marcas --> SMEMBERS --> aplica ✓+esmaecido
```

O estado é um **conjunto (SET) de IDs** no Redis. Ler é aberto; escrever exige a
senha. O site lê o conjunto ao carregar e ao focar a aba, e marca visualmente os
itens cujo ID está no conjunto.

### Unidades (fronteiras claras)

1. **Função serverless `/api/marcas`** — único ponto de escrita; esconde a chave
   do KV e valida a senha. Não conhece o frontend.
2. **Composable `useReadMarks()`** (frontend, singleton) — carrega o conjunto,
   expõe `isRead(id)` e `toggle(id)` com atualização otimista; relê ao focar.
   Não conhece detalhes de cada aba.
3. **Botão `<ReadToggle :id>`** — componente burro: mostra o estado de um ID e
   chama `toggle`. Reutilizado em todas as listas.

## Identidade dos itens

ID estável com prefixo do tipo, para não colidir entre abas:

| Tipo     | ID                       | Campo-fonte                         |
|----------|--------------------------|-------------------------------------|
| Estudo   | `estudo:<slug>`          | slug do estudo                      |
| Revisão  | `revisao:<pmid>`         | PMID do artigo (fallback: link/slug)|
| Vídeo    | `video:<id>`             | id do YouTube                       |
| Notícia  | `noticia:<url>`          | URL da notícia                      |
| Imagem   | `imagem:<url>`           | image_url / link do tweet           |

O plano de implementação confirma, por tipo, qual campo estável existe no JSON
de cada item (e usa um fallback determinístico quando faltar).

## Backend — `/api/marcas`

- `GET /api/marcas` → `{ ids: ["estudo:...", "video:..."] }` (SMEMBERS). Aberto.
- `POST /api/marcas` body `{ id, lido }` + header `x-marcas-token`:
  - senha confere com `MARCAS_SECRET` (env) → `SADD` (lido=true) ou `SREM`
    (lido=false). Responde `{ ok: true }`.
  - senha errada/ausente → `401`.
- Chave única no Redis: `marcas:lidos` (um SET global do usuário).
- Variáveis de ambiente (injetadas pela integração KV da Vercel +1 manual):
  `KV_REST_API_URL`, `KV_REST_API_TOKEN`, `MARCAS_SECRET`.

## Frontend — UX e dados

- `useReadMarks()`:
  - no 1º uso: `GET /api/marcas` → preenche um `Set` reativo. Falha → `Set` vazio
    (site segue normal, nada marcado).
  - `isRead(id)` → boolean reativo.
  - `toggle(id)`: inverte localmente **na hora** (otimista) e dispara o `POST`;
    se o `POST` falhar, desfaz e mostra aviso discreto.
  - relê o conjunto no evento `visibilitychange` (aba volta a ficar visível).
  - lê a senha de `localStorage['marcas_token']`; sem senha, `toggle` fica
    desabilitado (modo leitura) e um campo discreto permite defini-la.
- Cada cartão/linha (estudo, artigo, vídeo, notícia, imagem) ganha:
  - `<ReadToggle :id="...">` (o ✓).
  - classe de esmaecido quando `isRead(id)` (ex.: opacidade reduzida).

## Configuração da Vercel

O `vercel.json` hoje reescreve **tudo** para `index.html`, o que engoliria
`/api`. Ajuste de 1 linha para excluir a rota da API:
`"source": "/((?!api/).*)"`.

## Tratamento de erros (degradação graciosa)

- KV/função indisponível no `GET` → conjunto vazio; o dashboard funciona igual,
  só sem as marcas. Nunca quebra a tela.
- Falha no `POST` → reverte a marca otimista + aviso discreto; nada é perdido.
- Sem senha → ✓ desabilitado; ver conteúdo e marcas continua funcionando.

## Testes

- **Função:** GET retorna o SET; POST com senha certa grava/remove; POST sem
  senha → 401 (KV mockado).
- **`useReadMarks`:** `isRead`/`toggle` otimista e reversão em falha (fetch
  mockado), no padrão dos `__tests__` já existentes.

## Esforço do usuário (uma vez)

1. Conectar um KV (Upstash) ao projeto na Vercel — alguns cliques; as variáveis
   `KV_REST_API_*` entram sozinhas (~5 min).
2. Definir `MARCAS_SECRET` (a senha) como variável de ambiente na Vercel + digitar
   a mesma senha uma vez em cada aparelho (1 min).

## Fora de escopo (próximo mini-passo, sem urgência)

**Retomar onde parou** (o app "volta ao começo" quando o navegador recarrega):
é um subsistema independente e **local** (lembrar última aba/mês/posição no
`localStorage` do aparelho — não precisa de KV nem senha). Será uma spec curta e
separada, logo após esta, para manter este escopo focado.
