# Manual: Briefing de áudio via NotebookLM ("criar podcast")

> Como transformar o relatório diário num podcast de áudio usando o NotebookLM.
> Implementado no cardiology-agent (botão "📋 Copiar briefing"). Replicável
> para outros agentes que tenham relatório estruturado.

## A ideia em uma frase

Não construir TTS. Gerar um **documento de texto estruturado** do dia (botão
que copia pro clipboard), colar no NotebookLM como fonte, e usar o recurso
"criar podcast" (Audio Overview) pra ouvir o dia em ~10 minutos.

## Como o NotebookLM funciona (o que importa pro design)

Pesquisado e confirmado (2026-06):

1. **O NotebookLM NÃO tem API pública** (versão consumidor). Não dá pra enviar
   automático. Sempre há 1 passo manual: colar a fonte + criar o podcast.
2. **Documento = conteúdo. Comando = caixa separada.** O NotebookLM trata a
   fonte como material a resumir, **não obedece instruções escritas dentro do
   documento** (pode até narrá-las em voz alta). O comportamento (tom, foco,
   cobertura) vem SÓ da caixa de personalização ao "criar podcast".
3. **Instruções customizadas valem muito** — pontuam ~3,8× mais úteis que o
   default. O prompt importa.
4. **O prompt é sempre o mesmo** → você cola uma vez no NotebookLM e reusa.

**Conclusão de design:** separar as duas camadas.
- **Documento** (o botão gera): conteúdo limpo, hierarquizado, SEM comandos.
- **Prompt** (você cola na caixa "criar podcast", uma vez): toda a instrução
  de comportamento.

## Estrutura do documento (o que o botão "Copiar" gera)

Ordem pensada para o consumo (ajuste os campos ao schema do seu agente):

```
Briefing de Cardiologia — [data por extenso]
Resumo do dia: N artigos, N notícias, N destaques.

SEÇÃO 1 — DESTAQUES DO DIA (o que está em maior evidência)
1. [título]. [razão do destaque]
...

SEÇÃO 2 — REVISÕES E DIRETRIZES PUBLICADAS HOJE (vale ler na íntegra)
- [título] (fonte). Sobre o quê: [contexto]
...

SEÇÃO 3 — TODOS OS ARTIGOS DO DIA (o que é + conclusão)
Tema: [patologia]
- [título] [Classe]. Conclusão: [veredito]
...

SEÇÃO 4 — NOTÍCIAS DO DIA
- [título] (fonte). [por que importa]
...

Fim do briefing.
```

**Por que essa estrutura:**
- Seção 2 sinalizada explicitamente — o NotebookLM "vê" que aquilo é a categoria
  "ler na íntegra" e o prompt manda enfatizar.
- Seção 3 agrupada por tema (patologia) deixa o áudio navegável: "agora, em
  insuficiência cardíaca...". (Depende do campo `tema_principal`.)
- Tudo incluído (não só destaques) — cobertura completa é o objetivo.

## O PROMPT do NotebookLM (cole UMA vez na caixa "criar podcast")

```
Este é um briefing diário de cardiologia para UM cardiologista
(público especialista — use termos técnicos sem explicar o básico).
Cubra TODOS os itens do documento, não só os destaques — é importante
saber de tudo que foi publicado. Para cada artigo, diga em uma frase o
que é e qual a conclusão. Na seção de REVISÕES E DIRETRIZES, enfatize
que são leituras para baixar e ler na íntegra. Ritmo eficiente, de quem
já conhece o campo. Português brasileiro.
```

