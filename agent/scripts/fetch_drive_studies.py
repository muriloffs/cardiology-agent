"""Modulo Estudo via Google Drive: puxa PDFs novos de uma pasta do Drive,
processa (process_study) e move os processados para uma subpasta no Drive.

Roda 1x/dia (cron diario) — NAO em tempo real. O usuario larga PDFs na pasta
do Drive (de qualquer aparelho); uma vez por dia este job baixa os novos,
gera os estudos e move o PDF para 'processados' no Drive (para nao repetir).

Defensivo: erros em itens individuais logam e seguem; nunca derruba o run.

Env:
  ANTHROPIC_API_KEY            — obrigatorio (process_study)
  STUDY_MODEL                  — default 'claude-opus-4-8'
  DRIVE_STUDY_FOLDER_ID        — obrigatorio: id da pasta "Para estudar" (a vigiar)
  DRIVE_DONE_FOLDER_ID         — obrigatorio: id da pasta "Estudados" (destino)
  GOOGLE_SERVICE_ACCOUNT_JSON  — caminho do arquivo OU o JSON inline (secret do GitHub)
"""
import io
import json
import logging
import os
import re
from pathlib import Path

# truststore: usa a loja de certificados do SO (resolve TLS em maquina com
# antivirus inspecionando HTTPS). No-op se nao instalado (ex: no GitHub Actions).
try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent.parent
INBOX = ROOT / "study-inbox"
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]


def _drive_service():
    """Cria o cliente do Drive a partir do service account. Aceita o JSON inline
    (secret do GitHub) OU um caminho de arquivo (local)."""
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    sa = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if sa.startswith("{"):
        creds = service_account.Credentials.from_service_account_info(
            json.loads(sa), scopes=DRIVE_SCOPES)
    else:
        path = sa or str(ROOT / "agent" / "google-service-account.json")
        creds = service_account.Credentials.from_service_account_file(path, scopes=DRIVE_SCOPES)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def pull_new_pdfs(svc, folder_id: str, dest: Path) -> list[tuple[str, str]]:
    """Baixa os PDFs que estao DIRETO na pasta (nao na subpasta processados)
    para `dest`. Retorna [(drive_file_id, nome)]."""
    from googleapiclient.http import MediaIoBaseDownload

    q = f"'{folder_id}' in parents and mimeType='application/pdf' and trashed=false"
    files = svc.files().list(q=q, fields="files(id,name)", pageSize=100).execute().get("files", [])
    dest.mkdir(parents=True, exist_ok=True)
    pulled = []
    for f in files:
        try:
            buf = io.BytesIO()
            dl = MediaIoBaseDownload(buf, svc.files().get_media(fileId=f["id"]))
            done = False
            while not done:
                _, done = dl.next_chunk()
            (dest / f["name"]).write_bytes(buf.getvalue())
            pulled.append((f["id"], f["name"]))
            logger.info(f"Baixado do Drive: {f['name']}")
        except Exception as e:
            logger.error(f"Falha ao baixar {f.get('name')}: {e}")
    return pulled


def move_to_folder(svc, file_id: str, dest_id: str, new_name: str | None = None) -> None:
    f = svc.files().get(fileId=file_id, fields="parents").execute()
    prev = ",".join(f.get("parents", []))
    body = {"name": new_name} if new_name else {}
    svc.files().update(fileId=file_id, body=body, addParents=dest_id,
                       removeParents=prev, fields="id").execute()


def _title_map(estudos_dir: Path) -> dict[str, tuple[str, str]]:
    """{ nome_do_pdf_original -> (titulo, data) } a partir dos meta.json gerados."""
    m: dict[str, tuple[str, str]] = {}
    for mp in estudos_dir.glob("*/meta.json"):
        try:
            d = json.loads(mp.read_text(encoding="utf-8"))
            if d.get("pdf"):
                m[d["pdf"]] = (d.get("titulo", ""), d.get("data", ""))
        except Exception:
            pass
    return m


def _nome_legivel(titulo: str, data: str, fallback: str) -> str:
    """'Titulo do Artigo - 2026-06-25.pdf' (sanitizado p/ Drive)."""
    t = re.sub(r"[\\/:*?\"<>|]+", " ", titulo or "")
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) > 120:                       # corta no ultimo espaco antes de 120
        t = t[:120].rsplit(" ", 1)[0].rstrip(" ,;:-")
    if not t:
        return fallback
    return f"{t} - {data}.pdf" if data else f"{t}.pdf"


def main():
    folder_id = os.environ.get("DRIVE_STUDY_FOLDER_ID")
    done_id = os.environ.get("DRIVE_DONE_FOLDER_ID")
    if not folder_id or not done_id:
        logger.error("DRIVE_STUDY_FOLDER_ID e/ou DRIVE_DONE_FOLDER_ID nao setados — abortando.")
        return
    if not os.environ.get("ANTHROPIC_API_KEY"):
        logger.error("ANTHROPIC_API_KEY nao setado — abortando.")
        return

    try:
        svc = _drive_service()
    except Exception as e:
        logger.error(f"Falha ao autenticar no Drive: {e}")
        return

    pulled = pull_new_pdfs(svc, folder_id, INBOX)
    if not pulled:
        logger.info("Nenhum PDF novo no Drive — nada a fazer.")
        return
    logger.info(f"{len(pulled)} PDF(s) baixado(s) — processando...")

    # process_study processa tudo em study-inbox/ (gera estudos, move locais,
    # reconstroi o index). Nao comita (o workflow comita).
    from agent.scripts.process_study import main as process_main
    process_main()

    # so depois de processar, move os PDFs no Drive para "Estudados",
    # renomeando p/ "Titulo do artigo - data.pdf" (legivel).
    tmap = _title_map(ROOT / "data" / "estudos")
    for fid, name in pulled:
        titulo, data = tmap.get(name, ("", ""))
        novo = _nome_legivel(titulo, data, name)
        try:
            move_to_folder(svc, fid, done_id, novo)
            logger.info(f"Movido p/ Estudados como: {novo}")
        except Exception as e:
            logger.error(f"Falha ao mover {name} no Drive: {e}")


if __name__ == "__main__":
    main()
