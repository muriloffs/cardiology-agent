# Módulo Estudo (Aprofundamento) — Especificação de Design

**Data:** 2026-06-26
**Projeto:** cardiology-agent
**Status:** Aprovado para plano de implementação

---

## Objetivo

Um **modo de profundidade** complementar ao radar diário. O radar é amplitude (varrer muito, saber o que existe). Este módulo é o oposto: pegar os poucos materiais que merecem domínio — **revisões, diretrizes, recomendações** (não trials, que são "saber que existe") — em PDF e em inglês, e transformá-los em **material de estudo em português**: condensado na proporção do original, sem perder conceito, sem inventar nada, com voz técnica e leitura ideal para aprendizado.

O usuário (cardiologista) seleciona e baixa os PDFs manualmente (hoje no Zotero). A IA assume daí: processa o documento e entrega um material de estudo de duas camadas, navegável por mês no mesmo site do radar.

---

## Princípios invioláveis

1. **Nada inventado.** Todo conteúdo vem do documento original. Toda referência externa (link) vem da bibliografia do próprio artigo ou de uma busca real — nunca de um DOI/link fabricado de memória.
2. **Proporcionalidade.** A saída escala com a fonte. 5 páginas → documento curto. 50 páginas → documento longo. Não existe tamanho fixo.
3. **Cobertura total.** Condensa redundância/verbosidade, mas preserva todo conceito, definição, recomendação e resultado numérico. Percorre seção por seção.
4. **Voz dupla e visível.** O leitor sempre sabe quem fala: o texto fiel ("o artigo") vs a camada de estudo ("o tutor"), visualmente distintos.
5. **Custo de infra zero.** Reaproveita GitHub Actions + Vercel + a chave Claude que o pipeline diário já usa.

---

## Arquitetura — o fluxo

```
Você (no PC)                 GitHub Actions (nuvem, automático)      Você (qualquer aparelho)
────────────                 ──────────────────────────────────     ───────────────────────
curar + baixar PDF (Zotero)
arrasta p/ study-inbox/  ──► detecta PDF novo
2 cliques (processar.bat)    extrai texto + figuras (PyMuPDF)
  → commit + push            Opus 4.8 gera o material de estudo
                             salva markdown + figuras + index   ──► abre o site → aba Estudo
                             comita o resultado                     lê em modo leitura
```

---

## Componentes

### 1. Ingestão — `study-inbox/`