Salve esse prompt (no NotebookLM dá pra ver/reusar via "Ver prompt
personalizado" no menu de três pontos). Ele não muda de um dia pro outro.

### Variante "expandida" do prompt de áudio (opcional — corta a enrolação)

O NotebookLM tende a encher de conversa fiada. Esta versão adiciona anti-banter,
ordem das seções e transição por tema. Teste ouvindo qual prefere:

```
Briefing diário de cardiologia para UM cardiologista (especialista —
use termos técnicos sem explicar o básico; pronuncie siglas como TAVR,
HFpEF, SGLT2 com naturalidade).

Percorra o documento na ORDEM das seções: primeiro os destaques, depois
as revisões e diretrizes, depois os artigos por tema, por fim as
notícias. Cubra TODOS os itens, não só os destaques.

Por artigo: uma frase com o que é + a conclusão. Nada além disso.
Ao trocar de tema, anuncie ("agora, em insuficiência cardíaca...").
Na seção de revisões e diretrizes, deixe claro que são leituras para
baixar e ler na íntegra.

Estilo: ritmo eficiente, direto ao ponto. EVITE conversa fiada, reações
genéricas ("nossa, fascinante!") e repetições — é um briefing técnico,
não um bate-papo descontraído. Português brasileiro.
```

Controle de duração: o NotebookLM tem "Mais curto / Padrão / Mais longo". Se
30 min ficar longo, use "Mais curto" + o prompt acima.

## Outros formatos do mesmo documento (slides e mapa mental)

O MESMO documento (botão "Copiar briefing") serve para os três formatos do
NotebookLM. Você gera uma vez e escolhe ouvir, ver ou mapear. Os três aceitam
prompt (o Mapa Mental ganhou customização em maio/2026, nas contas pagas).

### 🎬 Slides (Visão geral em vídeo)

```
Apresentação visual do briefing diário de cardiologia para UM cardiologista
especialista. Siga a ordem do documento: destaques, revisões e diretrizes,
artigos por tema, notícias.

Um slide por estudo relevante (agrupe estudos do mesmo tema quando fizer
sentido). Em cada slide: título curto + a CONCLUSÃO como frase de destaque +
os números-chave (HR, IC 95%, p, n) quando houver.

Dê um slide-separador destacado para "Revisões e diretrizes — ler na íntegra",
listando-as.

Linguagem técnica, sem explicar o básico. Direto ao ponto, sem slides de
enchimento. Português brasileiro.
```

### 🧠 Mapa mental

```
Mapa mental do dia em cardiologia, para um cardiologista especialista.

Nó central: "Cardiologia — [data]".
Ramos principais: os TEMAS / patologias (insuficiência cardíaca, doença
coronariana, arritmias, valvopatias, etc.).
Sob cada tema: um nó por estudo, com o título curto; abaixo do estudo, um nó
com a conclusão em poucas palavras.
Crie um ramo separado e destacado: "Revisões e diretrizes — ler na íntegra".

Rótulos curtos e específicos (com números quando relevante). Português
brasileiro.
```

Os três aproveitam o agrupamento por `tema_principal`: no mapa mental os temas
viram os ramos; nos slides, os separadores de seção; no áudio, as transições.

## Passo a passo diário (~30 segundos)

1. No dashboard, toque **"📋 Copiar briefing"** (copia o dia pro clipboard).
2. Abra o NotebookLM → seu caderno de cardiologia.
3. "Adicionar fonte" → "Texto colado" → cole (Ctrl/Cmd+V).
4. "Criar podcast" (Audio Overview) → cole o prompt acima (na 1ª vez; depois
   ele lembra) → gerar.
5. ~2-5 min depois, o áudio está pronto. Ouça.

**Dica:** apague a fonte do dia anterior antes de colar a nova, ou o podcast
mistura dias. Ou use um caderno novo por dia.

## Implementação técnica (frontend)

Um composable + um botão. Zero backend, zero custo LLM.

- `composables/useAudioBriefing.js`:
  - `buildAudioBriefing(report)` → monta o texto a partir do JSON do dia.
  - `copyAudioBriefing(report)` → escreve no clipboard (Clipboard API +
    fallback `execCommand` para contextos sem permissão).
- Botão no `App.vue` que chama `copyAudioBriefing` e mostra "✓ Copiado!".

Detalhes:
- **Texto limpo, não markdown pesado.** O NotebookLM lê melhor texto corrido
  com seções em CAIXA ALTA do que `##` e `**`.
- **Clipboard API precisa de https + gesto do usuário** — o clique no botão
  satisfaz. Fallback com `<textarea>` + `execCommand('copy')` cobre browsers
  antigos.
- **Degradação graciosa:** relatórios antigos (sem `tema_principal`) caem todos
  em "Outros temas" — funciona, só não agrupa. Melhora quando o campo existe.

## Anti-padrões a evitar

| ❌ Anti-padrão | ✅ Por quê não |
|---|---|
| Escrever comandos dentro do documento ("NotebookLM, faça X") | Ele não obedece; pode narrar a instrução no áudio |
| Amarrar o formato do doc ao prompt | São camadas separadas; o prompt é fixo, o doc é conteúdo |
| Markdown pesado (`##`, `**`, tabelas) na fonte | TTS lê pior; prefira texto corrido + seções em CAIXA ALTA |
| Mandar o relatório inteiro cru (8 seções por artigo) | Vira parede de texto; o NotebookLM pula itens. Resuma a "o que é + conclusão" |
| Tentar automatizar via ferramentas não-oficiais (Playwright) | Frágeis, quebram quando o Google muda a UI, ferem ToS |
| Esquecer de apagar a fonte do dia anterior | Podcast mistura dois dias |

## Custo

- **Implementação:** ~1-2h (1 composable + 1 botão)
- **Tokens LLM:** zero (frontend puro)
- **NotebookLM:** você já paga; o "criar podcast" está incluído
- **Diário:** ~30s de trabalho manual seu

## Limitação conhecida + alternativa

O passo manual existe porque o NotebookLM consumidor não tem API. Se um dia
quiser **áudio 100% automático** (sem passo manual), o caminho é OUTRO: a
**Gemini API tem TTS nativo multi-locutor** (2 vozes, PT-BR, tags de emoção) —
dá pra gerar o podcast dentro do próprio pipeline e só "apertar play". Custo
estimado ~$5-50/mês dependendo do modelo e batch. Ver protótipo separado se
for o caso. Trade-off: mais engenharia + custo mensal, em troca de zero passo
manual e controle total do tom.

## Commit de referência

cardiology-agent — `feat(audio): botão Copiar briefing para NotebookLM`

## Manuais irmãos

- `docs/manuais/modo-leitura-mobile-manual.md`
- `docs/manuais/links-ios-chrome-manual.md`
- `docs/manuais/modo-pesquisa-historico-manual.md`
- `docs/manuais/modo-compacto-cards-manual.md`
