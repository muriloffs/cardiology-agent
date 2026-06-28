"""Modulo Estudo via Google Drive: puxa PDFs novos de uma pasta do Drive,
processa (process_study) e move os processados para outra pasta no Drive.

Roda 1x/dia (encadeado apos o relatorio) — NAO em tempo real. O usuario larga
PDFs na pasta "Para estudar" (de qualquer aparelho); este job baixa os novos,
gera os estudos e move o PDF para "Estudados" no Drive (renomeado).

DURABILIDADE POR PDF (importante): processa UM PDF por vez e, logo apos cada um:
publica no git (commit+push) e SO ENTAO move o PDF no Drive. Assim cada estudo
pronto vira duravel na hora — um timeout do runner perde no maximo o PDF em
andamento, nunca os ja prontos, e nada e reprocessado (commit antes do move).
Isso resolve o modo de falha do design tudo-ou-nada (lote grande estourava o
timeout, movia/commitava nada, e reprocessava — gastando Opus — todo dia).

Defensivo: erros em itens individuais logam e seguem; nunca derruba o run.

Env:
  ANTHROPIC_API_KEY            — obrigatorio (process_study)
  STUDY_MODEL                  — default 'claude-opus-4-8'
  DRIVE_STUDY_FOLDER_ID        — obrigatorio: id da pasta "Para estudar" (a vigiar)
  DRIVE_DONE_FOLDER_ID         — obrigatorio: id da pasta "Estudados" (destino)
  GOOGLE_SERVICE_ACCOUNT_JSON  — caminho do arquivo OU o JSON inline (secret do GitHub)
  DRIVE_MAX_PER_RUN            — default 20: teto de PDFs por run (limita custo/tempo;
                                 o restante drena nos runs seguintes)
"""
import io
import json
import logging
import os
import random
import re
import shutil
import subprocess
import time
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
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]

# Reutiliza o motor de processamento (1 PDF -> 1 estudo) e o builder do indice.
from agent.scripts.process_study import (
    INBOX, ESTUDOS_DIR, STUDY_MODEL, process_one,
)
from agent.scripts.study_index import build_index


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


def list_pdfs(svc, folder_id: str) -> list[tuple[str, str]]:
    """PDFs que estao DIRETO na pasta (ordenados por nome). Retorna [(id, nome)]."""
    q = f"'{folder_id}' in parents and mimeType='application/pdf' and trashed=false"
    files = svc.files().list(q=q, fields="files(id,name)", pageSize=100,
                             orderBy="name").execute().get("files", [])
    return [(f["id"], f["name"]) for f in files]


def download_pdf(svc, file_id: str, dest: Path) -> None:
    from googleapiclient.http import MediaIoBaseDownload
    buf = io.BytesIO()
    dl = MediaIoBaseDownload(buf, svc.files().get_media(fileId=file_id))
    done = False
    while not done:
        _, done = dl.next_chunk()
    dest.write_bytes(buf.getvalue())


def move_to_folder(svc, file_id: str, dest_id: str, new_name: str | None = None) -> None:
    f = svc.files().get(fileId=file_id, fields="parents").execute()
    prev = ",".join(f.get("parents", []))
    body = {"name": new_name} if new_name else {}
    svc.files().update(fileId=file_id, body=body, addParents=dest_id,
                       removeParents=prev, fields="id").execute()


def _nome_legivel(titulo: str, data: str, fallback: str) -> str:
    """'Titulo do Artigo - 2026-06-25.pdf' (sanitizado p/ Drive)."""
    t = re.sub(r"[\\/:*?\"<>|]+", " ", titulo or "")
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) > 120:                       # corta no ultimo espaco antes de 120
        t = t[:120].rsplit(" ", 1)[0].rstrip(" ,;:-")
    if not t:
        return fallback
    return f"{t} - {data}.pdf" if data else f"{t}.pdf"


def _meta(slug: str) -> tuple[str, str]:
    """(titulo, data) do estudo recem-gerado."""
    try:
        d = json.loads((ESTUDOS_DIR / slug / "meta.json").read_text(encoding="utf-8"))
        return d.get("titulo", ""), d.get("data", "")
    except Exception:
        return "", ""


