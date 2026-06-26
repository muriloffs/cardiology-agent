# agent/scripts/study_pdf.py
"""Extracao de figuras de PDF para o modulo Estudo (PyMuPDF).

Defensivo: erros em itens individuais sao logados e pulados, nunca levantam.
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_figures(pdf_path: Path, out_dir: Path) -> list[dict]:
    import fitz
    out_dir.mkdir(parents=True, exist_ok=True)
    figs: list[dict] = []
    n = 0
    try:
        doc = fitz.open(str(pdf_path))
    except Exception as e:
        logger.error(f"Falha ao abrir PDF {pdf_path}: {e}")
        return []
    try:
        for page_index in range(len(doc)):
            try:
                page = doc[page_index]
                for img in page.get_images(full=True):
                    xref = img[0]
                    try:
                        pix = fitz.Pixmap(doc, xref)
                        if pix.n - pix.alpha >= 4:  # CMYK/outros -> RGB
                            pix = fitz.Pixmap(fitz.csRGB, pix)
                        n += 1
                        nome = f"fig-{n}.png"
                        pix.save(str(out_dir / nome))
                        figs.append({"id": f"fig-{n}", "arquivo": nome, "pagina": page_index + 1})
                    except Exception as e:
                        logger.warning(f"Pulando imagem xref={xref} na pag {page_index+1}: {e}")
            except Exception as e:
                logger.warning(f"Pulando pagina {page_index}: {e}")
    finally:
        doc.close()
    return figs


def render_page(pdf_path: Path, page_index: int, out_path: Path) -> bool:
    import fitz
    try:
        doc = fitz.open(str(pdf_path))
        try:
            page = doc[page_index]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x para legibilidade
            out_path.parent.mkdir(parents=True, exist_ok=True)
            pix.save(str(out_path))
            return True
        finally:
            doc.close()
    except Exception as e:
        logger.error(f"Falha ao renderizar pagina {page_index} de {pdf_path}: {e}")
        return False
