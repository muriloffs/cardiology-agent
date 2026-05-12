"""Find semantically related historical items for Pulso context.

Two-stage pipeline:
1. Keyword pre-filter (instant, free) — find candidates with token overlap
2. Gemini semantic re-rank ($0.10/run) — keep only items with score >= 7

Anti-force principle: if no strong matches found, return empty list. Better
to omit historical context than to fabricate weak connections. Same philosophy
applied across the codebase (show_notes_quality, news enrichment, etc.).

Loaded by generate_pulso.py to enrich Sonnet input with historical context.
"""

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from agent.scripts.fetch_gemini_external import _get_client, _grounded_call

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "data"
DEFAULT_LOOKBACK_DAYS = 90
SCORE_THRESHOLD = 7.0      # below this, ignore (anti-force)
MAX_RELATED_PER_ITEM = 5   # final cap after re-rank

# Generic stopwords (not medically meaningful) — filtered from keyword extraction
_STOPWORDS = frozenset({
    # English
    "the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by",
    "from", "as", "is", "was", "are", "were", "be", "been", "being", "have", "has",
    "had", "do", "does", "did", "will", "would", "should", "could", "may", "might",
    "this", "that", "these", "those", "study", "trial", "patient", "patients",
    "year", "years", "month", "months", "week", "weeks", "data", "result", "results",
    # PT-BR
    "que", "para", "com", "uma", "uns", "umas", "não", "uma", "esse", "essa", "isso",
    "no", "na", "nos", "nas", "do", "da", "dos", "das", "se", "em", "por", "ao",
    "como", "mais", "mas", "foi", "ser", "ter", "ele", "ela", "eles", "elas",
    "estudo", "estudos", "ensaio", "paciente", "pacientes", "ano", "anos", "mes",
    "meses", "semana", "semanas", "dia", "dias", "resultado", "resultados", "dados",
})


def _extract_keywords(item: dict, max_keywords: int = 10) -> list[str]:
    """Extract medical-domain keywords from an item's title + key text fields."""
    text_parts: list[str] = []
    for field in ("titulo", "resumo", "conclusao_uma_frase", "interpretacao_pratica",
                  "contexto_clinico", "principais_resultados", "impacto_clinico"):
        v = item.get(field)
        if isinstance(v, str):
            text_parts.append(v)
    for list_field in ("pontos_chave", "bullets", "bullet_points"):
        v = item.get(list_field)
        if isinstance(v, list):
            text_parts.extend(p for p in v if isinstance(p, str))
    text = " ".join(text_parts).lower()
    tokens = re.findall(r"[a-záéíóúâêôãõç-]{4,}", text)
    counts: dict[str, int] = {}
    for t in tokens:
        if t in _STOPWORDS:
            continue
        counts[t] = counts.get(t, 0) + 1
    return sorted(counts.keys(), key=lambda t: -counts[t])[:max_keywords]


def load_recent_reports(days: int = DEFAULT_LOOKBACK_DAYS,
                        exclude_date: str | None = None) -> list[dict]:
    """Load all relatorio-*.json files from data/ within the lookback window."""
    if not DATA_DIR.is_dir():
        return []
    cutoff_date = (datetime.now() - timedelta(days=days)).date().isoformat()
    reports: list[dict] = []
    for f in sorted(DATA_DIR.glob("relatorio-*.json"), reverse=True):
        try:
            date_str = f.stem.replace("relatorio-", "")
            if date_str < cutoff_date:
                break
            if exclude_date and date_str == exclude_date:
                continue
            with open(f, encoding="utf-8") as fp:
                report = json.load(fp)
            report["_date"] = date_str
            reports.append(report)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"History: skipping {f.name}: {e}")
    return reports