def _write_index() -> None:
    index = build_index(ESTUDOS_DIR)
    (ESTUDOS_DIR / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


def _git(*args, check=True) -> int:
    return subprocess.run(["git", *args], cwd=str(ROOT)).returncode if not check \
        else subprocess.run(["git", *args], cwd=str(ROOT), check=True).returncode


def _git_config() -> None:
    # so seta se ainda nao houver (nao sobrescreve a config local do usuario)
    if subprocess.run(["git", "config", "user.email"], cwd=str(ROOT),
                      capture_output=True).returncode != 0:
        _git("config", "user.email", "github-actions[bot]@users.noreply.github.com")
        _git("config", "user.name", "github-actions[bot]")


def _commit_push(msg: str) -> bool:
    """Commita data/estudos + study-inbox e da push com retry (corrida com o
    x-images). True se publicou; False se nao havia nada/push falhou."""
    _git("add", "data/estudos", "study-inbox")
    if subprocess.run(["git", "commit", "-m", msg], cwd=str(ROOT)).returncode != 0:
        return False  # nada para commitar
    for i in range(1, 6):
        pulled = subprocess.run(["git", "pull", "--rebase", "origin", "main"], cwd=str(ROOT)).returncode
        pushed = subprocess.run(["git", "push", "origin", "main"], cwd=str(ROOT)).returncode
        if pulled == 0 and pushed == 0:
            logger.info(f"Push OK na tentativa {i}.")
            return True
        logger.warning(f"Tentativa {i} de push falhou — repetindo...")
        time.sleep(random.randint(4, 12))
    logger.error("Push falhou apos 5 tentativas.")
    return False


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

    fila = list_pdfs(svc, folder_id)
    if not fila:
        logger.info("Nenhum PDF novo no Drive — nada a fazer.")
        return

    cap = int(os.environ.get("DRIVE_MAX_PER_RUN", "20"))
    batch = fila[:cap]
    logger.info(f"{len(fila)} PDF(s) na fila; processando {len(batch)} neste run "
                f"(teto={cap}).")

    INBOX.mkdir(parents=True, exist_ok=True)
    ESTUDOS_DIR.mkdir(parents=True, exist_ok=True)
    processados = INBOX / "processados"
    processados.mkdir(parents=True, exist_ok=True)
    _git_config()

    publicados = 0
    for fid, name in batch:
        local = INBOX / name
        try:
            download_pdf(svc, fid, local)
            logger.info(f"Baixado do Drive: {name}")
        except Exception as e:
            logger.error(f"Falha ao baixar {name}: {e}")
            continue

        slug = process_one(local, ESTUDOS_DIR, STUDY_MODEL)
        if not slug:
            local.unlink(missing_ok=True)   # mantem no Drive p/ retry no proximo run
            continue

        # PDF local -> processados/ (serve o link jsDelivr do "Abrir PDF original")
        shutil.move(str(local), str(processados / name))
        _write_index()

        # publica ANTES de mover no Drive — se cair aqui, o PDF fica em "Para
        # estudar" e no maximo gera uma duplicata no proximo run (sem perda).
        if _commit_push(f"chore: estudo do Drive — {slug}"):
            titulo, data = _meta(slug)
            try:
                move_to_folder(svc, fid, done_id, _nome_legivel(titulo, data, name))
                logger.info(f"Movido p/ Estudados: {_nome_legivel(titulo, data, name)}")
            except Exception as e:
                logger.error(f"Estudo publicado, mas falha ao mover {name} no Drive: {e}")
            publicados += 1
        else:
            logger.error(f"Push falhou p/ {slug} — PDF fica em 'Para estudar' p/ retry.")

    restam = len(fila) - publicados
    logger.info(f"Concluido: {publicados}/{len(batch)} publicado(s). "
                f"Restam ~{restam} na fila (drenam nos proximos runs).")


if __name__ == "__main__":
    main()
