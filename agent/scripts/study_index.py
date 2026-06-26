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


def slugify(titulo: str) -> str:
    nfkd = unicodedata.normalize("NFKD", titulo or "")
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii").lower()
    kebab = re.sub(r"[^a-z0-9]+", "-", ascii_str)
    return kebab.strip("-")


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