- Pasta na **cópia local do projeto**: `C:\Users\totor\Downloads\claude code\study-inbox\`.
- O usuário arrasta o PDF para lá e dá dois cliques num atalho (`processar.bat`) que faz `git add` + `commit` + `push`. **O usuário nunca toca em git diretamente.**
- O `.bat` pode ser também do tipo "arraste o PDF em cima dele" (copia para `study-inbox/` e envia). Forma exata afinada na implementação.
- Múltiplos PDFs podem ser soltos de uma vez; cada um vira um estudo.

### 2. Gatilho — GitHub Actions

- Workflow `study-process.yml`, disparado por:
  - `push` que toque em `study-inbox/**.pdf`, **e/ou**
  - `workflow_dispatch` (botão manual).
- **Idempotência:** processa apenas PDFs em `study-inbox/` que ainda não têm estudo correspondente. Após processar com sucesso, **move o PDF** de `study-inbox/` para `study-inbox/processados/` (ou apaga, decisão de implementação) para não reprocessar.
- `timeout-minutes`: 30 (uma diretriz longa com Opus em alto esforço pode levar minutos; margem ampla).
- Permissões: `contents: write` (comita o resultado).
- Defensivo: qualquer falha num PDF não derruba os outros nem o workflow; loga e segue.

### 3. Motor de processamento — `agent/scripts/process_study.py`

**Modelo:** Opus 4.8 (`claude-opus-4-8`), trocável por variável de ambiente/config (`STUDY_MODEL`) para um eventual downgrade a Sonnet 4.6 se o volume crescer.

**Estratégia de passada única (1M de contexto):** o Opus 4.8 tem janela de 1 milhão de tokens. Mesmo uma diretriz de ~100 páginas cabe inteira numa única chamada. O modelo vê o documento completo de uma vez — sem fatiar, sem perder coerência global. O PDF é enviado como `document` block (base64), que dá ao modelo tanto o texto quanto a visão das páginas (necessária para ler tabelas/figuras).

**Pedido ao modelo (via prompt dedicado `agent/prompts/study_prompt.txt`):**
- **Faixa de compressão:** condensar para ~30–45% do tamanho do original. O modelo calibra o tamanho da saída ao tamanho da fonte.
- **Cobertura seção por seção:** percorrer a estrutura do original; não pular seções; preservar todo conceito, definição, recomendação e resultado numérico; cortar só redundância, metodologia verbosa e repetição.
- **Tradução para PT-BR**, voz técnica, leitura de aprendizado.
- **Duas camadas** (ver formato de saída abaixo).
- **Tabelas/algoritmos/figuras:** reconstruir o conteúdo em PT (tabela markdown / passos de fluxograma) — via a capacidade de visão. As figuras originais entram separadamente (ver extração abaixo).
- **Referências:** quando a camada de estudo apontar uma referência, usar a entrada exata da bibliografia do próprio artigo (autor, ano, journal, e DOI/PMID se presente).

**Parâmetros da API:** streaming (saída pode passar de 16K tokens), `max_tokens` alto (até 128K), `thinking: {type: "adaptive"}`, `output_config: {effort: "high"}`. Sem `temperature`/`budget_tokens` (removidos no Opus 4.8).

**Saída estruturada do modelo:** um JSON com `titulo`, `fonte`, `tipo` (revisão|diretriz|recomendação), `data`, `markdown` (o corpo de duas camadas), e `figuras` (lista de `{id, descricao_pt, pagina}` referenciando as figuras extraídas).

### 4. Extração de figuras — PyMuPDF

> **Risco de engenharia conhecido (o ponto mais frágil).** Figuras que já são imagem raster saem fáceis via `page.get_images()`. Tabelas/fluxogramas que são texto vetorial não são imagens extraíveis — precisam ser "fotografadas" renderizando a região da página (`page.get_pixmap(clip=...)`).

**Plano pragmático:**
- Extrair todas as imagens raster embutidas (figuras de resultado, gráficos).
- Para tabelas/algoritmos identificados pelo modelo (que retorna a página), **fallback:** renderizar a página inteira como PNG e embutir essa página.
- A **reconstrução em PT** (texto/tabela markdown via visão do Opus) sempre funciona — é o conteúdo estudável. A imagem original ao lado é o complemento de conferência; quando o recorte exato falha, vem como página inteira.
- Figuras salvas em `data/estudos/<slug>/fig-N.png`.

### 5. Armazenamento

```
data/estudos/
  index.json                       ← biblioteca, agrupada por mês
  <slug>/
    estudo.md                      ← material de estudo (markdown, duas camadas)
    meta.json                      ← {titulo, fonte, tipo, data, slug, mes}
    fig-1.png, fig-2.png ...       ← figuras extraídas
```

- `slug`: derivado do título (kebab-case, único).
- `index.json` schema:
  ```json
  {
    "gerado_em": "ISO-8601",
    "por_mes": {
      "2026-06": [
        {"slug": "...", "titulo": "...", "fonte": "@NEJM",
         "tipo": "revisão", "data": "2026-06-24"}
      ]
    },
    "meses_disponiveis": ["2026-06", "2026-05"]
  }
  ```
- O `index.json` precisa de exceção no `.gitignore` (como `imagens-x-sample.json` já tem), pois `data/*.json` é ignorado.

### 6. Formato do `estudo.md` — duas camadas

- **Texto fiel** = markdown normal (parágrafos, tabelas, headings de seção). É "o artigo falando".
- **Camada de estudo** = bloco destacado com convenção fixa, para o frontend pintar distinto:
  ```markdown
  > 🎓 **Aprofunde:** O conceito-chave aqui é a rigidez ventricular...
  > Ver ref. [12]: Pfeffer MA et al., NEJM 2019. [DOI](https://doi.org/...)
  ```
- **Figuras** referenciadas inline: `![Figura 1: forest plot de MACE](fig-1.png)` seguidas da tabela/descrição reconstruída em PT.
- **Headings de seção** (`## Diagnóstico`, `## Tratamento`...) alimentam o índice navegável no modo leitura.

### 7. Links de referência — lógica anti-invenção

- **Com DOI/PMID na bibliografia** (maioria dos artigos modernos): link direto clicável — `https://doi.org/<doi>` ou PubMed via PMID. O identificador *está no PDF*.
- **Sem DOI/PMID:** link de **busca** (PubMed ou Google Scholar) montado a partir da citação (autor/título/journal). Sempre resolve em algo real.
- **Nunca** fabricar um DOI ou URL direto de memória.
- Busca externa proativa (sugerir artigos novos além da bibliografia) = **fora de escopo / fase 2**.

### 8. Frontend — aba "📚 Estudo", navegável por mês

- Nova aba no `frontend/src/App.vue`, ao lado de Imagens e Revisões.
- **Navegação por mês idêntica à aba Revisões.** Criar `frontend/src/composables/useMonthlyStudies.js` **espelhando** `useMonthlyReviews.js` (`selectedMonth`, `monthCache`, `availableMonths`, `olderMonth/newerMonth`, `canOlder/canNewer`, `open()`), e reusar o componente de navegação ◄ ► já existente no App.vue.
  - Mostra o **mês corrente** por padrão; setas navegam meses anteriores. Quando vira o mês, a aba "rola" para o novo mês automaticamente.
- **Biblioteca do mês:** lista de estudos (título, fonte, tipo, data). Clicar abre o modo leitura.
- **Modo leitura** (`frontend/src/components/StudyReader.vue`):
  - Layout longform: largura confortável, tipografia de leitura, espaçamento generoso. Não truncado, não sintético, não gamificado.
  - Renderiza o markdown; a camada de estudo (`> 🎓 ...`) é pintada com cor/ícone distintos; tabelas limpas; figuras embutidas inline; referências como links clicáveis.
  - **Índice de seções** (a partir dos headings) para pular direto — útil em diretriz longa. Indicador discreto de progresso de leitura.
  - Funciona em iPhone/PC/qualquer plataforma (mesma base Vercel).
- Carrega os estudos do GitHub raw com cache-bust (mesmo padrão de `useXImages.js` / `useMonthlyReviews.js`).
- Precisa de um renderizador de markdown no frontend (ex: `marked` + sanitização) — escolha de lib na implementação.

---

## Tratamento de erros

- Motor defensivo: falha num PDF → loga, marca como falho, segue para os outros. Nunca derruba o workflow.
- PDF ilegível / escaneado sem texto: o Opus ainda lê via visão; se mesmo assim falhar, registra falha clara (não gera estudo vazio silencioso).
- Saída do modelo malformada (JSON): tentar reparar (`json_repair`, como em `fetch_x_images.py`); se irreparável, falha registrada.
- Frontend: estudo sem figuras / index vazio → estados vazios amigáveis, sem quebrar.

---

## Custo

- Opus 4.8 ($5 input / $25 output por 1M tokens). Por documento: ~$0,40–0,50 (revisão ~15 pág) a ~$1,20–1,50 (diretriz ~50 pág).
- Volume esperado: 2–4 documentos/semana → ~$5–18/mês. Trocável por Sonnet 4.6 (config) se o volume crescer.

---

## Fora de escopo (fase 2 / futuro)

- Busca externa proativa de referências no PubMed (além da bibliografia do artigo).
- Botão "Estudar a fundo" no dashboard do radar (atalho que busca o full-text aberto).
- Integração direta com a API do Zotero.
- Página de upload web / pasta na nuvem (Drive/Dropbox) — descartadas a favor do drop no repo.
- Tradução fiel 1:1 do documento inteiro (o foco é condensação proporcional, não tradução literal).

---

## Resumo das decisões

| Tema | Decisão |
|---|---|
| Entrada | Drop de PDF em `study-inbox/` + atalho `processar.bat` (commit+push automático) |
| Onde roda | GitHub Actions (assíncrono, `push` em `study-inbox/**.pdf` + manual), infra zero |
| Modelo | Opus 4.8 (janela 1M → documento inteiro numa passada), trocável por config |
| Saída | Markdown, duas camadas (fiel + estudo destacado), proporção ~30–45% |
| Figuras | Reconstruídas em PT + imagem original embutida (fallback: página inteira) |
| Referências | Da bibliografia do artigo; DOI/PMID → link direto, senão → link de busca; nunca fabricar |
| Armazenamento | `data/estudos/<slug>/` (markdown + figuras + meta), `index.json` por mês |
| Apresentação | Aba "📚 Estudo" no site atual, navegação por mês igual à de Revisões, modo leitura longform |
