# Módulo Estudo (Aprofundamento) — Plano de Implementação

> **Para workers agênticos:** SUB-SKILL OBRIGATÓRIA: usar superpowers:subagent-driven-development (recomendado) ou superpowers:executing-plans para implementar tarefa a tarefa. Os passos usam checkbox (`- [ ]`).

**Goal:** Dropar um PDF (revisão/diretriz) numa pasta → GitHub Actions → Opus 4.8 gera material de estudo PT de duas camadas → aba "Estudo" navegável por mês no site.

**Architecture:** Backend Python (extração de PDF via PyMuPDF + chamada Claude streaming + escrita de markdown/figuras/index) disparado por workflow do GitHub Actions ao dar push de PDF em `study-inbox/`. Frontend Vue 3 (composable singleton espelhando `useMonthlyReviews` + componente de leitura que renderiza markdown).

**Tech Stack:** Python 3.11, anthropic SDK 0.42.0 (`messages.stream` + `get_final_message`), PyMuPDF (pymupdf), pytest; Vue 3 + Vite + Tailwind, vitest, marked + dompurify; GitHub Actions; Vercel.

## Global Constraints

- **Modelo:** `claude-opus-4-8` por padrão, lido de `STUDY_MODEL` (env), trocável sem editar código. Chamada via `client.messages.stream(...)` + `stream.get_final_message()` (padrão provado do repo em `agent/agent.py:228`); **sem** params `thinking`/`output_config`/`temperature` (não usados no repo nesta versão do SDK).
- **Nada inventado:** links de referência só de DOI/PMID presentes no texto, ou link de busca PubMed montado da citação. Nunca fabricar DOI/URL.
- **Defensivo:** falha num PDF loga e segue; nunca derruba o workflow nem gera estudo vazio silencioso.
- **PT-BR** em toda saída de estudo; voz técnica.
- **Idioma do código/commits:** seguir o repo (mensagens de commit sem acento, como o histórico).
- **Chave Claude:** `ANTHROPIC_API_KEY` (a mesma do pipeline diário).
- **Caminhos de dados:** estudos em `data/estudos/<slug>/` (`estudo.md`, `meta.json`, `fig-N.png`); biblioteca em `data/estudos/index.json`.
- **Raw GitHub base:** `https://raw.githubusercontent.com/muriloffs/cardiology-agent/main/` (padrão de `useXImages.js`).

---

## Estrutura de arquivos

**Backend (criar):**
- `agent/scripts/study_index.py` — helpers puros: `slugify`, `build_index`, `linkify_references`.
- `agent/scripts/study_pdf.py` — `extract_figures` (PyMuPDF).
- `agent/scripts/process_study.py` — orquestração: lê PDFs de `study-inbox/`, chama Claude, parseia, escreve arquivos, atualiza index. Entrypoint `python -m agent.scripts.process_study`.
- `agent/prompts/study_prompt.txt` — prompt de geração.
- `agent/tests/test_study_index.py`, `agent/tests/test_study_pdf.py`, `agent/tests/test_process_study.py` — testes.

**Backend (modificar):**
- `agent/requirements.txt` — adicionar `pymupdf`.
- `.gitignore` — garantir rastreamento de `data/estudos/`.

**Infra (criar):**
- `.github/workflows/study-process.yml` — gatilho por push em `study-inbox/**.pdf` + manual.
- `processar.bat` — atalho de commit+push (raiz do projeto).
- `study-inbox/.gitkeep` — cria a pasta.

**Frontend (criar):**
- `frontend/src/composables/useMonthlyStudies.js` — acumulador navegável por mês (espelha `useMonthlyReviews.js`).
- `frontend/src/components/StudyReader.vue` — modo leitura (renderiza markdown).
- `frontend/src/composables/__tests__/useMonthlyStudies.spec.js`, `frontend/src/components/__tests__/StudyReader.spec.js`.

**Frontend (modificar):**
- `frontend/package.json` — adicionar `marked`, `dompurify`.
- `frontend/src/App.vue` — aba "📚 Estudo" + biblioteca + navegação de mês.

---

### Task 1: Helpers puros de índice e referências (`study_index.py`)

**Files:**
- Create: `agent/scripts/study_index.py`
- Test: `agent/tests/test_study_index.py`

**Interfaces:**
- Produces:
  - `slugify(titulo: str) -> str` — kebab-case sem acento, só `[a-z0-9-]`.
  - `build_index(estudos_dir: Path) -> dict` — varre `<estudos_dir>/*/meta.json`, retorna `{"gerado_em": iso, "por_mes": {ym: [meta...]}, "meses_disponiveis": [ym...]}`. Itens de cada mês ordenados por `data` desc; `meses_disponiveis` desc.
  - `linkify_references(markdown: str) -> str` — converte `DOI: 10.x/y` → `[10.x/y](https://doi.org/10.x/y)`, `PMID: 12345` → `[PMID 12345](https://pubmed.ncbi.nlm.nih.gov/12345/)`, e em linhas de referência numeradas (`^\d+\.`) sem DOI/PMID anexa ` — [buscar](https://pubmed.ncbi.nlm.nih.gov/?term=<10 primeiras palavras url-encoded>)`.

- [ ] **Step 1: Escrever os testes que falham**

