"""Fetch cardiology Substack posts via Gemini API with Google Search grounding.

Substack blocks GitHub Actions runner IPs (datacenter blocking via Cloudflare),
so direct RSS fails with 403 in CI. Gemini grounding works around this by
having Google's crawler fetch the content.

Pattern (validated empirically by user research): grounded query asking for
recent posts from a specific Substack publication → multi-line text response
with rich fields (TITLE/URL/DATE/AUTOR/TEMA/BULLETS/RESUMO/TAGS) → block
parser → structured items.

12 Substacks targeted (9 international + 3 Brazilian), 7-day window.

Returns a flat list of substack items for direct injection into report['substacks'].
"""

import os
import re
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-2.5-pro"
GEMINI_CALL_TIMEOUT = 120  # Pro is 2-3x slower than Flash, give more headroom
DEFAULT_DAYS_BACK = 7  # Substacks publish 1-3x/week
DEFAULT_MAX_ITEMS = 3


# ──────────────────────────────────────────────────────────────────────
# CLIENT + GROUNDED CALL HELPER (same pattern as fetch_gemini_external.py)
# ──────────────────────────────────────────────────────────────────────

def _get_client():
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return None
    try:
        from google import genai
        return genai.Client(api_key=api_key)
    except ImportError:
        logger.error("google-genai SDK not installed — pip install google-genai")
        return None


def _extract_text(response) -> str:
    if hasattr(response, "text") and response.text:
        return response.text.strip()
    if hasattr(response, "candidates") and response.candidates:
        parts_text = []
        for cand in response.candidates:
            if hasattr(cand, "content") and cand.content and hasattr(cand.content, "parts"):
                for part in cand.content.parts or []:
                    if hasattr(part, "text") and part.text:
                        parts_text.append(part.text)
        return "\n".join(parts_text).strip()
    return ""


def _grounded_call(client, prompt: str, label: str, _is_retry: bool = False) -> str:
    """Make 1 grounded Gemini Pro call with two retry layers.

    Layer 1 — server errors (503/UNAVAILABLE, 429/RESOURCE_EXHAUSTED): exponential
    backoff 2s, 4s, 8s. Transient overload errors (seen 2026-05-11 when all 12
    Substacks failed simultaneously due to Pro overload).

    Layer 2 — empty text (known grounding pathology): single retry with bumped
    temperature + prompt nudge.
    """
    import time as _time
    SERVER_ERROR_SIGNALS = ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "INTERNAL")
    MAX_SERVER_RETRIES = 3
    BACKOFFS = (2, 4, 8)

    def _call_once(prompt_text: str, temp: float):
        from google.genai import types
        config = types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=temp,
        )
        return client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt_text,
            config=config,
        )

    response = None
    last_err: Exception | None = None
    for attempt in range(MAX_SERVER_RETRIES + 1):
        try:
            response = _call_once(prompt, 0.5 if _is_retry else 0.2)
            last_err = None
            break
        except Exception as e:
            last_err = e
            msg = str(e)
            is_transient = any(sig in msg for sig in SERVER_ERROR_SIGNALS)
            if not is_transient or attempt >= MAX_SERVER_RETRIES:
                break
            wait = BACKOFFS[min(attempt, len(BACKOFFS) - 1)]
            logger.info(f"[{label}] Gemini transient error — backing off {wait}s (attempt {attempt+1}/{MAX_SERVER_RETRIES})")
            _time.sleep(wait)

    if last_err is not None:
        logger.warning(f"[{label}] Gemini call failed (after backoff): {type(last_err).__name__}: {last_err}")
        return ""

    text = _extract_text(response)
    if not text and not _is_retry:
        logger.info(f"[{label}] Empty response — retrying once with temp=0.5")
        retry_prompt = prompt + "\n\nProceed and respond with the requested format now."
        return _grounded_call(client, retry_prompt, label, _is_retry=True)
    if not text:
        logger.warning(f"[{label}] Gemini returned empty text (after retry)")
    elif _is_retry:
        logger.info(f"[{label}] Retry succeeded")
    return text


# ──────────────────────────────────────────────────────────────────────
# RICH BLOCK PARSER
# ──────────────────────────────────────────────────────────────────────

