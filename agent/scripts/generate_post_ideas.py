"""Generate Instagram post ideas for lay-audience patients from the curated report.

Uses Claude Sonnet 4.6 (cheaper than Opus, plenty for creative-structured task).
Output is a list of 20-30 ideas (scales with report size — see prompt's quantity
table), each with: tipo, emoji, ideia, bullets, formato_visual, fonte. The
cardiologist uses these as inspiration to write the actual post elsewhere.
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from anthropic import Anthropic, APIError

logger = logging.getLogger(__name__)

POST_IDEAS_MODEL = os.environ.get("POST_IDEAS_MODEL", "claude-sonnet-4-6")
# 30 ideas × ~470 tokens each (ideia + 5+ bullets + formato_visual + fonte) ≈ 14k.
# Observed: 30-idea run hit exactly 14000 tokens and got truncated mid-JSON.
# 20000 gives ~40% safety margin for 30 ideas; Sonnet 4.6 supports up to 32k.
POST_IDEAS_MAX_TOKENS = 20000


def _extract_compact_report(report: dict) -> str:
    """Build a compact text summary of the report (only fields that matter for ideas)."""
    lines = []

    # ARTIGOS — top 30 by score
    artigos = sorted(report.get("artigos", []), key=lambda a: a.get("score", 0), reverse=True)[:30]
    if artigos:
        lines.append("=== ARTIGOS CIENTÍFICOS ===")
        for a in artigos:
            url = (a.get("links", {}).get("url")
                   or (f"https://pubmed.ncbi.nlm.nih.gov/{a['links']['pubmed']}/" if a.get("links", {}).get("pubmed") else "")
                   or (f"https://doi.org/{a['links']['doi']}" if a.get("links", {}).get("doi") else ""))
            lines.append(f"[{a.get('id', '?')}] [{a.get('classe', '?')}] {a.get('publicacao', '')}: {a.get('titulo', '')[:140]}")
            lines.append(f"   resumo: {a.get('resumo', '')[:280]}")
            if a.get("conclusao"):
                lines.append(f"   conclusao: {a['conclusao'][:240]}")
            if a.get("pontos_chave"):
                chave_str = " | ".join(a["pontos_chave"][:5])
                lines.append(f"   dados: {chave_str[:320]}")
            if a.get("impacto_clinico"):
                lines.append(f"   impacto: {a['impacto_clinico'][:180]}")
            if url:
                lines.append(f"   url: {url}")
            lines.append("")

    # NOTICIAS — top 15
    noticias = report.get("noticias", [])[:15]
    if noticias:
        lines.append("\n=== NOTÍCIAS ===")
        for n in noticias:
            url = n.get("links", {}).get("url") or ""
            lines.append(f"[{n.get('id', '?')}] {n.get('publicacao', '')}: {n.get('titulo', '')[:140]}")
            lines.append(f"   resumo: {n.get('resumo', '')[:240]}")
            if url:
                lines.append(f"   url: {url}")
            lines.append("")

    # PODCASTS — top 10
    podcasts = report.get("podcasts", [])[:10]
    if podcasts:
        lines.append("\n=== PODCASTS ===")
        for p in podcasts:
            url = p.get("links", {}).get("episode_url") or ""
            lines.append(f"[{p.get('id', '?')}] {p.get('publicacao', '')}: {p.get('titulo', '')[:140]}")
            lines.append(f"   resumo: {p.get('resumo', '')[:280]}")
            if p.get("bullet_points"):
                bullets_str = " | ".join(p["bullet_points"][:5])
                lines.append(f"   bullets: {bullets_str[:400]}")
            if url:
                lines.append(f"   url: {url}")
            lines.append("")

    # VIDEOS YOUTUBE — top 25. Use Combo-Total enriched fields (Pro + transcript)
    # when available, fall back to raw RSS description.
    videos = report.get("videos_youtube", [])[:25]
    if videos:
        lines.append("\n=== VÍDEOS YOUTUBE ===")
        for v in videos:
            transcript_flag = " [TRANSCRIPT-BASED]" if v.get("_transcript_used") else ""
            lines.append(f"[v_{videos.index(v)+1:03d}]{transcript_flag} [{v.get('canal', '')}] {v.get('titulo', '')[:140]}")
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
            lines.append(f"   url: {v.get('video_url', '')}")
            lines.append("")

    # DISCUSSOES X — top 20
    disc = report.get("discussoes_x", [])[:20]
    if disc:
        lines.append("\n=== DISCUSSÕES X/TWITTER ===")
        for d in disc:
            url = (d.get("links", {}).get("post_url") or d.get("links", {}).get("url") or "")
            lines.append(f"[{d.get('id', '?')}] {d.get('autor', '')}: {d.get('titulo', '')[:140]}")
            lines.append(f"   resumo: {d.get('resumo', '')[:240]}")
            if url:
                lines.append(f"   url: {url}")
            lines.append("")

    # SUBSTACKS — Phase 7 + Combo-Total enriched (Pro + 3 new contextual fields).
    substacks = report.get("substacks", [])[:15]
    if substacks:
        lines.append("\n=== SUBSTACKS (newsletters de cardiologistas) ===")
        for s in substacks:
            autor = s.get("autor") or s.get("publicacao", "?")
            lines.append(f"[{s.get('id', '?')}] {s.get('publicacao', '')} ({autor}): {s.get('titulo', '')[:140]}")
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
            if s.get("url"):
                lines.append(f"   url: {s['url']}")
            lines.append("")

    return "\n".join(lines)


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


def generate_post_ideas(report: dict, anthropic_client: Anthropic = None) -> list[dict[str, Any]]:
    """
    Generate 8-10 post ideas from a curated report.

    Args:
        report: parsed report dict (with artigos, noticias, podcasts, videos_youtube, discussoes_x)
        anthropic_client: optional, will be created from env if not provided

    Returns:
        list of post idea dicts (may be empty if generation fails — non-critical feature)
    """
    if anthropic_client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not set — skipping post ideas generation")
            return []
        anthropic_client = Anthropic(api_key=api_key, max_retries=2)

    # Load prompt
    prompt_path = Path(__file__).parent.parent / "prompts" / "post_ideas_prompt.txt"
    try:
        with open(prompt_path, encoding="utf-8") as f:
            system_prompt = f.read()
    except FileNotFoundError:
        logger.error(f"post_ideas_prompt.txt not found at {prompt_path}")
        return []

    # Build compact input
    compact = _extract_compact_report(report)
    input_chars = len(compact)
    logger.info(f"Post ideas: extracted {input_chars} chars of compact report for Sonnet")

    if input_chars < 200:
        logger.warning("Compact report is suspiciously small — skipping post ideas generation")
        return []

    # Count total items so the user message can reinforce the quantity table.
    # System prompt has the authoritative table; this echoes it explicitly so
    # Sonnet doesn't ignore the rule (history: it does ignore generic system
    # rules when user message says something different).
    n_items = (
        len(report.get("artigos", []))
        + len(report.get("noticias", []))
        + len(report.get("podcasts", []))
        + len(report.get("videos_youtube", []))
        + len(report.get("discussoes_x", []))
        + len(report.get("substacks", []))
    )
    if n_items >= 80:
        target = "30"
        minimum = "30"
    elif n_items >= 50:
        target = "27-30"
        minimum = "25"
    elif n_items >= 30:
        target = "22-25"
        minimum = "20"
    elif n_items >= 15:
        target = "17-20"
        minimum = "15"
    else:
        target = "5-8"
        minimum = "5"

    user_message = (
        f"O relatório abaixo tem {n_items} itens curados. Conforme a tabela do system_prompt, "
        f"você DEVE gerar NO MÍNIMO {minimum} ideias (alvo: {target}). Não retorne menos — "
        f"se achar só 10-15 'perfeitas', faça segundo passe pra atingir o mínimo conforme as "
        f"regras do system_prompt (ângulos secundários, cobertura cruzada, hooks razoáveis vs perfeitos).\n\n"
        f"Material disponível ({n_items} itens):\n\n"
        f"{compact}"
    )
    logger.info(f"Post ideas: target {target} ideias (minimum {minimum}) for {n_items} items")

    try:
        logger.info(f"Calling Claude {POST_IDEAS_MODEL} for post ideas generation")
        response = anthropic_client.messages.create(
            model=POST_IDEAS_MODEL,
            max_tokens=POST_IDEAS_MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        usage = getattr(response, "usage", None)
        if usage:
            logger.info(f"Post ideas usage: input={usage.input_tokens}, output={usage.output_tokens}")
    except APIError as e:
        logger.error(f"Post ideas API call failed: {e}")
        return []
    except Exception as e:
        logger.error(f"Post ideas unexpected error: {e}")
        return []

    raw = response.content[0].text if response.content else ""
    if not raw:
        logger.warning("Empty response from Sonnet for post ideas")
        return []

    cleaned = _strip_json_fences(raw)
    try:
        ideas = json.loads(cleaned)
    except json.JSONDecodeError as e:
        # Try json_repair before giving up — handles truncated arrays, missing
        # commas, unbalanced quotes. Saves partial output when Sonnet hits
        # max_tokens mid-array (last full idea still recoverable).
        logger.warning(f"Direct JSON parse failed: {e} — trying json_repair fallback")
        try:
            from json_repair import repair_json
            repaired = repair_json(cleaned)
            ideas = json.loads(repaired) if isinstance(repaired, str) else repaired
            if not isinstance(ideas, list):
                raise ValueError(f"repaired result is not a list (got {type(ideas).__name__})")
            logger.info(f"json_repair recovered {len(ideas)} ideias from malformed output")
        except Exception as e2:
            logger.error(f"Failed to parse post_ideas JSON (even with repair): {e2}")
            logger.debug(f"Raw response (first 500): {raw[:500]}")
            return []

    if not isinstance(ideas, list):
        logger.warning(f"Post ideas response is not a list (got {type(ideas).__name__})")
        return []

    # Validate + assign sequential ids; drop malformed items silently.
    # `formato_visual` is required per upgraded prompt — drop items without it.
    valid = []
    required = {"tipo", "emoji", "ideia", "bullets", "fonte", "formato_visual"}
    valid_tipos = {"novidade", "alerta", "atencao", "lifestyle", "medicacao", "evolucao",
                   "mito", "prevencao", "dado", "faq", "checklist", "comparativo"}
    # Note: 'atencao' kept for backwards-compat with reports generated before alerta rename
    for i, idea in enumerate(ideas, 1):
        if not isinstance(idea, dict):
            continue
        if not required.issubset(idea.keys()):
            continue
        if idea.get("tipo") not in valid_tipos:
            # Coerce unknown types to closest match or skip — keep prompt-disciplined
            continue
        if not isinstance(idea.get("bullets"), list) or not idea["bullets"]:
            continue
        if not isinstance(idea.get("fonte"), dict):
            continue
        if not isinstance(idea.get("formato_visual"), dict):
            continue
        # formato_visual: tipo_post + estilo essenciais
        fv = idea["formato_visual"]
        if not fv.get("tipo_post") or not fv.get("estilo"):
            continue
        # Normalize dado_central to string (default empty)
        if not isinstance(fv.get("dado_central"), str):
            fv["dado_central"] = ""
        # Anti-invention rule: graph/number styles REQUIRE non-empty dado_central
        # (number must be quotable from source — empty = Sonnet invented or ignored)
        graph_styles = {"grafico_barras", "grafico_pizza", "grafico_linha", "numero_destacado"}
        if fv["estilo"] in graph_styles and not fv["dado_central"].strip():
            logger.debug(f"Dropping idea pi_{i:03d}: estilo={fv['estilo']} sem dado_central — possível invenção")
            continue
        idea["id"] = f"pi_{i:03d}"
        valid.append(idea)

    logger.info(f"Post ideas generated: {len(valid)}/{len(ideas)} valid")
    return valid


if __name__ == "__main__":
    # Smoke test using the latest committed report
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
    ideas = generate_post_ideas(report)
    print(f"\nGenerated {len(ideas)} post ideas:\n")
    for idea in ideas:
        print(f"  {idea['emoji']} [{idea['tipo']}] {idea['ideia'][:80]}")
        for b in idea["bullets"][:3]:
            print(f"     • {b[:90]}")
        print(f"     fonte: {idea['fonte'].get('publicacao', '?')} — {idea['fonte'].get('titulo_origem', '?')[:60]}")
        print()
