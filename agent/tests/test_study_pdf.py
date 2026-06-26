# agent/tests/test_study_pdf.py
import fitz  # pymupdf
from pathlib import Path
from agent.scripts.study_pdf import extract_figures, render_page


def _make_pdf_with_image(path: Path):
    doc = fitz.open()
    page = doc.new_page()
    # Um pixmap vermelho 32x32 embutido como imagem na página
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 32, 32))
    pix.set_rect(pix.irect, (255, 0, 0))
    page.insert_image(fitz.Rect(10, 10, 110, 110), pixmap=pix)
    doc.save(str(path))
    doc.close()


def test_extract_figures_returns_raster_images(tmp_path):
    pdf = tmp_path / "doc.pdf"
    _make_pdf_with_image(pdf)
    out = tmp_path / "figs"
    out.mkdir()
    figs = extract_figures(pdf, out)
    assert len(figs) >= 1
    assert figs[0]["id"] == "fig-1"
    assert (out / figs[0]["arquivo"]).exists()


def test_extract_figures_empty_pdf(tmp_path):
    pdf = tmp_path / "empty.pdf"
    doc = fitz.open(); doc.new_page(); doc.save(str(pdf)); doc.close()
    out = tmp_path / "figs"; out.mkdir()
    assert extract_figures(pdf, out) == []


def test_render_page_writes_png(tmp_path):
    pdf = tmp_path / "doc.pdf"
    _make_pdf_with_image(pdf)
    target = tmp_path / "page.png"
    assert render_page(pdf, 0, target) is True
    assert target.exists() and target.stat().st_size > 0


def test_render_page_returns_false_on_bad_path(tmp_path):
    result = render_page(tmp_path / "nao-existe.pdf", 0, tmp_path / "x.png")
    assert result is False


def test_extract_figures_bad_path_returns_empty(tmp_path):
    result = extract_figures(tmp_path / "nao-existe.pdf", tmp_path / "figs")
    assert result == []
