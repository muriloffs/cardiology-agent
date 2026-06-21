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


def fetch_x_images() -> list[dict[str, Any]]:
    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        logger.warning("XAI_API_KEY não setada — pulando.")
        return []

    prompt = PROMPT_PATH.read_text(encoding="utf-8")

    brasilia_tz = timezone(timedelta(hours=-3))
    target = (datetime.now(brasilia_tz) - timedelta(days=1)).strftime("%Y-%m-%d")
    from_date = (datetime.strptime(target, "%Y-%m-%d") - timedelta(days=5)).strftime("%Y-%m-%d")

    import requests
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": GROK_MODEL,
        "input": [{"role": "user", "content": prompt}],
        "tools": [{
            "type": "x_search",
            "from_date": from_date,
            "enable_image_understanding": True,
        }],
        "temperature": 0.2,
        "max_output_tokens": 16000,   # capturar TODAS as boas (varias por post/fonte) pode gerar array grande
        "max_tool_calls": 12,         # mais buscas = mais imagens colhidas
        "parallel_tool_calls": True,
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"Chamada Grok imagens (tentativa {attempt}/{MAX_RETRIES}, model={GROK_MODEL})")
            resp = requests.post(GROK_API_URL, headers=headers, json=payload, timeout=180)
            resp.raise_for_status()
            data = resp.json()
            usage = data.get("usage", {})
            logger.info(f"Grok usage: {json.dumps(usage)[:200]}")
            raw = _extract_text(data)
            if not raw:
                logger.warning("Sem texto na resposta.")
                if attempt < MAX_RETRIES:
                    time.sleep(BACKOFF[attempt - 1])
                    continue
                return []
            logger.info(f"Preview: {raw[:300]}")
            images = _parse_images(raw)
            logger.info(f"Imagens válidas colhidas: {len(images)}")
            return images
        except Exception as e:
            logger.error(f"Erro na tentativa {attempt}: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(BACKOFF[attempt - 1])
    return []


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