def _parse_substack_blocks(text: str) -> list[dict]:
    """Parse Gemini rich-format response into a list of post dicts.

    Expected format per post (separated by '---' or blank lines):
        TITLE: <title>
        URL: <url>
        DATE: <YYYY-MM-DD>
        AUTOR: <author>
        TEMA: <theme>
        BULLETS:
        - bullet 1
        - bullet 2
        RESUMO: <summary>
        TAGS: tag1, tag2, tag3
    """
    if not text or text.strip().upper() == "NONE":
        return []

    # Strip markdown code fences if Gemini added any
    text = re.sub(r"```\w*\n?", "", text)
    text = text.replace("```", "")

    # Split into post blocks. Try '---' separator first; fall back to double newline
    if "---" in text:
        blocks = re.split(r"\n\s*---+\s*\n", text)
    else:
        blocks = re.split(r"\n\s*\n+", text)

    posts = []
    for raw_block in blocks:
        block = raw_block.strip()
        if not block or block.upper() == "NONE":
            continue

        post = _parse_single_block(block)
        if post and post.get("titulo") and post.get("url"):
            posts.append(post)

    return posts


def _parse_single_block(block: str) -> dict | None:
    """Extract fields from one post block (Nível-1: includes 3 new contextual fields)."""
    lines = block.split("\n")

    post = {
        "titulo": "",
        "titulo_pt": "",
        "url": "",
        "data_pub": "",
        "autor": "",
        "tema": "",
        "bullets": [],
        "resumo": "",
        "tags": [],
        "quem_se_aplica": "",
        "evidencia_chave": "",
        "contraponto": "",
    }

    current_field = None
    bullet_buffer = []

    # Label → post-field mapping (multi-line capable for resumo/contraponto/quem_se_aplica/evidencia_chave)
    LABEL_MAP = {
        "TITLE": "titulo", "TITULO": "titulo",
        "TITLE_PT": "titulo_pt", "TITULO_PT": "titulo_pt",
        "URL": "url",
        "DATE": "data_pub", "DATA": "data_pub",
        "AUTOR": "autor", "AUTHOR": "autor",
        "TEMA": "tema",
        "RESUMO": "resumo",
        "QUEM_SE_APLICA": "quem_se_aplica", "QUEMSEAPLICA": "quem_se_aplica",
        "EVIDENCIA_CHAVE": "evidencia_chave", "EVIDENCIACHAVE": "evidencia_chave",
        "CONTRAPONTO": "contraponto",
    }
    MULTILINE_FIELDS = {"resumo", "quem_se_aplica", "evidencia_chave", "contraponto", "titulo", "titulo_pt"}

    for raw_line in lines:
        line = raw_line.rstrip()
        if not line.strip():
            continue

        m = re.match(r"^\s*([A-Za-z_ÁÉÍÓÚá-ú]+)\s*:\s*(.*)$", line)
        if m:
            label = m.group(1).upper().replace(" ", "_")
            value = m.group(2).strip()

            if label in LABEL_MAP:
                field = LABEL_MAP[label]
                current_field = field
                if field == "url":
                    v = re.sub(r"^\[.*?\]\((.*)\)$", r"\1", value)
                    post["url"] = v.strip("()<>[] ")
                else:
                    post[field] = _strip_markdown(value)
            elif label == "BULLETS":
                current_field = "bullets"
                if value:
                    bullet_buffer.append(value)
            elif label == "TAGS":
                current_field = "tags"
                post["tags"] = [t.strip().lstrip("#") for t in value.split(",") if t.strip()]
            else:
                current_field = None
            continue

        # Continuation lines for current_field
        stripped = line.strip()
        if current_field == "bullets":
            bullet_text = re.sub(r"^[\-\*•\d\.\)]+\s*", "", stripped).strip()
            if bullet_text:
                bullet_buffer.append(bullet_text)
        elif current_field in MULTILINE_FIELDS:
            post[current_field] = (post[current_field] + " " + stripped).strip()

    if bullet_buffer:
        post["bullets"] = [_strip_markdown(b) for b in bullet_buffer[:8]]

    if not post["url"].startswith("http"):
        return None
    if not post["titulo"]:
        return None

    return post


def _strip_markdown(s: str) -> str:
    """Remove common markdown artifacts from Gemini output."""
    if not s:
        return s
    # Bold/italic **text** or *text*
    s = re.sub(r"\*+([^*]+)\*+", r"\1", s)
    # Backticks
    s = s.replace("`", "")
    # Citation markers like [1], [2] that Gemini sometimes adds
    s = re.sub(r"\[\d+\]", "", s)
    return s.strip()


