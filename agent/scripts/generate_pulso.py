"""Generate Pulso do Dia — 5-10 highlights with multi-source interpretation.

Sonnet reads the curated report (artigos + noticias + podcasts + videos +
discussoes_x), identifies items that "made difference" today, and produces
deep contextual analysis citing multi-source coverage.

This is what the user reads first thing in the morning — quick scan of
"what mattered today" with cross-source signal and community interpretation
(Mandrola podcast take, Topol X comment, Medscape commentary, etc.).

The Destaque do Dia (single most important item) is the FIRST entry with
is_destaque_do_dia=true, replacing the standalone destaque_do_dia field.

Output schema (per item):
    {
      id: pulso_001,
      is_destaque_do_dia: bool (only 1st = true),
      titulo: str,
      razao_destaque: str,
      o_que_paper_diz: str,
      interpretacao_comunidade: str,
      o_que_muda: str,
      o_que_nao_muda_ainda: str,
      fontes_cobertura: [{tipo, id, publicacao|autor}],
      classe: A|B|C,
      score: 0-10
    }
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from anthropic import Anthropic, APIError

logger = logging.getLogger(__name__)

PULSO_MODEL = os.environ.get("PULSO_MODEL", "claude-sonnet-4-6")
PULSO_MAX_TOKENS = 8000  # ~10 items × ~500 tokens ≈ 5K + headroom


def _strip_json_fences(text: str) -> str:
    """Remove markdown code fences if present."""
    text = text.strip()
    m = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    if not text.startswith("["):
        idx = text.find("[")
        if idx >= 0:
            text = text[idx:]
    return text


def _extract_compact_report(report: dict) -> str:
    """Build compact structured representation of the report for Sonnet to analyze.

    Includes IDs explicitly so Sonnet can reference them in fontes_cobertura.
    """
    lines = []

    artigos = sorted(report.get("artigos", []), key=lambda a: a.get("score", 0), reverse=True)[:30]
    if artigos:
        lines.append("=== ARTIGOS CIENTÍFICOS (top 30 por score) ===")
        for a in artigos:
            lines.append(f"[id={a.get('id', '?')}] [{a.get('classe', '?')}/score={a.get('score', '?')}] {a.get('publicacao', '')}: {a.get('titulo', '')[:140]}")
            if a.get("resumo"):
                lines.append(f"   resumo: {a['resumo'][:280]}")
            # Framework fields (preferidos quando presentes; mais ricos que `resumo`)
            if a.get("contexto_clinico"):
                lines.append(f"   contexto: {a['contexto_clinico'][:240]}")
            if a.get("principais_resultados"):
                lines.append(f"   resultados: {a['principais_resultados'][:400]}")
            if a.get("conclusao_uma_frase"):
                lines.append(f"   veredito: {a['conclusao_uma_frase'][:200]}")
            elif a.get("conclusao"):  # legacy fallback
                lines.append(f"   conclusao: {a['conclusao'][:240]}")
            if a.get("pontos_chave"):
                chave_str = " | ".join(a["pontos_chave"][:5])
                lines.append(f"   dados: {chave_str[:320]}")
            if a.get("interpretacao_pratica"):
                lines.append(f"   interpretacao: {a['interpretacao_pratica'][:240]}")
            elif a.get("impacto_clinico"):  # legacy fallback
                lines.append(f"   impacto: {a['impacto_clinico'][:200]}")
            lines.append("")

    noticias = report.get("noticias", [])[:15]
    if noticias:
        lines.append("\n=== NOTÍCIAS CLÍNICAS ===")
        for n in noticias:
            lines.append(f"[id={n.get('id', '?')}] {n.get('publicacao', '')}: {n.get('titulo', '')[:140]}")
            if n.get("resumo"):
                lines.append(f"   resumo: {n['resumo'][:240]}")
            lines.append("")

    podcasts = report.get("podcasts", [])[:10]
    if podcasts:
        lines.append("\n=== PODCASTS ===")
        for p in podcasts:
            lines.append(f"[id={p.get('id', '?')}] {p.get('publicacao', '')} (host: {p.get('host', '?')}): {p.get('titulo', '')[:140]}")
            if p.get("resumo"):
                lines.append(f"   resumo: {p['resumo'][:280]}")
            if p.get("bullet_points"):
                bullets_str = " | ".join(p["bullet_points"][:4])
                lines.append(f"   bullets: {bullets_str[:300]}")
            lines.append("")

    videos = report.get("videos_youtube", [])[:25]
    if videos:
        lines.append("\n=== VÍDEOS YOUTUBE (use video_url como id em fontes_cobertura) ===")
        for v in videos:
            transcript_flag = " [TRANSCRIPT]" if v.get("_transcript_used") else ""
            lines.append(f"[url={v.get('video_url', '?')}]{transcript_flag} [{v.get('canal', '')}]: {v.get('titulo', '')[:140]}")
            # Phase 6 + Combo Total: prefer Gemini-enriched PT-BR fields with rich
            # Nível-1 schema (5-7 bullets, 5-7 sentence resumo, 3 contextual fields).
            if v.get("tema"):
                lines.append(f"   tema: {v['tema'][:80]}")
            if v.get("resumo_pt"):
                lines.append(f"   resumo: {v['resumo_pt'][:400]}")
            elif v.get("descricao_preview"):
                lines.append(f"   desc: {v['descricao_preview'][:200]}")
            if v.get("bullets_pt"):
                bullets_str = " | ".join(v["bullets_pt"][:5])
                lines.append(f"   bullets: {bullets_str[:400]}")
            if v.get("evidencia_chave"):
                lines.append(f"   evidencia: {v['evidencia_chave'][:200]}")
            if v.get("contraponto"):
                lines.append(f"   contraponto: {v['contraponto'][:200]}")
            if v.get("quem_se_aplica"):
                lines.append(f"   aplicacao: {v['quem_se_aplica'][:160]}")
            lines.append("")

    disc = report.get("discussoes_x", [])[:25]
    if disc:
        lines.append("\n=== DISCUSSÕES X/TWITTER ===")
        for d in disc:
            cache_flag = " [CACHE_FALLBACK]" if d.get("_cache_fallback") else ""
            lines.append(f"[id={d.get('id', '?')}]{cache_flag} {d.get('autor', '')}: {d.get('titulo', '')[:140]}")
            if d.get("resumo"):
                lines.append(f"   resumo: {d['resumo'][:240]}")
            if d.get("impacto_clinico"):
                lines.append(f"   impacto: {d['impacto_clinico'][:180]}")
            lines.append("")

    substacks = report.get("substacks", [])[:20]
    if substacks:
        lines.append("\n=== SUBSTACKS (newsletters de cardiologistas — voz da comunidade) ===")
        for s in substacks:
            autor = s.get("autor") or s.get("publicacao", "?")
            lines.append(f"[id={s.get('id', '?')}] {s.get('publicacao', '')} ({autor}): {s.get('titulo', '')[:140]}")
            if s.get("tema"):
                lines.append(f"   tema: {s['tema'][:80]}")
            if s.get("resumo"):
                lines.append(f"   resumo: {s['resumo'][:400]}")
            if s.get("bullets"):
                bullets_str = " | ".join(s["bullets"][:5])
                lines.append(f"   bullets: {bullets_str[:400]}")
            if s.get("evidencia_chave"):
                lines.append(f"   evidencia: {s['evidencia_chave'][:200]}")
            if s.get("contraponto"):
                lines.append(f"   contraponto: {s['contraponto'][:200]}")
            if s.get("quem_se_aplica"):
                lines.append(f"   aplicacao: {s['quem_se_aplica'][:160]}")
            lines.append("")

    return "\n".join(lines)


def generate_pulso(report: dict, anthropic_client: Anthropic = None) -> list[dict[str, Any]]:
    """
    Generate 5-10 Pulso highlights from a curated report.

    Args:
        report: parsed report dict (already populated by Opus + injectors)
        anthropic_client: optional, will be created from env if not provided

    Returns:
        list of pulso items (may be empty if generation fails — non-critical feature)
    """
    if anthropic_client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not set — skipping Pulso generation")
            return []
        anthropic_client = Anthropic(api_key=api_key, max_retries=2)

    # Load prompt
    prompt_path = Path(__file__).parent.parent / "prompts" / "pulso_prompt.txt"
    try:
        with open(prompt_path, encoding="utf-8") as f:
            system_prompt = f.read()
    except FileNotFoundError:
        logger.error(f"pulso_prompt.txt not found at {prompt_path}")
        return []

    compact = _extract_compact_report(report)
    input_chars = len(compact)
    logger.info(f"Pulso: extracted {input_chars} chars of compact report for Sonnet")

    if input_chars < 500:
        logger.warning("Compact report is too small for meaningful Pulso — skipping")
        return []

    # Historical context — semantic lookup of related items from past 90 days.
    # Pulso candidates get a "_historical_context" block in the prompt with
    # references that scored >= 7 (anti-force). Items with no strong matches
    # simply don't get historical references — better honest silence than
    # forced connections.
    historical_block = ""
    related_map: dict = {}
    if os.environ.get("DISABLE_HISTORY_LOOKUP", "").lower() not in ("1", "true", "yes"):
        try:
            from agent.scripts.history_lookup import find_related_for_items
            top_candidates = []
            for a in (report.get("artigos") or [])[:8]:
                top_candidates.append(a)
            for n in (report.get("noticias") or [])[:8]:
                top_candidates.append(n)
            for p in (report.get("podcasts") or [])[:5]:
                top_candidates.append(p)
            today_date = report.get("relatorio_data")
            logger.info(f"History lookup: searching related context for {len(top_candidates)} candidates...")
            related_map = find_related_for_items(
                top_candidates,
                exclude_date=today_date,
                lookback_days=90,
            )
            if related_map:
                lines = ["", "=== CONTEXTO HISTÓRICO (últimos 90 dias) ===",
                         "Items abaixo têm ligação clínica forte com items de hoje (score >= 7/10).",
                         "Use SE a conexão for naturalmente relevante. NÃO force referência se duvidoso.",
                         ""]
                for item_id, related in related_map.items():
                    lines.append(f"[id={item_id}] tem {len(related)} relacionado(s):")
                    for r in related:
                        lines.append(
                            f"  - {r['date']} ({r['type']}, score {r['score']}/10): "
                            f"{r['titulo'][:100]}"
                        )
                        if r.get('reason'):
                            lines.append(f"      ligação: {r['reason']}")
                historical_block = "\n".join(lines)
                logger.info(f"History: {len(related_map)} items have related context")
        except Exception as e:
            logger.warning(f"History lookup failed (degrading): {type(e).__name__}: {e}")

    user_message = (
        f"Gere 5-10 destaques do Pulso a partir do relatório abaixo. "
        f"Use os IDs reais (id=art_xxx, not_xxx, pod_xxx, x_xxx) em fontes_cobertura.\n\n"
        f"{compact}"
        f"{historical_block}"
    )

    try:
        logger.info(f"Calling Claude {PULSO_MODEL} for Pulso generation")
        response = anthropic_client.messages.create(
            model=PULSO_MODEL,
            max_tokens=PULSO_MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        usage = getattr(response, "usage", None)
        if usage:
            logger.info(f"Pulso usage: input={usage.input_tokens}, output={usage.output_tokens}")
    except APIError as e:
        logger.error(f"Pulso API call failed: {e}")
        return []
    except Exception as e:
        logger.error(f"Pulso unexpected error: {e}")
        return []

    raw = response.content[0].text if response.content else ""
    if not raw:
        logger.warning("Empty response from Sonnet for Pulso")
        return []

    cleaned = _strip_json_fences(raw)
    try:
        items = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Pulso JSON: {e}")
        logger.debug(f"Raw response (first 500): {raw[:500]}")
        return []

    if not isinstance(items, list):
        logger.warning(f"Pulso response is not a list (got {type(items).__name__})")
        return []

    # Validate & normalize
    valid = []
    required = {"titulo", "razao_destaque", "o_que_paper_diz",
                "interpretacao_comunidade", "o_que_muda", "o_que_nao_muda_ainda",
                "fontes_cobertura", "classe", "score"}
    valid_classes = {"A", "B", "C"}

    has_destaque = False  # ensure exactly 1 is_destaque_do_dia=true
    for i, item in enumerate(items, 1):
        if not isinstance(item, dict):
            continue
        if not required.issubset(item.keys()):
            logger.debug(f"Pulso item {i}: missing fields {required - set(item.keys())}")
            continue
        if item.get("classe") not in valid_classes:
            continue
        # Score must be number 0-10
        score = item.get("score")
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            continue
        if not (0 <= score <= 10):
            continue
        # fontes_cobertura must be non-empty list
        if not isinstance(item.get("fontes_cobertura"), list) or not item["fontes_cobertura"]:
            continue
        # Coerce is_destaque_do_dia to bool, ensure only 1st is true
        is_destaque = bool(item.get("is_destaque_do_dia", False))
        if is_destaque and not has_destaque:
            has_destaque = True
        else:
            is_destaque = False
        item["is_destaque_do_dia"] = is_destaque
        # Assign sequential id (overrides any ID Sonnet generated)
        item["id"] = f"pulso_{len(valid)+1:03d}"
        valid.append(item)

    # Ensure first item is the Big One — if none were marked, force first to be
    if valid and not has_destaque:
        valid[0]["is_destaque_do_dia"] = True
        logger.info("Pulso: no item flagged is_destaque_do_dia — forced first item")

    # Inject authoritative URLs into historical_references.
    # Sonnet may include the field but cannot reliably produce URLs (we never
    # gave it URLs in the input). We have the real URLs from related_map —
    # match each Sonnet-generated ref to its authoritative source by
    # (date + titulo prefix) and overwrite/set the url field.
    if related_map:
        url_lookup: dict = {}
        for refs_list in related_map.values():
            for r in refs_list:
                if r.get("url"):
                    key = (r.get("date", ""), (r.get("titulo") or "")[:60].strip().lower())
                    url_lookup[key] = r["url"]
        if url_lookup:
            injected = 0
            for v in valid:
                hist = v.get("historical_references") or []
                if not isinstance(hist, list):
                    continue
                for h in hist:
                    if not isinstance(h, dict):
                        continue
                    key = (h.get("date", ""), (h.get("titulo") or "")[:60].strip().lower())
                    if key in url_lookup:
                        h["url"] = url_lookup[key]
                        injected += 1
            if injected:
                logger.info(f"Pulso: injected {injected} authoritative URLs into historical_references")

    logger.info(f"Pulso generated: {len(valid)}/{len(items)} valid")
    return valid


if __name__ == "__main__":
    import sys, glob
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.INFO)

    files = sorted(glob.glob("data/relatorio-*.json"))
    if not files:
        print("No reports found in data/")
        sys.exit(1)

    with open(files[-1], encoding="utf-8") as f:
        report = json.load(f)

    print(f"Loading {files[-1]}...")
    items = generate_pulso(report)
    print(f"\nGenerated {len(items)} Pulso items:\n")
    for item in items:
        flag = "🌟 DESTAQUE" if item.get("is_destaque_do_dia") else "▸"
        print(f"\n{flag} [{item['classe']}/score {item['score']}] {item['titulo']}")
        print(f"   Razão: {item['razao_destaque'][:140]}")
        print(f"   Fontes: {len(item['fontes_cobertura'])} cross-source")