```python
# agent/tests/test_study_index.py
import json
from pathlib import Path
from agent.scripts.study_index import slugify, build_index, linkify_references


def test_slugify_strips_accents_and_punctuation():
    assert slugify("Insuficiência Cardíaca: FE preservada (HFpEF)") == "insuficiencia-cardiaca-fe-preservada-hfpef"


def test_slugify_collapses_and_trims_hyphens():
    assert slugify("  A  --  B  ") == "a-b"


def test_build_index_groups_by_month(tmp_path):
    for slug, data, mes in [("a", "2026-06-24", "2026-06"),
                            ("b", "2026-06-10", "2026-06"),
                            ("c", "2026-05-30", "2026-05")]:
        d = tmp_path / slug
        d.mkdir()
        (d / "meta.json").write_text(json.dumps(
            {"slug": slug, "titulo": slug.upper(), "fonte": "@NEJM",
             "tipo": "revisao", "data": data, "mes": mes}), encoding="utf-8")
    idx = build_index(tmp_path)
    assert idx["meses_disponiveis"] == ["2026-06", "2026-05"]
    assert [m["slug"] for m in idx["por_mes"]["2026-06"]] == ["a", "b"]  # data desc
    assert idx["por_mes"]["2026-05"][0]["slug"] == "c"


def test_build_index_empty_dir(tmp_path):
    idx = build_index(tmp_path)
    assert idx["por_mes"] == {}
    assert idx["meses_disponiveis"] == []


def test_linkify_doi_inline():
    out = linkify_references("Pfeffer MA et al. DOI: 10.1056/NEJMoa1409077")
    assert "[10.1056/NEJMoa1409077](https://doi.org/10.1056/NEJMoa1409077)" in out


def test_linkify_pmid():
    out = linkify_references("Smith J. PMID: 31535829")
    assert "[PMID 31535829](https://pubmed.ncbi.nlm.nih.gov/31535829/)" in out


def test_linkify_plain_numbered_ref_gets_search_link():
    out = linkify_references("12. Doe J. Heart Failure Review. Circulation 2020")
    assert "pubmed.ncbi.nlm.nih.gov/?term=" in out


def test_linkify_leaves_prose_without_refs_untouched():
    txt = "A HFpEF representa metade dos casos."
    assert linkify_references(txt) == txt
```

- [ ] **Step 2: Rodar os testes e confirmar que falham**

Run: `cd "/c/Users/totor/Downloads/claude code" && python -m pytest agent/tests/test_study_index.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'agent.scripts.study_index'`

- [ ] **Step 3: Implementar `study_index.py`**

```python
# agent/scripts/study_index.py
"""Helpers puros do módulo Estudo: slug, índice por mês, linkificação de referências."""
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus

_DOI_RE = re.compile(r"\b[Dd][Oo][Ii]:\s*(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)")
_PMID_RE = re.compile(r"\bPMID:\s*(\d+)")
_NUMBERED_REF_RE = re.compile(r"^\s*\d+\.\s+\S")


def slugify(titulo: str) -> str:
    nfkd = unicodedata.normalize("NFKD", titulo or "")
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii").lower()
    kebab = re.sub(r"[^a-z0-9]+", "-", ascii_str)
    return kebab.strip("-")


def linkify_references(markdown: str) -> str:
    def _doi(m):
        d = m.group(1)
        return f"[{d}](https://doi.org/{d})"

    def _pmid(m):
        p = m.group(1)
        return f"[PMID {p}](https://pubmed.ncbi.nlm.nih.gov/{p}/)"

    out_lines = []
    for line in markdown.splitlines():
        had_id = bool(_DOI_RE.search(line) or _PMID_RE.search(line))
        line = _DOI_RE.sub(_doi, line)
        line = _PMID_RE.sub(_pmid, line)
        if _NUMBERED_REF_RE.match(line) and not had_id:
            termos = " ".join(line.split()[1:11])
            line = f"{line} — [buscar](https://pubmed.ncbi.nlm.nih.gov/?term={quote_plus(termos)})"
        out_lines.append(line)
    return "\n".join(out_lines)


def build_index(estudos_dir: Path) -> dict:
    por_mes: dict[str, list] = {}
    if estudos_dir.exists():
        for meta_path in sorted(estudos_dir.glob("*/meta.json")):
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            ym = meta.get("mes") or (meta.get("data", "")[:7])
            if not ym:
                continue
            por_mes.setdefault(ym, []).append({
                "slug": meta.get("slug", ""),
                "titulo": meta.get("titulo", ""),
                "fonte": meta.get("fonte", ""),
                "tipo": meta.get("tipo", ""),
                "data": meta.get("data", ""),
            })
    for ym in por_mes:
        por_mes[ym].sort(key=lambda m: m.get("data", ""), reverse=True)
    meses = sorted(por_mes.keys(), reverse=True)
    return {
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "por_mes": por_mes,
        "meses_disponiveis": meses,
    }
```

- [ ] **Step 4: Rodar os testes e confirmar que passam**

Run: `python -m pytest agent/tests/test_study_index.py -v`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add agent/scripts/study_index.py agent/tests/test_study_index.py
git commit -m "feat(estudo): helpers de slug, indice por mes e linkificacao de referencias"
```

---

### Task 2: Extração de figuras do PDF (`study_pdf.py`)

**Files:**
- Create: `agent/scripts/study_pdf.py`
- Modify: `agent/requirements.txt`
- Test: `agent/tests/test_study_pdf.py`

**Interfaces:**
- Consumes: nada de tarefas anteriores.
- Produces:
  - `extract_figures(pdf_path: Path, out_dir: Path) -> list[dict]` — extrai imagens raster embutidas para `out_dir/fig-N.png`; retorna `[{"id": "fig-1", "arquivo": "fig-1.png", "pagina": int}]`. Defensivo: qualquer erro num item é pulado, nunca levanta.
  - `render_page(pdf_path: Path, page_index: int, out_path: Path) -> bool` — renderiza uma página inteira como PNG (fallback para tabela vetorial). Retorna True se gravou.

- [ ] **Step 1: Adicionar dependência**

Em `agent/requirements.txt`, acrescentar ao final:
```
pymupdf==1.24.10
```
Instalar: `pip install pymupdf==1.24.10`

- [ ] **Step 2: Escrever os testes que falham**

```python
# agent/tests/test_study_pdf.py
import fitz  # pymupdf
from pathlib import Path
from agent.scripts.study_pdf import extract_figures, render_page


def _make_pdf_with_image(path: Path):
    doc = fitz.open()
    page = doc.new_page()
    # Um pixmap vermelho 32x32 embutido como imagem na página
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 32, 32))
    pix.set_rect(pix.irect, (255, 0, 0))
    page.insert_image(fitz.Rect(10, 10, 110, 110), pixmap=pix)
    doc.save(str(path))
    doc.close()


def test_extract_figures_returns_raster_images(tmp_path):
    pdf = tmp_path / "doc.pdf"
    _make_pdf_with_image(pdf)
    out = tmp_path / "figs"
    out.mkdir()
    figs = extract_figures(pdf, out)
    assert len(figs) >= 1
    assert figs[0]["id"] == "fig-1"
    assert (out / figs[0]["arquivo"]).exists()


