"""Helpers puros do modulo Estudo: slug, indice por mes, linkificacao de referencias."""
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus

_DOI_RE = re.compile(r"\b[Dd][Oo][Ii]:\s*(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)")
_PMID_RE = re.compile(r"\bPMID:\s*(\d+)")
_NUMBERED_REF_RE = re.compile(r"^\s*\d+\.\s+\S")
_REFS_HEADING_RE = re.compile(r"^#+\s*refer[êe]ncias", re.IGNORECASE)
_ANY_HEADING_RE = re.compile(r"^#+\s")


def slugify(titulo: str, max_len: int = 80) -> str:
    nfkd = unicodedata.normalize("NFKD", titulo or "")
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii").lower()
    kebab = re.sub(r"[^a-z0-9]+", "-", ascii_str).strip("-")
    # Capa o tamanho (titulos de guidelines tem 200+ chars): nome de pasta longo
    # demais estoura o limite de caminho do Windows (260) e quebra o git local.
    # Corta na ultima palavra antes de max_len.
    if len(kebab) > max_len:
        kebab = kebab[:max_len].rsplit("-", 1)[0].strip("-") or kebab[:max_len]
    return kebab


def linkify_references(markdown: str) -> str:
    def _doi(m):
        d = m.group(1)
        # O DOI no texto-fonte costuma vir seguido de pontuacao (ex: "10.x/y)."
        # fechando um parenteses, ou "10.x/y;" separando refs). Essa pontuacao
        # NAO faz parte do DOI: separamos para o link ficar valido e devolvemos
        # a pontuacao logo apos o link (preserva o texto ao redor).
        trail = ""
        while d and d[-1] in ").,;:":
            trail = d[-1] + trail
            d = d[:-1]
        return f"[{d}](https://doi.org/{d}){trail}"

    def _pmid(m):
        p = m.group(1)
        return f"[PMID {p}](https://pubmed.ncbi.nlm.nih.gov/{p}/)"

    out_lines = []
    in_refs = False
    for line in markdown.splitlines():
        # Rastreia se estamos DENTRO da secao "Referencias citadas" — o link de
        # busca por NOME so vale ali (nao em listas numeradas de outras secoes,
        # ex: "Consideracoes Praticas").
        if _REFS_HEADING_RE.match(line):
            in_refs = True
        elif _ANY_HEADING_RE.match(line):
            in_refs = False

        # Link "buscar" (Google Academico) pelo NOME inteiro do artigo, em nova
        # aba. Query montada do texto LIMPO da citacao: sem o numero e sem os
        # tokens DOI:/PMID:. Complementa o link de DOI (que vai ao artigo exato)
        # ajudando a achar o PDF livre / outras versoes.
        scholar = ""
        if in_refs and _NUMBERED_REF_RE.match(line):
            limpo = _PMID_RE.sub("", _DOI_RE.sub("", line))
            limpo = re.sub(r"^\s*\d+\.\s*", "", limpo).strip()
            termos = " ".join(limpo.split()[:30])
            if termos:
                scholar = (" — [🔍 buscar](https://scholar.google.com/scholar"
                           f"?q={quote_plus(termos)})")

        line = _DOI_RE.sub(_doi, line)
        line = _PMID_RE.sub(_pmid, line)
        out_lines.append(line + scholar)
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
                "doi": meta.get("doi", ""),
            })
    for ym in por_mes:
        por_mes[ym].sort(key=lambda m: m.get("data", ""), reverse=True)
    meses = sorted(por_mes.keys(), reverse=True)
    return {
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "por_mes": por_mes,
        "meses_disponiveis": meses,
    }
