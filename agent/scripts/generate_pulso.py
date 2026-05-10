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
            if a.get("impacto_clinico"):
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
            lines.append(f"[url={v.get('video_url', '?')}] [{v.get('canal', '')}]: {v.get('titulo', '')[:140]}")
            if v.get("descricao_preview"):
                lines.append(f"   desc: {v['descricao_preview'][:200]}")
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

    user_message = (
        f"Gere 5-10 destaques do Pulso a partir do relatório abaixo. "
        f"Use os IDs reais (id=art_xxx, not_xxx, pod_xxx, x_xxx) em fontes_cobertura.\n\n"
        f"{compact}"
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