def test_extract_figures_empty_pdf(tmp_path):
    pdf = tmp_path / "empty.pdf"
    doc = fitz.open(); doc.new_page(); doc.save(str(pdf)); doc.close()
    out = tmp_path / "figs"; out.mkdir()
    assert extract_figures(pdf, out) == []


def test_render_page_writes_png(tmp_path):
    pdf = tmp_path / "doc.pdf"
    _make_pdf_with_image(pdf)
    target = tmp_path / "page.png"
    assert render_page(pdf, 0, target) is True
    assert target.exists() and target.stat().st_size > 0
```

- [ ] **Step 3: Rodar os testes e confirmar que falham**

Run: `python -m pytest agent/tests/test_study_pdf.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'agent.scripts.study_pdf'`

- [ ] **Step 4: Implementar `study_pdf.py`**

```python
# agent/scripts/study_pdf.py
"""Extracao de figuras de PDF para o modulo Estudo (PyMuPDF).

Defensivo: erros em itens individuais sao logados e pulados, nunca levantam.
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_figures(pdf_path: Path, out_dir: Path) -> list[dict]:
    import fitz
    out_dir.mkdir(parents=True, exist_ok=True)
    figs: list[dict] = []
    n = 0
    try:
        doc = fitz.open(str(pdf_path))
    except Exception as e:
        logger.error(f"Falha ao abrir PDF {pdf_path}: {e}")
        return []
    try:
        for page_index in range(len(doc)):
            try:
                page = doc[page_index]
                for img in page.get_images(full=True):
                    xref = img[0]
                    try:
                        pix = fitz.Pixmap(doc, xref)
                        if pix.n - pix.alpha >= 4:  # CMYK/outros -> RGB
                            pix = fitz.Pixmap(fitz.csRGB, pix)
                        n += 1
                        nome = f"fig-{n}.png"
                        pix.save(str(out_dir / nome))
                        figs.append({"id": f"fig-{n}", "arquivo": nome, "pagina": page_index + 1})
                    except Exception as e:
                        logger.warning(f"Pulando imagem xref={xref} na pag {page_index+1}: {e}")
            except Exception as e:
                logger.warning(f"Pulando pagina {page_index}: {e}")
    finally:
        doc.close()
    return figs


def render_page(pdf_path: Path, page_index: int, out_path: Path) -> bool:
    import fitz
    try:
        doc = fitz.open(str(pdf_path))
        try:
            page = doc[page_index]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x para legibilidade
            out_path.parent.mkdir(parents=True, exist_ok=True)
            pix.save(str(out_path))
            return True
        finally:
            doc.close()
    except Exception as e:
        logger.error(f"Falha ao renderizar pagina {page_index} de {pdf_path}: {e}")
        return False
```

- [ ] **Step 5: Rodar os testes e confirmar que passam**

Run: `python -m pytest agent/tests/test_study_pdf.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
git add agent/scripts/study_pdf.py agent/tests/test_study_pdf.py agent/requirements.txt
git commit -m "feat(estudo): extracao de figuras de PDF via PyMuPDF (com fallback de pagina)"
```

---

### Task 3: Prompt + orquestração (`process_study.py`)

**Files:**
- Create: `agent/prompts/study_prompt.txt`, `agent/scripts/process_study.py`
- Test: `agent/tests/test_process_study.py`

**Interfaces:**
- Consumes: `study_index.slugify`, `study_index.build_index`, `study_index.linkify_references`, `study_pdf.extract_figures`.
- Produces:
  - `parse_study_output(raw: str) -> dict` — recorta o JSON da resposta do modelo (com `json_repair` de fallback); retorna `{"titulo","fonte","tipo","data","markdown"}` ou levanta `ValueError` se irreparável.
  - `write_study(estudos_dir: Path, parsed: dict, figs: list[dict]) -> str` — cria `<estudos_dir>/<slug>/` com `estudo.md` (markdown linkificado) + `meta.json`; retorna o slug. (Figuras já estão na pasta, movidas/geradas pelo caller.)
  - `process_one(pdf_path, estudos_dir, model) -> str|None` — pipeline de um PDF (extrai figuras, chama Claude, parseia, escreve). Retorna slug ou None em falha.
  - `main()` — varre `study-inbox/*.pdf`, processa cada um, reconstrói `index.json`, move PDFs processados para `study-inbox/processados/`.

- [ ] **Step 1: Escrever o prompt**

```text
# agent/prompts/study_prompt.txt
Você é um especialista em cardiologia que transforma um artigo científico (revisão, diretriz ou recomendação) em MATERIAL DE ESTUDO em português brasileiro, para um cardiologista que quer DOMINAR o conteúdo.

O PDF do artigo está anexado. Produza um documento de ESTUDO, não um resumo raso.

REGRAS DE CONTEÚDO:
- PROPORÇÃO: condense para ~30–45% do tamanho do original. A saída escala com a fonte (artigo curto → documento curto; diretriz longa → documento longo). NÃO há tamanho fixo.
- COBERTURA: percorra o artigo SEÇÃO POR SEÇÃO. Preserve TODO conceito, definição, recomendação e resultado numérico. Corte só redundância, metodologia verbosa e repetição. Nada de pular seções.
- VOZ TÉCNICA, tradução fiel para PT-BR, leitura de aprendizado.
- NÃO INVENTE NADA. Todo conteúdo vem do artigo.

DUAS CAMADAS (importante para a apresentação):
1. TEXTO FIEL (o artigo falando): markdown normal — parágrafos, headings de seção (## Nome da Seção), tabelas.
2. CAMADA DE ESTUDO (o tutor falando): blocos destacados, SEMPRE no formato exato:
   > 🎓 **Aprofunde:** <comentário que chama atenção para o conceito-chave, define termos, diz o que dominar>
   Use a camada de estudo para destacar conceitos-chave e, quando referenciar, cite a referência da BIBLIOGRAFIA DO PRÓPRIO ARTIGO.

TABELAS / ALGORITMOS / FLUXOGRAMAS:
- Reconstrua o conteúdo em PT como tabela markdown / passos numerados (ex: tabela de recomendações Classe I/IIa com colunas Recomendação | Classe | Nível).
- Onde houver figura/tabela relevante, deixe um marcador `[[FIGURA: descrição em PT]]` na posição — as imagens serão inseridas depois.

REFERÊNCIAS (anti-invenção):
- Quando citar uma referência, use a entrada EXATA da bibliografia do artigo.
- Se a referência tiver DOI no artigo, escreva `DOI: <doi>` literal. Se tiver PMID, escreva `PMID: <pmid>` literal. NUNCA invente um DOI/PMID.
- Termine com uma seção `## Referências citadas` listando, numeradas, só as referências que você citou (com DOI:/PMID: quando presentes no artigo).

FORMATO DE SAÍDA — retorne APENAS um objeto JSON (sem markdown em volta):
{
  "titulo": "título do artigo em PT",
  "fonte": "journal/sociedade (ex: NEJM, ESC)",
  "tipo": "revisao | diretriz | recomendacao",
  "data": "AAAA-MM-DD da publicação se constar, senão a data de hoje",
  "markdown": "o documento de estudo completo em markdown, com as duas camadas"
}
```

- [ ] **Step 2: Escrever os testes que falham**

```python
# agent/tests/test_process_study.py
import json
from pathlib import Path
from agent.scripts.process_study import parse_study_output, write_study


def test_parse_study_output_extracts_json():
    raw = 'Aqui está:\n{"titulo":"IC","fonte":"NEJM","tipo":"revisao","data":"2026-06-24","markdown":"# IC\\nTexto"}\nfim'
    out = parse_study_output(raw)
    assert out["titulo"] == "IC"
    assert out["markdown"].startswith("# IC")


def test_parse_study_output_repairs_trailing_comma():
    raw = '{"titulo":"A","fonte":"ESC","tipo":"diretriz","data":"2026-06-01","markdown":"x",}'
    out = parse_study_output(raw)
    assert out["tipo"] == "diretriz"


def test_parse_study_output_raises_on_garbage():
    import pytest
    with pytest.raises(ValueError):
        parse_study_output("sem json aqui")


def test_write_study_creates_files_and_linkifies(tmp_path):
    parsed = {
        "titulo": "Insuficiência Cardíaca",
        "fonte": "@NEJM",
        "tipo": "revisao",
        "data": "2026-06-24",
        "markdown": "## Intro\nTexto.\n\n## Referências citadas\n1. Pfeffer MA. DOI: 10.1056/NEJMoa1409077",
    }
    slug = write_study(tmp_path, parsed, figs=[])
    assert slug == "insuficiencia-cardiaca-2026-06-24"
    estudo_md = (tmp_path / slug / "estudo.md").read_text(encoding="utf-8")
    assert "[10.1056/NEJMoa1409077](https://doi.org/10.1056/NEJMoa1409077)" in estudo_md
    meta = json.loads((tmp_path / slug / "meta.json").read_text(encoding="utf-8"))
    assert meta["mes"] == "2026-06" and meta["slug"] == slug


def test_write_study_replaces_figure_markers(tmp_path):
    parsed = {
        "titulo": "T", "fonte": "ESC", "tipo": "diretriz", "data": "2026-06-01",
        "markdown": "Veja [[FIGURA: forest plot de MACE]] no estudo.",
    }
    figs = [{"id": "fig-1", "arquivo": "fig-1.png", "pagina": 3}]
    slug = write_study(tmp_path, parsed, figs=figs)
    md = (tmp_path / slug / "estudo.md").read_text(encoding="utf-8")
    assert "![forest plot de MACE](fig-1.png)" in md
    assert "[[FIGURA" not in md
```

- [ ] **Step 3: Rodar os testes e confirmar que falham**

Run: `python -m pytest agent/tests/test_process_study.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'agent.scripts.process_study'`

- [ ] **Step 4: Implementar `process_study.py`**

```python
# agent/scripts/process_study.py
"""Modulo Estudo: processa PDFs de study-inbox/ em material de estudo PT.