def _collect_historical_items(reports: list[dict],
                              include_types: set[str]) -> list[dict]:
    """Flatten items from historical reports, tagging each with date + type."""
    items: list[dict] = []
    type_map = [
        ("artigo", "artigos"),
        ("noticia", "noticias"),
        ("substack", "substacks"),
        ("pulso", "pulso"),
    ]
    for r in reports:
        date = r.get("_date", "?")
        for type_label, field_name in type_map:
            if type_label not in include_types:
                continue
            for it in r.get(field_name, []) or []:
                if isinstance(it, dict):
                    items.append({"_date": date, "_type": type_label, **it})
    return items


def _keyword_prefilter(today_item: dict, historical_items: list[dict],
                       top_n: int = 15) -> list[tuple[dict, int]]:
    """Return historical items sorted by keyword overlap with today's item.

    Only candidates with at least 2 keyword matches survive — single-keyword
    matches are usually too generic ("cardiac" alone is meaningless).
    """
    today_kw = set(_extract_keywords(today_item))
    if not today_kw:
        return []
    scored: list[tuple[dict, int]] = []
    for h in historical_items:
        h_kw = set(_extract_keywords(h))
        overlap = len(today_kw & h_kw)
        if overlap >= 2:
            scored.append((h, overlap))
    scored.sort(key=lambda x: -x[1])
    return scored[:top_n]


def _semantic_rerank(client, today_item: dict,
                     candidates: list[tuple[dict, int]],
                     threshold: float = SCORE_THRESHOLD) -> list[dict]:
    """Use Gemini to score each candidate's semantic relevance (0-10).

    Returns ONLY items with score >= threshold. Empty list if Gemini finds
    no genuine clinical connection — this is the anti-force guarantee.
    """
    if not candidates or not client:
        return []

    today_summary = (
        f"{today_item.get('titulo', '')}. "
        f"{(today_item.get('resumo') or today_item.get('conclusao_uma_frase') or '')[:300]}"
    )

    candidates_lines = []
    for i, (cand, _) in enumerate(candidates, 1):
        date = cand.get("_date", "?")
        ctype = cand.get("_type", "?")
        title = (cand.get("titulo") or "")[:80]
        summary = (cand.get("resumo") or cand.get("conclusao_uma_frase") or "")[:150]
        candidates_lines.append(f"[{i}] {date} ({ctype}): {title} — {summary}")
    candidates_str = "\n".join(candidates_lines)

    prompt = f"""Avalie se algum item HISTÓRICO de cardiologia tem ligação CLÍNICA GENUÍNA com o item de HOJE.

ITEM DE HOJE:
{today_summary}

CANDIDATOS HISTÓRICOS (últimos 90 dias):
{candidates_str}

Para cada candidato, escreva UMA LINHA neste formato EXATO:
INDEX: <número> | SCORE: <0-10> | REASON: <explicação curta em PT-BR>

Critérios de SCORE:
- 10: Mesma droga/intervenção/doença, achados diretamente comparáveis
- 8-9: Mesma área clínica, evidências complementares ou contraditórias
- 6-7: Tópico relacionado mas ângulo diferente (ex: mecanismo vs desfecho)
- 4-5: Mesmo campo geral, foco específico diferente
- 0-3: Apenas sobreposição de palavra, NÃO clinicamente relacionado — IGNORE

REGRA INVIOLÁVEL: só retorne candidatos com score ≥ 6. Pule completamente os que tem score < 6. Preferimos NÃO citar do que citar uma ligação fraca/forçada.

Plain text. No JSON. No markdown. Se nenhum candidato atingir score ≥ 6: NONE"""

    text = _grounded_call(client, prompt, "history-rerank")
    if not text or text.strip().upper() == "NONE":
        return []

    related: list[dict] = []
    for line in text.split("\n"):
        line = line.strip()
        if "|" not in line or "INDEX" not in line.upper():
            continue
        try:
            parts = [p.strip() for p in line.split("|")]
            idx_match = re.search(r"\d+", parts[0])
            score_match = re.search(r"[\d.]+", parts[1])
            if not idx_match or not score_match:
                continue
            idx = int(idx_match.group(0))
            score = float(score_match.group(0))
            reason = ""
            if len(parts) > 2:
                reason = re.sub(r"^[A-Z_]+\s*:?\s*", "", parts[2]).strip()
            if score >= threshold and 1 <= idx <= len(candidates):
                cand = candidates[idx - 1][0]
                related.append({
                    "date": cand.get("_date"),
                    "type": cand.get("_type"),
                    "titulo": (cand.get("titulo") or "")[:140],
                    "score": round(score, 1),
                    "reason": reason[:200],
                })
        except (ValueError, AttributeError, IndexError):
            continue

    related.sort(key=lambda x: -x["score"])
    return related[:MAX_RELATED_PER_ITEM]


