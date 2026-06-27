import json
from pathlib import Path
from agent.scripts.process_study import parse_study_output, write_study


def test_parse_study_output_extracts_json():
    raw = 'Aqui está:\n{"titulo":"IC","fonte":"NEJM","tipo":"revisao","data":"2026-06-24","markdown":"# IC\\nTexto"}\nfim'
    out = parse_study_output(raw)
    assert out["titulo"] == "IC"
    assert out["markdown"].startswith("# IC")


def test_parse_study_output_repairs_trailing_comma():
    raw = '{"titulo":"A","fonte":"ESC","tipo":"diretriz","data":"2026-06-01","markdown":"x",}'
    out = parse_study_output(raw)
    assert out["tipo"] == "diretriz"


def test_parse_study_output_raises_on_garbage():
    import pytest
    with pytest.raises(ValueError):
        parse_study_output("sem json aqui")


def test_write_study_creates_files_and_linkifies(tmp_path):
    parsed = {
        "titulo": "Insuficiência Cardíaca",
        "fonte": "@NEJM",
        "tipo": "revisao",
        "data": "2026-06-24",
        "markdown": "## Intro\nTexto.\n\n## Referências citadas\n1. Pfeffer MA. DOI: 10.1056/NEJMoa1409077",
    }
    slug = write_study(tmp_path, parsed, figs=[])
    assert slug == "insuficiencia-cardiaca-2026-06-24"
    estudo_md = (tmp_path / slug / "estudo.md").read_text(encoding="utf-8")
    assert "[10.1056/NEJMoa1409077](https://doi.org/10.1056/NEJMoa1409077)" in estudo_md
    meta = json.loads((tmp_path / slug / "meta.json").read_text(encoding="utf-8"))
    from datetime import datetime, timezone
    hoje = datetime.now(timezone.utc)
    # 'mes' = mes de PROCESSAMENTO (hoje), nao da publicacao do artigo
    assert meta["mes"] == hoje.strftime("%Y-%m")
    assert meta["processado_em"] == hoje.strftime("%Y-%m-%d")
    assert meta["data"] == "2026-06-24"  # data do artigo preservada para exibicao
    assert meta["slug"] == slug


def test_write_study_replaces_figure_markers(tmp_path):
    parsed = {
        "titulo": "T", "fonte": "ESC", "tipo": "diretriz", "data": "2026-06-01",
        "markdown": "Veja [[FIGURA: forest plot de MACE]] no estudo.",
    }
    figs = [{"id": "fig-1", "arquivo": "fig-1.png", "pagina": 3}]
    slug = write_study(tmp_path, parsed, figs=figs)
    md = (tmp_path / slug / "estudo.md").read_text(encoding="utf-8")
    assert "![forest plot de MACE](fig-1.png)" in md
    assert "[[FIGURA" not in md


def test_write_study_figure_marker_without_figure_falls_back(tmp_path):
    parsed = {
        "titulo": "T", "fonte": "ESC", "tipo": "diretriz", "data": "2026-06-01",
        "markdown": "Veja [[FIGURA: grafico ausente]] aqui.",
    }
    slug = write_study(tmp_path, parsed, figs=[])  # no figures available
    md = (tmp_path / slug / "estudo.md").read_text(encoding="utf-8")
    assert "grafico ausente" in md
    assert "[[FIGURA" not in md


def test_write_study_adds_pdf_link(tmp_path):
    parsed = {
        "titulo": "T", "fonte": "ESC", "tipo": "revisao", "data": "2026-06-01",
        "markdown": "Texto do estudo.",
    }
    slug = write_study(tmp_path, parsed, figs=[], pdf_name="meu artigo.pdf")
    md = (tmp_path / slug / "estudo.md").read_text(encoding="utf-8")
    assert "Abrir o PDF original" in md
    assert "raw.githubusercontent.com" in md  # link 'raw' = PDF direto, aba dedicada
    assert "study-inbox/processados/meu%20artigo.pdf" in md  # nome url-encoded
    meta = json.loads((tmp_path / slug / "meta.json").read_text(encoding="utf-8"))
    assert meta["pdf"] == "meu artigo.pdf"