Roda no GitHub Actions ao dar push de PDF em study-inbox/. Defensivo:
falha num PDF loga e segue; nunca derruba o run.

Env:
  ANTHROPIC_API_KEY  — obrigatorio
  STUDY_MODEL        — default 'claude-opus-4-8'
"""
import base64
import json
import logging
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from agent.scripts.study_index import slugify, build_index, linkify_references
from agent.scripts.study_pdf import extract_figures

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent.parent
INBOX = ROOT / "study-inbox"
ESTUDOS_DIR = ROOT / "data" / "estudos"
PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "study_prompt.txt"
STUDY_MODEL = os.environ.get("STUDY_MODEL", "claude-opus-4-8")
_FIG_MARKER_RE = re.compile(r"\[\[FIGURA:\s*(.*?)\]\]")


def parse_study_output(raw: str) -> dict:
    txt = (raw or "").strip()
    a, b = txt.find("{"), txt.rfind("}")
    if a != -1 and b != -1:
        txt = txt[a:b + 1]
    try:
        obj = json.loads(txt)
    except json.JSONDecodeError:
        try:
            from json_repair import repair_json
            obj = json.loads(repair_json(txt))
        except Exception as e:
            raise ValueError(f"JSON irreparavel do modelo: {e}")
    if not isinstance(obj, dict) or "markdown" not in obj:
        raise ValueError("Resposta do modelo sem campo markdown")
    return obj


def _call_claude(pdf_bytes: bytes, model: str) -> str:
    from anthropic import Anthropic
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], max_retries=5)
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    b64 = base64.standard_b64encode(pdf_bytes).decode("ascii")
    content = [
        {"type": "document",
         "source": {"type": "base64", "media_type": "application/pdf", "data": b64}},
        {"type": "text", "text": prompt},
    ]
    with client.messages.stream(
        model=model,
        max_tokens=32000,
        messages=[{"role": "user", "content": content}],
    ) as stream:
        response = stream.get_final_message()
    return response.content[0].text


def write_study(estudos_dir: Path, parsed: dict, figs: list[dict]) -> str:
    data = parsed.get("data") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slug = f"{slugify(parsed.get('titulo', 'estudo'))}-{data}"
    out = estudos_dir / slug
    out.mkdir(parents=True, exist_ok=True)

    markdown = parsed["markdown"]
    # Substitui marcadores [[FIGURA: desc]] pela proxima figura disponivel
    fig_iter = iter(figs)

    def _sub(m):
        desc = m.group(1).strip()
        try:
            f = next(fig_iter)
            return f"![{desc}]({f['arquivo']})"
        except StopIteration:
            return f"_(figura: {desc} — ver original)_"

    markdown = _FIG_MARKER_RE.sub(_sub, markdown)
    markdown = linkify_references(markdown)
    (out / "estudo.md").write_text(markdown, encoding="utf-8")

    meta = {
        "slug": slug,
        "titulo": parsed.get("titulo", ""),
        "fonte": parsed.get("fonte", ""),
        "tipo": parsed.get("tipo", ""),
        "data": data,
        "mes": data[:7],
    }
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return slug


def process_one(pdf_path: Path, estudos_dir: Path, model: str) -> str | None:
    try:
        logger.info(f"Processando {pdf_path.name}")
        tmp_figs = estudos_dir / "_tmp_figs"
        if tmp_figs.exists():
            shutil.rmtree(tmp_figs)
        figs = extract_figures(pdf_path, tmp_figs)
        raw = _call_claude(pdf_path.read_bytes(), model)
        parsed = parse_study_output(raw)
        slug = write_study(estudos_dir, parsed, figs)
        # Move figuras para a pasta final do estudo
        for f in figs:
            src = tmp_figs / f["arquivo"]
            if src.exists():
                shutil.move(str(src), str(estudos_dir / slug / f["arquivo"]))
        if tmp_figs.exists():
            shutil.rmtree(tmp_figs)
        logger.info(f"OK: {slug} ({len(figs)} figuras)")
        return slug
    except Exception as e:
        logger.error(f"Falha ao processar {pdf_path.name}: {e}")
        return None


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        logger.error("ANTHROPIC_API_KEY nao setada — abortando.")
        return
    ESTUDOS_DIR.mkdir(parents=True, exist_ok=True)
    processados_dir = INBOX / "processados"
    processados_dir.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(p for p in INBOX.glob("*.pdf"))
    if not pdfs:
        logger.info("Nenhum PDF em study-inbox/ — nada a fazer.")
        return

    for pdf in pdfs:
        slug = process_one(pdf, ESTUDOS_DIR, STUDY_MODEL)
        if slug:
            shutil.move(str(pdf), str(processados_dir / pdf.name))

    index = build_index(ESTUDOS_DIR)
    (ESTUDOS_DIR / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"Index atualizado: {len(index['meses_disponiveis'])} meses")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Rodar os testes e confirmar que passam**

Run: `python -m pytest agent/tests/test_process_study.py -v`
Expected: PASS (5 passed)

- [ ] **Step 6: Commit**

```bash
git add agent/prompts/study_prompt.txt agent/scripts/process_study.py agent/tests/test_process_study.py
git commit -m "feat(estudo): prompt + orquestracao de processamento de PDF para material de estudo"
```

---

### Task 4: Pasta de entrada, gitignore, workflow e atalho de envio

**Files:**
- Create: `study-inbox/.gitkeep`, `.github/workflows/study-process.yml`, `processar.bat`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `python -m agent.scripts.process_study` (Task 3).
- Produces: gatilho automático no push de PDF; nada consumido por tarefas posteriores.

- [ ] **Step 1: Criar a pasta de entrada**

```bash
mkdir -p "study-inbox"
printf '' > "study-inbox/.gitkeep"
```

- [ ] **Step 2: Garantir rastreamento de `data/estudos/` no `.gitignore`**

Acrescentar ao final do `.gitignore` (logo após as exceções de `data/` existentes):
```
# Modulo Estudo: rastrear o conteudo gerado em data/estudos/
!data/estudos/
!data/estudos/**
```

- [ ] **Step 3: Verificar que os arquivos do estudo NÃO ficam ignorados**

Run:
```bash
mkdir -p data/estudos/teste && echo "x" > data/estudos/teste/estudo.md
git check-ignore data/estudos/teste/estudo.md data/estudos/index.json; echo "exit=$?"
```
Expected: nenhuma linha impressa e `exit=1` (nada ignorado). Depois limpar: `rm -rf data/estudos/teste`.

- [ ] **Step 4: Criar o workflow**

```yaml
# .github/workflows/study-process.yml
name: Process Study PDFs

on:
  push:
    paths:
      - 'study-inbox/**.pdf'
  workflow_dispatch:

concurrency:
  group: study-process
  cancel-in-progress: false

jobs:
  process:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    permissions:
      contents: write

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 1

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install --default-timeout=30 -r agent/requirements.txt

      - name: Process study PDFs
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          STUDY_MODEL: ${{ vars.STUDY_MODEL || 'claude-opus-4-8' }}
        run: python -m agent.scripts.process_study

      - name: Configure Git
        run: |
          git config --local user.email "github-actions[bot]@users.noreply.github.com"
          git config --local user.name "github-actions[bot]"

      - name: Commit results
        run: |
          git add data/estudos study-inbox || true
          git commit -m "chore: processa estudos de study-inbox $(date -u +%Y-%m-%d)" || echo "Nothing to commit"
          git pull --rebase origin main
          git push origin main
```

- [ ] **Step 5: Criar o atalho de envio (Windows)**

```bat
@echo off
REM processar.bat — envia os PDFs de study-inbox/ para processamento na nuvem.
cd /d "%~dp0"
git add study-inbox
git commit -m "chore: novos PDFs para estudo"
git pull --rebase origin main
git push origin main
echo.
echo Enviado. O GitHub Actions vai processar e o resultado aparece na aba Estudo.
pause
```

- [ ] **Step 6: Commit**

```bash
git add .gitignore study-inbox/.gitkeep .github/workflows/study-process.yml processar.bat
git commit -m "feat(estudo): pasta study-inbox, workflow de processamento e atalho processar.bat"
```

---

### Task 5: Composable de estudos por mês (`useMonthlyStudies.js`)

**Files:**
- Create: `frontend/src/composables/useMonthlyStudies.js`, `frontend/src/composables/__tests__/useMonthlyStudies.spec.js`

**Interfaces:**
- Consumes: `data/estudos/index.json` (estrutura `{por_mes, meses_disponiveis}` da Task 3) via GitHub raw.
- Produces: `useMonthlyStudies()` retornando `{ loading, loadError, items, selectedMonth, availableMonths, monthLabelText, canOlder, canNewer, olderMonth, newerMonth, open }`. `items` = lista de estudos do mês selecionado.

- [ ] **Step 1: Escrever o teste que falha**

```javascript
// frontend/src/composables/__tests__/useMonthlyStudies.spec.js
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useMonthlyStudies } from '../useMonthlyStudies'

const INDEX = {
  por_mes: {
    '2026-06': [{ slug: 'a-2026-06-24', titulo: 'A', fonte: '@NEJM', tipo: 'revisao', data: '2026-06-24' }],
    '2026-05': [{ slug: 'b-2026-05-10', titulo: 'B', fonte: '@ESC', tipo: 'diretriz', data: '2026-05-10' }],
  },
  meses_disponiveis: ['2026-06', '2026-05'],
}

describe('useMonthlyStudies', () => {
  beforeEach(() => {
    global.fetch = vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve(INDEX) }))
  })

  it('abre no mes mais recente e lista seus estudos', async () => {
    const s = useMonthlyStudies()
    await s.open()
    expect(s.selectedMonth.value).toBe('2026-06')
    expect(s.items.value.map((i) => i.slug)).toEqual(['a-2026-06-24'])
  })

  it('navega para o mes anterior', async () => {
    const s = useMonthlyStudies()
    await s.open()
    expect(s.canOlder.value).toBe(true)
    await s.olderMonth()
    expect(s.selectedMonth.value).toBe('2026-05')
    expect(s.items.value[0].slug).toBe('b-2026-05-10')
    expect(s.canNewer.value).toBe(true)
  })
})
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `cd "/c/Users/totor/Downloads/claude code/frontend" && npx vitest run src/composables/__tests__/useMonthlyStudies.spec.js`
Expected: FAIL (módulo inexistente)

- [ ] **Step 3: Implementar `useMonthlyStudies.js`**

```javascript
// frontend/src/composables/useMonthlyStudies.js
/**
 * "Estudo do Mês" — biblioteca de materiais de estudo navegável por mês.
 * Espelha useMonthlyReviews: abre no mês atual, volta para meses anteriores.
 * O index.json já vem agrupado por mês (por_mes/meses_disponiveis). Singleton.
 */
import { ref, computed } from 'vue'

const GITHUB_RAW = 'https://raw.githubusercontent.com/muriloffs/cardiology-agent/main/data/estudos/index.json'

function monthLabel(ym) {
  if (!ym) return ''
  try {
    const [y, m] = ym.split('-').map(Number)
    const nome = new Date(y, m - 1, 1).toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' })
    return nome.charAt(0).toUpperCase() + nome.slice(1)
  } catch {
    return ym
  }
}

function currentYM() {
  const n = new Date()
  return n.getFullYear() + '-' + String(n.getMonth() + 1).padStart(2, '0')
}

// Estado singleton
const index = ref(null)            // { por_mes, meses_disponiveis }
const indexLoaded = ref(false)
const selectedMonth = ref('')
const loading = ref(false)
const loadError = ref(null)

async function ensureIndex(force = false) {
  if (indexLoaded.value && !force) return
  loading.value = true
  loadError.value = null
  try {
    const resp = await fetch(`${GITHUB_RAW}?t=${Date.now()}`)
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    index.value = await resp.json()
    indexLoaded.value = true
  } catch (e) {
    loadError.value = e?.message || 'Falha ao carregar índice de estudos'
    index.value = { por_mes: {}, meses_disponiveis: [] }
    console.error('useMonthlyStudies load failed:', e)
  } finally {
    loading.value = false
  }
}

async function open() {
  await ensureIndex()
  const months = index.value?.meses_disponiveis || []
  const ym = currentYM()
  selectedMonth.value = months.includes(ym) ? ym : (months[0] || ym)
}

function goToMonth(ym) {
  if (ym) selectedMonth.value = ym
}

export function useMonthlyStudies() {
  const availableMonths = computed(() => index.value?.meses_disponiveis || [])
  const items = computed(() => (index.value?.por_mes || {})[selectedMonth.value] || [])
  const monthIndex = computed(() => availableMonths.value.indexOf(selectedMonth.value))
  const canOlder = computed(() => monthIndex.value >= 0 && monthIndex.value < availableMonths.value.length - 1)
  const canNewer = computed(() => monthIndex.value > 0)
  function olderMonth() {
    if (canOlder.value) goToMonth(availableMonths.value[monthIndex.value + 1])
  }
  function newerMonth() {
    if (canNewer.value) goToMonth(availableMonths.value[monthIndex.value - 1])
  }
  return {
    loading,
    loadError,
    items,
    selectedMonth,
    availableMonths,
    monthLabelText: computed(() => monthLabel(selectedMonth.value)),
    canOlder,
    canNewer,
    olderMonth,
    newerMonth,
    goToMonth,
    open,
  }
}
```

- [ ] **Step 4: Rodar o teste e confirmar que passa**

Run: `npx vitest run src/composables/__tests__/useMonthlyStudies.spec.js`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/composables/useMonthlyStudies.js frontend/src/composables/__tests__/useMonthlyStudies.spec.js
git commit -m "feat(estudo): composable useMonthlyStudies (biblioteca navegavel por mes)"
```

---

### Task 6: Componente de leitura (`StudyReader.vue`)

**Files:**
- Modify: `frontend/package.json` (deps `marked`, `dompurify`)
- Create: `frontend/src/components/StudyReader.vue`, `frontend/src/components/__tests__/StudyReader.spec.js`

**Interfaces:**
- Consumes: `data/estudos/<slug>/estudo.md` (GitHub raw) e figuras `fig-N.png` na mesma pasta.
- Produces: função pura exportada `renderStudyMarkdown(md: string, baseUrl: string) -> string` (HTML sanitizado, com `<blockquote class="study-layer">` para blocos `> 🎓` e `src` de imagem reescrito para `baseUrl + arquivo`); componente `StudyReader` (prop `slug`).

- [ ] **Step 1: Instalar dependências**

```bash
cd "/c/Users/totor/Downloads/claude code/frontend"
npm install marked@12 dompurify@3
```

- [ ] **Step 2: Escrever o teste que falha**

```javascript
// frontend/src/components/__tests__/StudyReader.spec.js
import { describe, it, expect } from 'vitest'
import { renderStudyMarkdown } from '../StudyReader.vue'

const BASE = 'https://raw.example/data/estudos/a-2026-06-24/'

describe('renderStudyMarkdown', () => {
  it('marca a camada de estudo com classe distinta', () => {
    const html = renderStudyMarkdown('> 🎓 **Aprofunde:** rigidez ventricular', BASE)
    expect(html).toContain('class="study-layer"')
    expect(html).toContain('Aprofunde')
  })

  it('reescreve src de imagem relativa para a base raw', () => {
    const html = renderStudyMarkdown('![forest plot](fig-1.png)', BASE)
    expect(html).toContain(`src="${BASE}fig-1.png"`)
  })

  it('renderiza tabela e parágrafo normais', () => {
    const html = renderStudyMarkdown('## Intro\n\nTexto normal.', BASE)
    expect(html).toContain('<h2')
    expect(html).toContain('Texto normal')
  })
})
```

- [ ] **Step 3: Rodar o teste e confirmar que falha**

Run: `npx vitest run src/components/__tests__/StudyReader.spec.js`
Expected: FAIL (export inexistente)

- [ ] **Step 4: Implementar `StudyReader.vue`**

```vue
<script>
import { marked } from 'marked'
import DOMPurify from 'dompurify'

// Função pura (testável): markdown -> HTML sanitizado, com camada de estudo
// marcada e src de imagem reescrito para a base raw do estudo.
export function renderStudyMarkdown(md, baseUrl) {
  const renderer = new marked.Renderer()
  const baseBlockquote = renderer.blockquote.bind(renderer)
  renderer.blockquote = (quote) => {
    const html = baseBlockquote(quote)
    if (quote.includes('🎓')) {
      return html.replace('<blockquote>', '<blockquote class="study-layer">')
    }
    return html
  }
  const baseImage = renderer.image.bind(renderer)
  renderer.image = (href, title, text) => {
    const abs = /^https?:\/\//.test(href) ? href : baseUrl + href
    return baseImage(abs, title, text)
  }
  const raw = marked.parse(md || '', { renderer })
  return DOMPurify.sanitize(raw, { ADD_ATTR: ['class'] })
}
</script>

<script setup>
import { ref, watch, computed } from 'vue'

const props = defineProps({ slug: { type: String, required: true } })
const emit = defineEmits(['close'])

const RAW_BASE = 'https://raw.githubusercontent.com/muriloffs/cardiology-agent/main/data/estudos/'
const html = ref('')
const loading = ref(false)
const error = ref(null)
const baseUrl = computed(() => `${RAW_BASE}${props.slug}/`)

async function load() {
  loading.value = true
  error.value = null
  try {
    const resp = await fetch(`${baseUrl.value}estudo.md?t=${Date.now()}`)
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const md = await resp.text()
    html.value = renderStudyMarkdown(md, baseUrl.value)
  } catch (e) {
    error.value = e?.message || 'Falha ao carregar o estudo'
  } finally {
    loading.value = false
  }
}

watch(() => props.slug, load, { immediate: true })
</script>

<template>
  <div class="study-reader">
    <button class="study-close" @click="emit('close')">← Voltar</button>
    <div v-if="loading" class="study-status">Carregando…</div>
    <div v-else-if="error" class="study-status study-error">{{ error }}</div>
    <article v-else class="study-body" v-html="html"></article>
  </div>
</template>

<style scoped>
.study-reader { max-width: 760px; margin: 0 auto; padding: 1rem 1.25rem 4rem; }
.study-close { margin-bottom: 1rem; font-size: 0.95rem; color: #2563eb; background: none; border: none; cursor: pointer; }
.study-status { padding: 2rem 0; color: #6b7280; }
.study-error { color: #b91c1c; }
.study-body { line-height: 1.75; font-size: 1.05rem; color: #1f2937; }
.study-body :deep(h2) { margin-top: 2rem; font-size: 1.4rem; font-weight: 700; }
.study-body :deep(table) { border-collapse: collapse; width: 100%; margin: 1rem 0; }
.study-body :deep(th), .study-body :deep(td) { border: 1px solid #e5e7eb; padding: 0.5rem 0.75rem; text-align: left; }
.study-body :deep(img) { max-width: 100%; border-radius: 8px; margin: 1rem 0; }
.study-body :deep(.study-layer) {
  background: #f5f3ff; border-left: 4px solid #8b5cf6; border-radius: 8px;
  padding: 0.75rem 1rem; margin: 1.25rem 0; color: #4c1d95;
}
</style>
```

- [ ] **Step 5: Rodar o teste e confirmar que passa**

Run: `npx vitest run src/components/__tests__/StudyReader.spec.js`
Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/components/StudyReader.vue frontend/src/components/__tests__/StudyReader.spec.js
git commit -m "feat(estudo): StudyReader (markdown de duas camadas + figuras + links)"
```

---

### Task 7: Aba "Estudo" no `App.vue` (biblioteca + navegação de mês)

**Files:**
- Modify: `frontend/src/App.vue`

**Interfaces:**
- Consumes: `useMonthlyStudies()` (Task 5), `StudyReader` (Task 6).
- Produces: aba "📚 Estudo" com biblioteca do mês, navegação ◄ ►, e abertura do leitor.

- [ ] **Step 1: Localizar os pontos de inserção**

Run:
```bash
cd "/c/Users/totor/Downloads/claude code"
grep -n "openXImages\|🖼️ Imagens\|Revisões do Mês\|activeTab\|olderMonth\|import.*useXImages" frontend/src/App.vue | head -30
```
Expected: linhas mostrando o padrão de abas, o import dos composables, e o bloco de navegação ◄ ► da aba Revisões (a ser espelhado).

- [ ] **Step 2: Importar o composable e o leitor + estado de seleção**

No bloco `<script setup>` de `frontend/src/App.vue`, junto aos imports de composables/componentes existentes, adicionar:
```javascript
import StudyReader from './components/StudyReader.vue'
import { useMonthlyStudies } from './composables/useMonthlyStudies'

const studies = useMonthlyStudies()
const selectedStudySlug = ref(null)

async function openStudies() {
  activeTab.value = 'estudo'        // usar o mesmo mecanismo de aba do App
  selectedStudySlug.value = null
  await studies.open()
}
```
(Ajustar `activeTab.value = 'estudo'` ao mecanismo real de abas descoberto no Step 1 — se o app usa outro nome de variável/função para trocar de aba, seguir esse padrão.)

- [ ] **Step 3: Adicionar o botão da aba na navegação**

No `<template>`, ao lado do botão "🖼️ Imagens" (encontrado no Step 1), adicionar:
```html
<button :class="tabClass('estudo')" @click="openStudies">📚 Estudo</button>
```
(Usar a mesma classe/handler das outras abas, conforme o padrão real.)

- [ ] **Step 4: Adicionar o painel da aba**

No `<template>`, junto aos painéis das outras abas, adicionar o painel da aba estudo:
```html
<section v-if="activeTab === 'estudo'" class="estudo-tab">
  <!-- Leitor aberto -->
  <StudyReader
    v-if="selectedStudySlug"
    :slug="selectedStudySlug"
    @close="selectedStudySlug = null"
  />
  <!-- Biblioteca do mês -->
  <div v-else>
    <div class="month-nav">
      <button :disabled="!studies.canOlder.value" @click="studies.olderMonth">◄</button>
      <span class="month-label">{{ studies.monthLabelText.value }}</span>
      <button :disabled="!studies.canNewer.value" @click="studies.newerMonth">►</button>
    </div>

    <div v-if="studies.loading.value" class="estudo-status">Carregando…</div>
    <div v-else-if="studies.loadError.value" class="estudo-status">{{ studies.loadError.value }}</div>
    <div v-else-if="studies.items.value.length === 0" class="estudo-status">
      Nenhum estudo neste mês. Solte um PDF em <code>study-inbox/</code> e rode <code>processar.bat</code>.
    </div>
    <ul v-else class="estudo-lista">
      <li v-for="it in studies.items.value" :key="it.slug">
        <button class="estudo-item" @click="selectedStudySlug = it.slug">
          <span class="estudo-titulo">{{ it.titulo }}</span>
          <span class="estudo-meta">{{ it.fonte }} · {{ it.tipo }} · {{ it.data }}</span>
        </button>
      </li>
    </ul>
  </div>
</section>
```

- [ ] **Step 5: Adicionar estilos mínimos**

No `<style>` de `App.vue` (ou no escopo equivalente), adicionar:
```css
.month-nav { display: flex; align-items: center; justify-content: center; gap: 1rem; margin: 1rem 0; }
.month-nav button { background: #eef2ff; border: none; border-radius: 6px; padding: 0.3rem 0.7rem; cursor: pointer; }
.month-nav button:disabled { opacity: 0.4; cursor: default; }
.month-label { font-weight: 600; min-width: 12rem; text-align: center; }
.estudo-lista { list-style: none; padding: 0; max-width: 760px; margin: 0 auto; }
.estudo-item { display: flex; flex-direction: column; align-items: flex-start; width: 100%; text-align: left;
  background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 0.85rem 1rem; margin-bottom: 0.6rem; cursor: pointer; }
.estudo-titulo { font-weight: 600; color: #111827; }
.estudo-meta { font-size: 0.85rem; color: #6b7280; margin-top: 0.2rem; }
.estudo-status { text-align: center; color: #6b7280; padding: 2rem 0; }
```

- [ ] **Step 6: Build de verificação**

Run:
```bash
cd "/c/Users/totor/Downloads/claude code/frontend"
npx vitest run && npm run build
```
Expected: testes PASS e build sem erros.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/App.vue
git commit -m "feat(estudo): aba Estudo no App (biblioteca por mes + navegacao + leitor)"
```

---

## Verificação manual final (pós-implementação)

Itens que não dá para cobrir com teste unitário — verificar manualmente após implementar:

1. **Ponta a ponta:** colocar um PDF real de revisão em `study-inbox/`, rodar `python -m agent.scripts.process_study` localmente (com `ANTHROPIC_API_KEY` setada) e conferir `data/estudos/<slug>/estudo.md` + figuras + `index.json`.
2. **Workflow:** dar push de um PDF e confirmar que `study-process.yml` roda, comita o resultado e move o PDF para `study-inbox/processados/`.
3. **Frontend no ar:** abrir a aba Estudo no site, navegar entre meses, abrir um estudo e conferir a leitura (camada de estudo destacada, tabelas, figuras, links de referência clicáveis).
4. **Faixa de compressão:** avaliar se ~30–45% ficou no ponto; ajustar o número em `study_prompt.txt` se preciso (é o primeiro parâmetro a calibrar).

---

## Self-review (cobertura da spec)

- Entrada (drop + processar.bat) → Task 4 ✓
- Gatilho Actions (push + manual, idempotência por mover processados) → Task 4 + `main()` Task 3 ✓
- Motor Opus 4.8 passada única (PDF document block) → Task 3 ✓
- Proporção ~30–45% + cobertura seção a seção → `study_prompt.txt` Task 3 ✓
- Duas camadas (fiel + `> 🎓`) → prompt Task 3 + render Task 6 ✓
- Figuras: reconstrução PT + imagem (marcador `[[FIGURA]]` → `![]()`, extração + fallback `render_page`) → Tasks 2, 3 ✓
- Referências DOI/PMID direto vs busca, nunca fabricar → `linkify_references` Task 1 + prompt Task 3 ✓
- Armazenamento `data/estudos/<slug>/` + `index.json` por mês → Tasks 1, 3 ✓
- Apresentação: aba Estudo, navegação por mês igual Revisões, modo leitura → Tasks 5, 6, 7 ✓
- Modelo trocável por `STUDY_MODEL` → Task 3 + workflow Task 4 ✓
- Defensivo (nunca quebra) → `extract_figures`, `process_one`, `main` Tasks 2, 3 ✓