def find_related_for_items(today_items: list[dict],
                           exclude_date: str | None = None,
                           lookback_days: int = DEFAULT_LOOKBACK_DAYS,
                           include_types: set[str] | None = None
                           ) -> dict[str, list[dict]]:
    """Find related historical items for each item in today_items.

    Args:
        today_items: items to look up (each must have 'id' field)
        exclude_date: skip this date in history (avoids self-reference)
        lookback_days: how far back to search
        include_types: subset of {"artigo","noticia","substack","pulso"}

    Returns:
        dict: today_item_id -> list of related historical items.
        Items with no strong matches are OMITTED (anti-force principle).
        Each related item has: date, type, titulo, score, reason.
    """
    if not today_items:
        return {}
    if include_types is None:
        include_types = {"artigo", "noticia", "substack", "pulso"}

    reports = load_recent_reports(days=lookback_days, exclude_date=exclude_date)
    if not reports:
        logger.info("History lookup: no historical reports in window")
        return {}

    historical_items = _collect_historical_items(reports, include_types)
    logger.info(
        f"History lookup pool: {len(reports)} reports, "
        f"{len(historical_items)} items, types={sorted(include_types)}"
    )

    client = _get_client()
    if not client:
        logger.warning("History lookup: GOOGLE_API_KEY missing — skipping semantic re-rank")

    results: dict[str, list[dict]] = {}

    def _process(item: dict):
        item_id = item.get("id")
        if not item_id:
            return None, []
        candidates = _keyword_prefilter(item, historical_items, top_n=15)
        if not candidates:
            return item_id, []
        if not client:
            # Without semantic re-rank, return top 3 keyword candidates flagged as such.
            # Lower confidence — frontend can still show them but distinctly.
            return item_id, [{
                "date": c.get("_date"), "type": c.get("_type"),
                "titulo": (c.get("titulo") or "")[:140],
                "score": 6.0, "reason": "keyword overlap (no semantic re-rank)",
            } for c, _ in candidates[:3]]
        return item_id, _semantic_rerank(client, item, candidates)

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(_process, it): it for it in today_items}
        for future in as_completed(futures):
            try:
                item_id, related = future.result(timeout=90)
                if item_id and related:
                    results[item_id] = related
            except Exception as e:
                logger.warning(f"History lookup failed for item: {type(e).__name__}: {e}")

    logger.info(
        f"History lookup: {len(results)}/{len(today_items)} items got related context "
        f"(filtered for score >= {SCORE_THRESHOLD})"
    )
    return results


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    # Standalone test: use latest report's pulso candidates
    reports = load_recent_reports(days=90)
    if reports:
        latest = reports[0]
        items = latest.get("artigos", [])[:5]
        results = find_related_for_items(items, exclude_date=latest.get("_date"))
        print(f"\nFound related context for {len(results)} items:\n")
        for iid, related in results.items():
            print(f"Item {iid}:")
            for r in related:
                print(f"  [{r['date']} {r['type']}] score={r['score']} — {r['titulo'][:60]}")
                print(f"    reason: {r['reason']}")
            print()
