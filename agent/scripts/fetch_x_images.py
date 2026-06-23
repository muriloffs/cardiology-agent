"""PROTÓTIPO (Plano B-imagens) — colhe figuras científicas de cardiologia do X.

Chamada Grok DEDICADA e ISOLADA, separada do pipeline principal. Objetivo:
medir quantas imagens ÚTEIS (gráficos, tabelas, graphical abstracts, slides de
congresso) uma busca focada consegue colher num dia — para decidir se vale ligar
todo dia.

Roda sob demanda (workflow_dispatch). NÃO faz parte do relatório diário.
Saída: data/imagens-x-sample.json (lista de imagens + legenda + fonte).

Defensivo: qualquer falha → salva o que tiver (ou lista vazia), nunca quebra.

Env:
  XAI_API_KEY   — obrigatório
  GROK_MODEL    — default 'grok-4.3'
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

GROK_API_URL = "https://api.x.ai/v1/responses"
GROK_MODEL = os.environ.get("GROK_MODEL", "grok-4.3")
DATA_DIR = Path(__file__).parent.parent.parent / "data"
PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "grok_images_prompt.txt"

# Hosts permitidos (anti-hallucination — descarta URL inventada fora do X CDN)
IMAGE_HOST_WHITELIST = ("pbs.twimg.com", "pic.twitter.com")

MAX_RETRIES = 3
BACKOFF = [30, 60, 120]

# Handles VERIFICADOS (existentes do pipeline + produtores indicados pelo usuário,
# todos confirmados — são contas que o usuário segue). Usados em allowed_x_handles
# na PASSADA DE PRECISÃO. A doc do xAI diz cap de ~10 handles por busca, então
# dividimos em GRUPOS de <=10 e fazemos uma passada por grupo (fan-out) — cada
# escopo estreito força o Grok a enumerar em vez de resumir.
#
# Imagem-pesados (TheEKGGuy, DrRumberger, VLSorrellImages, echocardiac, mswami001)
# foram DEIXADOS DE FORA: postam exame bruto (ECG/eco/CT) que o filtro corta.
HANDLE_GROUPS = [
    # Grupo 1 — produtores/KOLs de alto rendimento (visual abstract, trial, editorial)
    ["EricTopol", "drjohnm", "DrMarthaGulati", "GreggWStone", "purviparwani",
     "iamritu", "onco_cardiology", "MusaSharkawi", "mirvatalasnag", "ottoecho"],
    # Grupo 2 — KOLs restantes + brasileiros + sociedades
    ["ErinMichos", "RoxanaMehran", "CarlosRochitte", "cardiopapers", "echotalk",
     "escardio", "ACCinTouch", "HRSonline", "TCTMD", "American_Heart"],
    # Grupo 3 — revistas / notícias
    ["NEJM", "TheLancet", "JACCJournals", "CircAHA", "JAMACardio", "EuroHeartJ",
     "JACCCRJournals", "Heart_BMJ", "NEJMClinician", "theheartorg"],
]

TARGET_IMAGES = 30  # alvo maior agora (fan-out); abaixo disso, retry da aberta


def _extract_text(data: dict) -> str:
    for item in data.get("output", []):
        if item.get("type") == "message":
            for block in item.get("content", []):
                if block.get("type") == "output_text":
                    return block.get("text", "") or ""
    return ""


def _parse_images(raw: str) -> list[dict[str, Any]]:
    """Parse o array JSON e filtra imagens válidas (URL no whitelist)."""
    txt = raw.strip()
    # Remove cercas de markdown se vierem
    if txt.startswith("```"):
        txt = txt.split("```", 2)[1] if "```" in txt[3:] else txt
        txt = txt.lstrip("json").strip().rstrip("`").strip()
    # Recorta do primeiro [ ao último ]
    a, b = txt.find("["), txt.rfind("]")
    if a != -1 and b != -1:
        txt = txt[a:b + 1]
    try:
        items = json.loads(txt)
    except json.JSONDecodeError:
        try:
            from json_repair import repair_json
            items = json.loads(repair_json(txt))
        except Exception as e:
            logger.error(f"Falha ao parsear JSON de imagens: {e}")
            return []
    if not isinstance(items, list):
        return []

    out = []
    seen = set()
    for it in items:
        if not isinstance(it, dict):
            continue
        url = (it.get("image_url") or "").strip()
        if not url.startswith("https://") or not any(h in url for h in IMAGE_HOST_WHITELIST):
            continue
        if url in seen:
            continue
        seen.add(url)
        out.append({
            "image_url": url,
            "tipo": (it.get("tipo") or "figura").strip(),
            "descricao": (it.get("descricao") or "").strip(),
            "fonte": (it.get("fonte") or "").strip(),
            "categoria_fonte": (it.get("categoria_fonte") or "").strip(),
            "post_url": (it.get("post_url") or "").strip(),
            "assunto": (it.get("assunto") or "").strip(),
        })
    return out


def _call_grok_once(prompt: str, from_date: str, allowed_handles: list[str] | None,
                    retry_feedback: str = "") -> list[dict[str, Any]]:
    """Uma chamada Grok. Se allowed_handles for dado, restringe a busca a essas
    contas (passada de PRECISÃO). Senão, busca aberta (passada de RECALL)."""
    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        return []

    import requests
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    tool: dict[str, Any] = {
        "type": "x_search",
        "from_date": from_date,
        "enable_image_understanding": True,
        "enable_video_understanding": True,   # figuras postadas como video/GIF (congresso)
    }
    if allowed_handles:
        tool["allowed_x_handles"] = allowed_handles[:20]  # cap xAI

    content = prompt + retry_feedback if retry_feedback else prompt
    payload = {
        "model": GROK_MODEL,
        "input": [{"role": "user", "content": content}],
        "tools": [tool],
        "temperature": 0.2,
        "max_output_tokens": 16000,
        "max_tool_calls": 14,
        "parallel_tool_calls": True,
    }

    modo = f"precisão ({len(allowed_handles)} handles)" if allowed_handles else "aberta (hashtags/tema)"
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"Chamada Grok [{modo}] (tentativa {attempt}/{MAX_RETRIES})")
            resp = requests.post(GROK_API_URL, headers=headers, json=payload, timeout=180)
            resp.raise_for_status()
            data = resp.json()
            logger.info(f"  usage: {json.dumps(data.get('usage', {}))[:160]}")
            raw = _extract_text(data)
            if not raw:
                if attempt < MAX_RETRIES:
                    time.sleep(BACKOFF[attempt - 1]); continue
                return []
            imgs = _parse_images(raw)
            logger.info(f"  [{modo}] colhidas: {len(imgs)}")
            return imgs
        except Exception as e:
            logger.error(f"  [{modo}] erro tentativa {attempt}: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(BACKOFF[attempt - 1])
    return []


def _dedupe(images: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen, out = set(), []
    for im in images:
        u = im.get("image_url")
        if u and u not in seen:
            seen.add(u); out.append(im)
    return out


def fetch_x_images() -> list[dict[str, Any]]:
    """Estratégia FAN-OUT (maximiza volume — combate a tendência do x_search de
    'resumir em vez de listar', confirmada na doc do xAI):

    - 1 passada de PRECISÃO por GRUPO de handles (<=10) — escopo estreito força
      o Grok a enumerar todas as figuras daquelas contas.
    - 1 passada de HASHTAGS — agrega a comunidade inteira (produtores conhecidos
      e não), focada nas hashtags ricas em figura.
    - 1 passada ABERTA — long-tail por tema.
    - Agrega tudo + dedupa por URL. Retry da aberta se ficar < TARGET.

    Custo: ~5 chamadas/run. Mais caro que 2, mas é o caminho pra sair de ~25.
    """
    if not os.environ.get("XAI_API_KEY"):
        logger.warning("XAI_API_KEY não setada — pulando.")
        return []

    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    brasilia_tz = timezone(timedelta(hours=-3))
    target = (datetime.now(brasilia_tz) - timedelta(days=1)).strftime("%Y-%m-%d")
    from_date = (datetime.strptime(target, "%Y-%m-%d") - timedelta(days=5)).strftime("%Y-%m-%d")

    todas: list[dict[str, Any]] = []

    # Passadas de precisão — uma por grupo de handles
    for i, grupo in enumerate(HANDLE_GROUPS, 1):
        imgs = _call_grok_once(prompt, from_date, allowed_handles=grupo)
        todas = _dedupe(todas + imgs)
        logger.info(f"Grupo {i} (precisão): +{len(imgs)} → {len(todas)} únicas")

    # Passada de hashtags (aberta, mas com ênfase em buscar pelas hashtags)
    hashtag_emphasis = (
        "\n\nFOCO DESTA BUSCA: priorize as HASHTAGS listadas (FRENTE 2). Busque "
        "ativamente por elas — é onde a comunidade posta figuras de trabalho. "
        "Traga TODAS as figuras científicas de qualidade que encontrar sob essas hashtags."
    )
    hashtags = _call_grok_once(prompt, from_date, allowed_handles=None, retry_feedback=hashtag_emphasis)
    todas = _dedupe(todas + hashtags)
    logger.info(f"Hashtags: +{len(hashtags)} → {len(todas)} únicas")

    # Passada aberta (long-tail por tema)
    aberta = _call_grok_once(prompt, from_date, allowed_handles=None)
    todas = _dedupe(todas + aberta)
    logger.info(f"Aberta: +{len(aberta)} → {len(todas)} únicas")

    # Retry da aberta se ainda baixo
    if len(todas) < TARGET_IMAGES:
        feedback = (f"\n\nATENÇÃO: a busca trouxe poucas imagens ({len(todas)}). Faça MAIS "
                    f"buscas (varie hashtags, termos e datas) e traga TODAS as figuras de "
                    f"qualidade. Alvo: pelo menos {TARGET_IMAGES}.")
        extra = _call_grok_once(prompt, from_date, allowed_handles=None, retry_feedback=feedback)
        todas = _dedupe(todas + extra)
        logger.info(f"Retry: +{len(extra)} → {len(todas)} únicas")

    return todas


def main():
    images = fetch_x_images()

    # Estatística de rendimento (para você avaliar)
    por_tipo: dict[str, int] = {}
    por_cat: dict[str, int] = {}
    for im in images:
        por_tipo[im["tipo"]] = por_tipo.get(im["tipo"], 0) + 1
        por_cat[im["categoria_fonte"]] = por_cat.get(im["categoria_fonte"], 0) + 1

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = {
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "total": len(images),
        "por_tipo": por_tipo,
        "por_categoria_fonte": por_cat,
        "imagens": images,
    }
    out_path = DATA_DIR / "imagens-x-sample.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info("=" * 50)
    logger.info(f"RENDIMENTO: {len(images)} imagens")
    logger.info(f"Por tipo: {por_tipo}")
    logger.info(f"Por fonte: {por_cat}")
    logger.info(f"Salvo em: {out_path}")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
