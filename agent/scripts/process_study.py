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
from urllib.parse import quote

from agent.scripts.study_index import slugify, build_index, linkify_references
from agent.scripts.study_pdf import extract_figures

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Em maquinas com antivirus que faz inspecao de HTTPS (re-assina os certificados
# com uma CA propria que esta na loja do Windows, mas nao no bundle do Python),
# a chamada TLS falha com "CERTIFICATE_VERIFY_FAILED". truststore redireciona a
# validacao para a loja de certificados do SO, resolvendo de forma segura (sem
# desligar a verificacao). Defensivo: se truststore nao estiver instalado (ex:
# no GitHub Actions, onde o certifi padrao ja funciona), apenas segue.
try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

ROOT = Path(__file__).parent.parent.parent
INBOX = ROOT / "study-inbox"
ESTUDOS_DIR = ROOT / "data" / "estudos"
PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "study_prompt.txt"
STUDY_MODEL = os.environ.get("STUDY_MODEL", "claude-opus-4-8")
_FIG_MARKER_RE = re.compile(r"\[\[FIGURA:\s*(.*?)\]\]")
# O PDF original fica no repo (study-inbox/processados/) apos o processamento.
# Link via blob do GitHub = abre o visualizador de PDF (bom no celular).
PDF_BASE = "https://github.com/muriloffs/cardiology-agent/blob/main/study-inbox/processados/"


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
        max_tokens=64000,
        messages=[{"role": "user", "content": content}],
    ) as stream:
        response = stream.get_final_message()
    if getattr(response, "stop_reason", None) == "max_tokens":
        logger.warning(
            "Resposta atingiu max_tokens — o estudo pode estar truncado (documento muito longo)."
        )
    return response.content[0].text


def write_study(estudos_dir: Path, parsed: dict, figs: list[dict], pdf_name: str = "") -> str:
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
    if pdf_name:
        markdown = f"📄 [Abrir o PDF original]({PDF_BASE}{quote(pdf_name)})\n\n" + markdown
    (out / "estudo.md").write_text(markdown, encoding="utf-8")

    # 'mes' agrupa pelo mes em que VOCE estudou (processou), nao pela data de
    # publicacao do artigo — um artigo antigo estudado hoje aparece em "hoje",
    # nao perdido num mes passado. 'data' segue sendo a publicacao (exibida).
    processado_em = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    meta = {
        "slug": slug,
        "titulo": parsed.get("titulo", ""),
        "fonte": parsed.get("fonte", ""),
        "tipo": parsed.get("tipo", ""),
        "data": data,
        "processado_em": processado_em,
        "mes": processado_em[:7],
        "pdf": pdf_name,
    }
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return slug


def process_one(pdf_path: Path, estudos_dir: Path, model: str) -> str | None:
    tmp_figs = estudos_dir / "_tmp_figs"
    try:
        logger.info(f"Processando {pdf_path.name}")
        if tmp_figs.exists():
            shutil.rmtree(tmp_figs)
        figs = extract_figures(pdf_path, tmp_figs)
        raw = _call_claude(pdf_path.read_bytes(), model)
        parsed = parse_study_output(raw)
        slug = write_study(estudos_dir, parsed, figs, pdf_path.name)
        # Move figuras para a pasta final do estudo
        for f in figs:
            src = tmp_figs / f["arquivo"]
            if src.exists():
                shutil.move(str(src), str(estudos_dir / slug / f["arquivo"]))
        logger.info(f"OK: {slug} ({len(figs)} figuras)")
        return slug
    except Exception as e:
        logger.error(f"Falha ao processar {pdf_path.name}: {e}")
        return None
    finally:
        if tmp_figs.exists():
            shutil.rmtree(tmp_figs)


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        logger.error("ANTHROPIC_API_KEY nao setada — abortando.")
        return
    ESTUDOS_DIR.mkdir(parents=True, exist_ok=True)
    processados_dir = INBOX / "processados"
    processados_dir.mkdir(parents=True, exist_ok=True)

    # glob("*.pdf") e nao-recursivo: processados/ nao e re-escaneado intencionalmente
    # (mudar para rglob reprocessaria PDFs ja arquivados)
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