# ──────────────────────────────────────────────────────────────────────
# PROMPT BUILDER
# ──────────────────────────────────────────────────────────────────────

def _build_substack_prompt(
    publication_name: str,
    publication_url: str,
    days_back: int = DEFAULT_DAYS_BACK,
    max_items: int = DEFAULT_MAX_ITEMS,
) -> str:
    """Build a Substack fetch prompt with deep clinical analysis (Pro + Nível 1).

    Title, tema, bullets, resumo, and contextual fields ALL in PT-BR — the
    dashboard is consumed by a Brazilian cardiologist. Author stays in
    original form. URL resolves to original post on click.

    Nível-1 enhancements: 5-7 bullets (vs 3), 5-7 sentence resumo (vs 2-3),
    plus 3 new contextual fields: quem_se_aplica, evidencia_chave, contraponto.
    """
    return f"""Você é um cardiologista revisor sênior analisando posts recentes da newsletter "{publication_name}" ({publication_url}) para um dashboard clínico brasileiro.

Use Google Search para encontrar os {max_items} posts mais recentes (últimos {days_back} dias). Leia o conteúdo de cada post com profundidade — não apenas o título.

Para cada post, responda EXATAMENTE neste formato. Separe posts com uma linha contendo apenas '---'.

TITLE: <título ORIGINAL do post no idioma em que foi publicado (sem traduzir)>
TITLE_PT: <tradução do título em português brasileiro — natural, fluente, não literal. Preserve nomes próprios e termos técnicos consagrados (TAVR, HFpEF, MACE, etc). Se o título já está em PT-BR, repita igual ao original.>
URL: <URL completa do post>
DATE: <data de publicação no formato YYYY-MM-DD>
AUTOR: <nome do autor original, sem traduzir>
TEMA: <tema principal em 2 a 5 palavras em português brasileiro>
BULLETS:
- <takeaway clínico 1 — frase curta, específica (números/nomes/contexto quando houver)>
- <takeaway clínico 2>
- <takeaway clínico 3>
- <takeaway clínico 4>
- <takeaway clínico 5>
- <takeaway 6 se relevante>
- <takeaway 7 se relevante>
RESUMO: <resumo em 5-7 frases em português brasileiro. Inclua: (1) o que o autor argumenta, (2) o contexto clínico/científico, (3) a evidência citada, (4) a conclusão prática. Densidade editorial, não feed-style.>
QUEM_SE_APLICA: <1-2 frases sobre o perfil de paciente / contexto clínico em que a discussão importa (ex: "Pacientes com FA não-valvar e CHA2DS2-VASc ≥ 2", "Cardiologistas que prescrevem PCSK9i")>
EVIDENCIA_CHAVE: <1 frase com o datapoint mais relevante citado no post — número, trial, estudo (ex: "HR 0,75 IC 95% 0,65-0,86 no VESALIUS-CV n=12.301", "Redução de 40% em tempo de procedimento")>
CONTRAPONTO: <1-2 frases com o caveat/crítica/limitação principal — o "porém". Se o post não tem contraponto óbvio, escreva "Sem contraponto significativo neste post.">
TAGS: <3 a 5 keywords curtas separadas por vírgulas, em português ou termos técnicos consagrados (TAVR, HFpEF, GLP-1, SGLT2) — sem '#'>

REGRAS:
- Idioma OBRIGATÓRIO português brasileiro para TITLE/TEMA/BULLETS/RESUMO/QUEM_SE_APLICA/EVIDENCIA_CHAVE/CONTRAPONTO
- Termos técnicos consagrados em inglês são OK
- Não invente números/citações que não estão no post
- Não use markdown (** ou ##)
- Plain text only, sem JSON
- Se nenhum post no período: responda apenas NONE"""


# ──────────────────────────────────────────────────────────────────────
# 12 SUBSTACK FETCHERS
# ──────────────────────────────────────────────────────────────────────

