import json
from pathlib import Path
from agent.scripts.study_index import slugify, build_index, linkify_references


def test_slugify_strips_accents_and_punctuation():
    assert slugify("Insuficiência Cardíaca: FE preservada (HFpEF)") == "insuficiencia-cardiaca-fe-preservada-hfpef"


def test_slugify_collapses_and_trims_hyphens():
    assert slugify("  A  --  B  ") == "a-b"


def test_build_index_groups_by_month(tmp_path):
    for slug, data, mes in [("a", "2026-06-24", "2026-06"),
                            ("b", "2026-06-10", "2026-06"),
                            ("c", "2026-05-30", "2026-05")]:
        d = tmp_path / slug
        d.mkdir()
        (d / "meta.json").write_text(json.dumps(
            {"slug": slug, "titulo": slug.upper(), "fonte": "@NEJM",
             "tipo": "revisao", "data": data, "mes": mes}), encoding="utf-8")
    idx = build_index(tmp_path)
    assert idx["meses_disponiveis"] == ["2026-06", "2026-05"]
    assert [m["slug"] for m in idx["por_mes"]["2026-06"]] == ["a", "b"]  # data desc
    assert idx["por_mes"]["2026-05"][0]["slug"] == "c"


def test_build_index_empty_dir(tmp_path):
    idx = build_index(tmp_path)
    assert idx["por_mes"] == {}
    assert idx["meses_disponiveis"] == []


def test_linkify_doi_inline():
    out = linkify_references("Pfeffer MA et al. DOI: 10.1056/NEJMoa1409077")
    assert "[10.1056/NEJMoa1409077](https://doi.org/10.1056/NEJMoa1409077)" in out


def test_linkify_doi_strips_trailing_punctuation():
    # DOI seguido de ')' e '.' (fechando um parenteses no texto-fonte):
    # a pontuacao nao pode entrar na URL, mas deve ser preservada apos o link.
    out = linkify_references("Ref. DOI: 10.1056/NEJMra052717).")
    assert "[10.1056/NEJMra052717](https://doi.org/10.1056/NEJMra052717)" in out
    assert out.rstrip().endswith(").")


def test_linkify_doi_strips_trailing_semicolon():
    out = linkify_references("DOI: 10.1093/eurheartj/ehz714;")
    assert "[10.1093/eurheartj/ehz714](https://doi.org/10.1093/eurheartj/ehz714)" in out
    assert out.rstrip().endswith(";")


def test_linkify_pmid():
    out = linkify_references("Smith J. PMID: 31535829")
    assert "[PMID 31535829](https://pubmed.ncbi.nlm.nih.gov/31535829/)" in out


def test_linkify_reference_in_section_gets_scholar_link():
    md = "## Referências citadas\n12. Doe J. Heart Failure Review. Circulation 2020"
    out = linkify_references(md)
    assert "scholar.google.com/scholar?q=" in out
    assert "🔍 buscar" in out


def test_linkify_reference_with_doi_also_gets_scholar():
    md = "## Referências\n26. Sandner S. DAPT vein graft. JAMA 2022. DOI: 10.1001/jama.2022.11966"
    out = linkify_references(md)
    assert "[10.1001/jama.2022.11966](https://doi.org/10.1001/jama.2022.11966)" in out
    assert "scholar.google.com/scholar?q=" in out


def test_linkify_numbered_line_outside_refs_untouched():
    # Lista numerada fora da secao de referencias (ex: Consideracoes Praticas)
    # NAO deve ganhar link de busca.
    md = "## Considerações Práticas\n1. Inicie aspirina dentro de 6 horas."
    out = linkify_references(md)
    assert "scholar.google" not in out
    assert out == md


def test_linkify_leaves_prose_without_refs_untouched():
    txt = "A HFpEF representa metade dos casos."
    assert linkify_references(txt) == txt