def _make_fetcher(name: str, slug: str, url: str, categoria: str, default_autor: str = ""):
    """Factory: returns a fetcher function for a single Substack."""
    def fetch(client):
        prompt = _build_substack_prompt(name, url)
        text = _grounded_call(client, prompt, slug)
        posts = _parse_substack_blocks(text)
        for p in posts:
            p["publicacao"] = name
            p["fonte_origem"] = slug
            p["categoria"] = categoria
            if not p.get("autor") and default_autor:
                p["autor"] = default_autor
        # Diagnostic: if Gemini returned text but parser got 0 blocks, log a
        # preview so we can iterate the prompt/parser. Frequent silent 0 results
        # (e.g. 'skeptical' on Pro) usually mean response shape changed.
        if text and not posts:
            preview = text[:300].replace("\n", " ⏎ ")
            logger.warning(f"[{slug}] Gemini returned text but parser got 0 blocks. Preview: {preview!r}")
        logger.info(f"Gemini Substack [{slug}]: {len(posts)} posts")
        return posts
    fetch.__name__ = f"fetch_{slug}"
    return fetch


# Definitions: (name, slug, url, categoria, default_autor)
SUBSTACKS_INT = [
    ("Ground Truths",                 "topol",         "erictopol.substack.com",            "tech-policy",         "Eric Topol"),
    ("Sensible Medicine",             "sensible_med",  "sensiblemed.substack.com",          "trials-critique",     ""),
    ("The Skeptical Cardiologist",    "skeptical",     "theskepticalcardiologist.substack.com", "consumer-tech",   "Anthony Pearson"),
    ("Cardiology Trial's Substack",   "cardio_trials", "cardiologytrials.substack.com",     "trials-summary",      ""),
    ("500 Rules of Cardiology",       "thompson",      "pauldthompsonmd.substack.com",      "clinical-pearls",     "Paul D. Thompson"),
    ("Numerical Heart",               "numerical",     "numericalheart.substack.com",       "ai-genomics",         "Venk Murthy"),
    ("Dr Paddy Barrett",              "barrett",       "drpaddybarrett.substack.com",       "prevention-philosophy", "Paddy Barrett"),
    ("Gregory Katz's Substack",       "gkatz",         "gregorykatz.substack.com",          "education",           "Gregory Katz"),
    ("CardioNerds Substack",          "cardionerds",   "cardionerds.substack.com",          "education",           ""),
]

SUBSTACKS_BR = [
    ("DozeNews / Doze por Oito",      "dozenews",      "dozenews.com.br",                   "br-clinical",         ""),
    ("Jornal do Clube da Cardio",     "clubedacardio", "clubedacardio.substack.com",        "br-congress",         ""),
    ("Cardio DF",                     "cardiodf",      "cardiodf.substack.com",             "br-clinical",         ""),
]

ALL_SUBSTACKS = SUBSTACKS_INT + SUBSTACKS_BR


# ──────────────────────────────────────────────────────────────────────
# ORCHESTRATOR
# ──────────────────────────────────────────────────────────────────────

def fetch_all_substacks() -> list[dict[str, Any]]:
    """Run all 12 Substack fetchers in parallel.

    Returns:
        List of substack post dicts (flat). Empty if API key missing or all fail.
    """
    client = _get_client()
    if not client:
        logger.warning("GOOGLE_API_KEY not set — Substack fetcher skipped")
        return []

    fetchers = [
        (slug, _make_fetcher(name, slug, url, cat, autor))
        for (name, slug, url, cat, autor) in ALL_SUBSTACKS
    ]

    posts: list[dict] = []
    seen_urls: set[str] = set()

    # 3 workers respects Flash rate limits with safety margin
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(fn, client): slug for slug, fn in fetchers}
        for future in as_completed(futures):
            slug = futures[future]
            try:
                result = future.result(timeout=GEMINI_CALL_TIMEOUT)
                for p in result:
                    url = p.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        posts.append(p)
            except Exception as e:
                logger.error(f"Substack fetcher [{slug}] failed: {e}")

    # Assign sequential IDs
    for i, p in enumerate(posts, 1):
        p["id"] = f"sub_{i:03d}"

    logger.info(f"Gemini Substacks TOTAL: {len(posts)} unique posts from {len(ALL_SUBSTACKS)} sources")
    return posts


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.INFO)

    result = fetch_all_substacks()
    print(f"\n{'=' * 60}")
    print(f"Total Substack posts: {len(result)}")
    print(f"{'=' * 60}\n")
    for item in result[:5]:
        print(f"[{item['fonte_origem']}] {item['publicacao']} — {item['autor']}")
        print(f"  📄 {item['titulo']}")
        print(f"  🔖 Tema: {item.get('tema', '')}")
        print(f"  📝 {item.get('resumo', '')[:150]}")
        print(f"  🔗 {item['url']}")
        print()
