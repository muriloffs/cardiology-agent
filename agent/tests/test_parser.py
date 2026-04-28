"""Tests for JSON parser with schema validation."""

import json
import pytest
from agent.parser import parse_report, ParsingError


# ============================================================================
# Shared Fixtures and Factories
# ============================================================================

def make_article(id="art_001", titulo="Sample Article", publicacao="Nature Reviews", classe="A", score=9.0,
                 categoria_fonte="revista", emoji="📰", resumo="Sample summary", impacto_clinico="High impact",
                 autores=None, **kwargs):
    """Factory for creating test articles."""
    article = {
        "id": id,
        "titulo": titulo,
        "publicacao": publicacao,
        "classe": classe,
        "score": score,
        "categoria_fonte": categoria_fonte,
        "emoji": emoji,
        "resumo": resumo,
        "impacto_clinico": impacto_clinico,
        "links": {
            "url": "https://example.com/article",
            "doi": "10.1038/example"
        }
    }
    if autores is not None:
        article["autores"] = autores
    article.update(kwargs)
    return article


def make_resumo(total_artigos=15, tempo_leitura_minutos=15, classe_a_count=5, classe_b_count=7, classe_c_count=3):
    """Factory for creating test resumo objects."""
    return {
        "total_artigos": total_artigos,
        "tempo_leitura_minutos": tempo_leitura_minutos,
        "classe_a_count": classe_a_count,
        "classe_b_count": classe_b_count,
        "classe_c_count": classe_c_count
    }


def make_report(relatorio_data="2026-04-28", gerado_em="2026-04-28T03:15:00Z", resumo=None, featured=None, artigos=None):
    """Factory for creating test reports."""
    return {
        "relatorio_data": relatorio_data,
        "gerado_em": gerado_em,
        "resumo": resumo or make_resumo(),
        "featured": featured or [make_article(id="featured_1")],
        "artigos": artigos or [make_article(id="art_001")]
    }


def to_json(obj):
    """Convert object to JSON string."""
    return json.dumps(obj)


# ============================================================================
# TestValidReportParsing - Happy path and boundary cases
# ============================================================================

class TestValidReportParsing:
    """Valid parsing scenarios."""

    def test_valid_minimal_report(self):
        """Parse valid report with minimal fields."""
        report = make_report()
        result = parse_report(to_json(report))
        assert result['relatorio_data'] == "2026-04-28"
        assert result['gerado_em'] == "2026-04-28T03:15:00Z"

    def test_valid_report_with_multiple_articles(self):
        """Parse report with multiple articles."""
        articles = [
            make_article(id="art_001", classe="A", score=9.0),
            make_article(id="art_002", classe="B", score=7.0),
            make_article(id="art_003", classe="C", score=5.0)
        ]
        report = make_report(artigos=articles)
        result = parse_report(to_json(report))
        assert len(result['artigos']) == 3

    def test_valid_report_with_authors(self):
        """Parse article with authors list."""
        article = make_article(autores=["Dr. Smith", "Dr. Jones"])
        report = make_report(artigos=[article])
        result = parse_report(to_json(report))
        assert result['artigos'][0]['autores'] == ["Dr. Smith", "Dr. Jones"]

    def test_valid_score_boundaries_classe_a(self):
        """Classe A accepts scores 8.0-10.0."""
        for score in [8.0, 9.0, 10.0]:
            article = make_article(classe="A", score=score)
            report = make_report(artigos=[article])
            result = parse_report(to_json(report))
            assert result['artigos'][0]['score'] == score

    def test_valid_score_boundaries_classe_b(self):
        """Classe B accepts scores 6.0-7.9."""
        for score in [6.0, 6.5, 7.9]:
            article = make_article(classe="B", score=score)
            report = make_report(artigos=[article])
            result = parse_report(to_json(report))
            assert result['artigos'][0]['score'] == score

    def test_valid_score_boundaries_classe_c(self):
        """Classe C accepts scores 4.0-5.9."""
        for score in [4.0, 4.5, 5.9]:
            article = make_article(classe="C", score=score)
            report = make_report(artigos=[article])
            result = parse_report(to_json(report))
            assert result['artigos'][0]['score'] == score

    def test_valid_link_combinations(self):
        """Parse various valid link combinations."""
        test_cases = [
            {"url": "https://example.com"},
            {"doi": "10.1038/example"},
            {"pubmed": "12345678"},
            {"url": "https://example.com", "doi": "10.1038/example", "pubmed": "12345678"}
        ]
        for links in test_cases:
            article = make_article(links=links)
            report = make_report(artigos=[article])
            result = parse_report(to_json(report))
            assert result['artigos'][0]['links'] == links


# ============================================================================
# TestMissingRequiredFields - Top-level and nested field validation
# ============================================================================

class TestMissingRequiredFields:
    """Missing required field scenarios."""

    def test_missing_relatorio_data(self):
        """Raise error when relatorio_data is missing."""
        report = make_report()
        del report['relatorio_data']
        with pytest.raises(ParsingError, match="Missing required fields.*relatorio_data"):
            parse_report(to_json(report))

    def test_missing_resumo(self):
        """Raise error when resumo is missing."""
        report = make_report()
        del report['resumo']
        with pytest.raises(ParsingError, match="Missing required fields.*resumo"):
            parse_report(to_json(report))

    def test_missing_article_titulo(self):
        """Raise error when article titulo is missing."""
        article = make_article()
        del article['titulo']
        report = make_report(artigos=[article])
        with pytest.raises(ParsingError, match="artigos\\[0\\].*missing required fields.*titulo"):
            parse_report(to_json(report))

    def test_missing_featured_classe(self):
        """Raise error when featured article classe is missing."""
        featured = make_article()
        del featured['classe']
        report = make_report(featured=[featured])
        with pytest.raises(ParsingError, match="featured\\[0\\].*missing required fields.*classe"):
            parse_report(to_json(report))

    def test_missing_resumo_total_artigos(self):
        """Raise error when resumo total_artigos is missing."""
        resumo = make_resumo()
        del resumo['total_artigos']
        report = make_report(resumo=resumo)
        with pytest.raises(ParsingError, match="resumo.*missing required fields.*total_artigos"):
            parse_report(to_json(report))


# ============================================================================
# TestResumoFieldValidation - Type and range validation
# ============================================================================

class TestResumoFieldValidation:
    """Resumo object validation."""

    def test_resumo_total_artigos_not_int(self):
        """Reject non-integer total_artigos."""
        resumo = make_resumo(total_artigos="15")
        report = make_report(resumo=resumo)
        with pytest.raises(ParsingError, match="resumo.total_artigos.*must be a number"):
            parse_report(to_json(report))

    def test_resumo_total_artigos_negative(self):
        """Reject negative total_artigos."""
        resumo = make_resumo(total_artigos=-1)
        report = make_report(resumo=resumo)
        with pytest.raises(ParsingError, match="resumo.total_artigos.*must be non-negative"):
            parse_report(to_json(report))

    def test_resumo_classe_a_count_is_bool(self):
        """Reject boolean value for classe_a_count."""
        resumo = make_resumo(classe_a_count=True)
        report = make_report(resumo=resumo)
        with pytest.raises(ParsingError, match="resumo.classe_a_count.*must be a number, not boolean"):
            parse_report(to_json(report))

    def test_resumo_tempo_leitura_float(self):
        """Accept float for tempo_leitura_minutos."""
        resumo = make_resumo(tempo_leitura_minutos=15.5)
        report = make_report(resumo=resumo)
        result = parse_report(to_json(report))
        assert result['resumo']['tempo_leitura_minutos'] == 15.5

    def test_resumo_classe_counts_match_total(self):
        """Accept valid class distribution."""
        resumo = make_resumo(total_artigos=15, classe_a_count=5, classe_b_count=7, classe_c_count=3)
        report = make_report(resumo=resumo)
        result = parse_report(to_json(report))
        assert result['resumo']['classe_a_count'] == 5


# ============================================================================
# TestArticleValidation - Article structure validation
# ============================================================================

class TestArticleValidation:
    """Article field validation."""

    def test_article_titulo_empty_string(self):
        """Reject empty titulo."""
        article = make_article(titulo="")
        report = make_report(artigos=[article])
        with pytest.raises(ParsingError, match="artigos\\[0\\].titulo.*must not be empty"):
            parse_report(to_json(report))

    def test_article_titulo_whitespace_only(self):
        """Reject whitespace-only titulo."""
        article = make_article(titulo="   ")
        report = make_report(artigos=[article])
        with pytest.raises(ParsingError, match="artigos\\[0\\].titulo.*must not be empty"):
            parse_report(to_json(report))

    def test_article_publicacao_not_string(self):
        """Reject non-string publicacao."""
        article = make_article(publicacao=123)
        report = make_report(artigos=[article])
        with pytest.raises(ParsingError, match="artigos\\[0\\].publicacao.*must be a string"):
            parse_report(to_json(report))

    def test_article_categoria_fonte_invalid(self):
        """Reject invalid categoria_fonte."""
        article = make_article(categoria_fonte="livro")
        report = make_report(artigos=[article])
        with pytest.raises(ParsingError, match="artigos\\[0\\].categoria_fonte"):
            parse_report(to_json(report))

    def test_article_categoria_fonte_valid_options(self):
        """Accept all valid categoria_fonte options."""
        valid_categories = ["revista", "podcast", "twitter", "substack", "x/twitter"]
        for category in valid_categories:
            article = make_article(categoria_fonte=category)
            report = make_report(artigos=[article])
            result = parse_report(to_json(report))
            assert result['artigos'][0]['categoria_fonte'] == category

    def test_article_emoji_empty(self):
        """Reject empty emoji."""
        article = make_article(emoji="")
        report = make_report(artigos=[article])
        with pytest.raises(ParsingError, match="artigos\\[0\\].emoji.*must not be empty"):
            parse_report(to_json(report))

    def test_article_resumo_length(self):
        """Accept long resumo text."""
        long_resumo = "x" * 500
        article = make_article(resumo=long_resumo)
        report = make_report(artigos=[article])
        result = parse_report(to_json(report))
        assert result['artigos'][0]['resumo'] == long_resumo

    def test_article_impacto_clinico_empty(self):
        """Reject empty impacto_clinico."""
        article = make_article(impacto_clinico="")
        report = make_report(artigos=[article])
        with pytest.raises(ParsingError, match="artigos\\[0\\].impacto_clinico.*must not be empty"):
            parse_report(to_json(report))

    def test_featured_article_has_no_autores(self):
        """Accept featured article without autores field."""
        featured = make_article(id="featured_1")
        # autores is optional
        assert 'autores' not in featured
        report = make_report(featured=[featured])
        result = parse_report(to_json(report))
        assert 'autores' not in result['featured'][0]

    def test_article_with_single_author(self):
        """Accept single author in autores list."""
        article = make_article(autores=["Dr. Smith"])
        report = make_report(artigos=[article])
        result = parse_report(to_json(report))
        assert result['artigos'][0]['autores'] == ["Dr. Smith"]

    def test_article_autores_empty_string(self):
        """Reject empty string in autores list."""
        article = make_article(autores=["Dr. Smith", "", "Dr. Jones"])
        report = make_report(artigos=[article])
        with pytest.raises(ParsingError, match="artigos\\[0\\].autores\\[1\\].*must be non-empty string"):
            parse_report(to_json(report))

    def test_article_autores_not_list(self):
        """Reject autores if not a list."""
        article = make_article(autores="Dr. Smith")
        report = make_report(artigos=[article])
        with pytest.raises(ParsingError, match="artigos\\[0\\].autores.*must be a list"):
            parse_report(to_json(report))

    def test_article_links_missing(self):
        """Raise error when links field is missing."""
        article = make_article()
        del article['links']
        report = make_report(artigos=[article])
        with pytest.raises(ParsingError, match="artigos\\[0\\].*missing required fields.*links"):
            parse_report(to_json(report))

    def test_article_multiple_in_artigos(self):
        """Parse multiple articles with different classes."""
        articles = [
            make_article(id="art_001", classe="A", score=9.5),
            make_article(id="art_002", classe="B", score=7.2),
            make_article(id="art_003", classe="C", score=4.8)
        ]
        report = make_report(artigos=articles)
        result = parse_report(to_json(report))
        assert len(result['artigos']) == 3
        assert result['artigos'][0]['classe'] == "A"
        assert result['artigos'][1]['classe'] == "B"
        assert result['artigos'][2]['classe'] == "C"


# ============================================================================
# TestScoreClasseConsistency - Score/classe boundary enforcement
# ============================================================================

class TestScoreClasseConsistency:
    """Score and classe consistency validation."""

    def test_classe_a_score_too_low(self):
        """Reject Classe A with score 7.9."""
        article = make_article(classe="A", score=7.9)
        report = make_report(artigos=[article])
        with pytest.raises(ParsingError, match="Classe A requires score between 8.0 and 10.0"):
            parse_report(to_json(report))

    def test_classe_a_score_too_high(self):
        """Reject Classe A with score 10.1."""
        article = make_article(classe="A", score=10.1)
        report = make_report(artigos=[article])
        with pytest.raises(ParsingError, match="must be between 0 and 10"):
            parse_report(to_json(report))

    def test_classe_a_score_exactly_8(self):
        """Accept Classe A with score exactly 8.0."""
        article = make_article(classe="A", score=8.0)
        report = make_report(artigos=[article])
        result = parse_report(to_json(report))
        assert result['artigos'][0]['score'] == 8.0

    def test_classe_a_score_exactly_10(self):
        """Accept Classe A with score exactly 10.0."""
        article = make_article(classe="A", score=10.0)
        report = make_report(artigos=[article])
        result = parse_report(to_json(report))
        assert result['artigos'][0]['score'] == 10.0

    def test_classe_b_score_too_low(self):
        """Reject Classe B with score 5.9."""
        article = make_article(classe="B", score=5.9)
        report = make_report(artigos=[article])
        with pytest.raises(ParsingError, match="Classe B requires score between 6.0 and 7.9"):
            parse_report(to_json(report))

    def test_classe_b_score_too_high(self):
        """Reject Classe B with score 8.0."""
        article = make_article(classe="B", score=8.0)
        report = make_report(artigos=[article])
        with pytest.raises(ParsingError, match="Classe B requires score between 6.0 and 7.9"):
            parse_report(to_json(report))

    def test_classe_b_score_exactly_6(self):
        """Accept Classe B with score exactly 6.0."""
        article = make_article(classe="B", score=6.0)
        report = make_report(artigos=[article])
        result = parse_report(to_json(report))
        assert result['artigos'][0]['score'] == 6.0

    def test_classe_b_score_exactly_7_9(self):
        """Accept Classe B with score exactly 7.9."""
        article = make_article(classe="B", score=7.9)
        report = make_report(artigos=[article])
        result = parse_report(to_json(report))
        assert result['artigos'][0]['score'] == 7.9

    def test_classe_c_score_too_low(self):
        """Reject Classe C with score 3.9."""
        article = make_article(classe="C", score=3.9)
        report = make_report(artigos=[article])
        with pytest.raises(ParsingError, match="Classe C requires score between 4.0 and 5.9"):
            parse_report(to_json(report))

    def test_classe_c_score_too_high(self):
        """Reject Classe C with score 6.0."""
        article = make_article(classe="C", score=6.0)
        report = make_report(artigos=[article])
        with pytest.raises(ParsingError, match="Classe C requires score between 4.0 and 5.9"):
            parse_report(to_json(report))

    def test_classe_c_score_exactly_4(self):
        """Accept Classe C with score exactly 4.0."""
        article = make_article(classe="C", score=4.0)
        report = make_report(artigos=[article])
        result = parse_report(to_json(report))
        assert result['artigos'][0]['score'] == 4.0

    def test_classe_c_score_exactly_5_9(self):
        """Accept Classe C with score exactly 5.9."""
        article = make_article(classe="C", score=5.9)
        report = make_report(artigos=[article])
        result = parse_report(to_json(report))
        assert result['artigos'][0]['score'] == 5.9

    def test_invalid_classe_letter(self):
        """Reject invalid classe letter."""
        article = make_article(classe="D")
        report = make_report(artigos=[article])
        with pytest.raises(ParsingError, match="classe.*must be 'A', 'B', or 'C'"):
            parse_report(to_json(report))

    def test_score_negative(self):
        """Reject negative score."""
        article = make_article(classe="A", score=-1)
        report = make_report(artigos=[article])
        with pytest.raises(ParsingError, match="must be between 0 and 10"):
            parse_report(to_json(report))

    def test_score_not_number(self):
        """Reject non-numeric score."""
        article = make_article(classe="A", score="9.0")
        report = make_report(artigos=[article])
        with pytest.raises(ParsingError, match="score.*must be a number"):
            parse_report(to_json(report))

    def test_score_is_bool(self):
        """Reject boolean value for score."""
        article = make_article(classe="A", score=True)
        report = make_report(artigos=[article])
        with pytest.raises(ParsingError, match="score.*must be a number, not boolean"):
            parse_report(to_json(report))

    def test_featured_score_classe_consistency(self):
        """Validate score/classe in featured articles."""
        featured = make_article(id="featured_1", classe="A", score=9.5)
        report = make_report(featured=[featured])
        result = parse_report(to_json(report))
        assert result['featured'][0]['classe'] == "A"
        assert result['featured'][0]['score'] == 9.5


# ============================================================================
# TestLinksValidation - Links object validation
# ============================================================================

class TestLinksValidation:
    """Links object validation."""

    def test_links_not_dict(self):
        """Reject links if not a dictionary."""
        article = make_article(links=["https://example.com"])
        report = make_report(artigos=[article])
        with pytest.raises(ParsingError, match="links.*must be a dictionary"):
            parse_report(to_json(report))

    def test_links_empty_dict(self):
        """Reject empty links dictionary."""
        article = make_article(links={})
        report = make_report(artigos=[article])
        with pytest.raises(ParsingError, match="links.*must have at least one link"):
            parse_report(to_json(report))

    def test_links_url_empty_string(self):
        """Reject empty string for URL."""
        article = make_article(links={"url": ""})
        report = make_report(artigos=[article])
        with pytest.raises(ParsingError, match="links.url.*must not be empty string"):
            parse_report(to_json(report))

    def test_links_url_whitespace_only(self):
        """Reject whitespace-only URL."""
        article = make_article(links={"url": "   "})
        report = make_report(artigos=[article])
        with pytest.raises(ParsingError, match="links.url.*must not be empty string"):
            parse_report(to_json(report))

    def test_links_unknown_field(self):
        """Reject unknown field in links."""
        article = make_article(links={"url": "https://example.com", "github": "https://github.com/user/repo"})
        report = make_report(artigos=[article])
        with pytest.raises(ParsingError, match="links.*unknown field 'github'"):
            parse_report(to_json(report))

    def test_links_with_null_values(self):
        """Accept null values in links object."""
        article = make_article(links={"url": "https://example.com", "doi": None, "pubmed": None})
        report = make_report(artigos=[article])
        result = parse_report(to_json(report))
        assert result['artigos'][0]['links']['url'] == "https://example.com"
        assert result['artigos'][0]['links']['doi'] is None


# ============================================================================
# TestMarkdownStripping - Markdown fence removal
# ============================================================================

class TestMarkdownStripping:
    """Markdown fence stripping."""

    def test_strip_json_fence_with_newlines(self):
        """Remove ```json\n...\n``` fence."""
        report = make_report()
        json_str = to_json(report)
        wrapped = f"```json\n{json_str}\n```"
        result = parse_report(wrapped)
        assert result['relatorio_data'] == "2026-04-28"

    def test_strip_generic_fence(self):
        """Remove ```\n...\n``` fence (no json specifier)."""
        report = make_report()
        json_str = to_json(report)
        wrapped = f"```\n{json_str}\n```"
        result = parse_report(wrapped)
        assert result['relatorio_data'] == "2026-04-28"

    def test_no_fence_plain_json(self):
        """Parse plain JSON without fence."""
        report = make_report()
        json_str = to_json(report)
        result = parse_report(json_str)
        assert result['relatorio_data'] == "2026-04-28"

    def test_json_with_internal_triple_backticks(self):
        """Handle JSON containing triple backticks in text (edge case)."""
        # This is an edge case - JSON with ``` in a string field
        # Our simple regex should still work as long as fence is on own line
        report = make_report()
        report['artigos'][0]['resumo'] = "Code example: ```python\nprint('hello')\n```"
        json_str = to_json(report)
        wrapped = f"```json\n{json_str}\n```"
        result = parse_report(wrapped)
        assert "```python" in result['artigos'][0]['resumo']


# ============================================================================
# TestMalformedJSON - JSON syntax error handling
# ============================================================================

class TestMalformedJSON:
    """Malformed JSON handling."""

    def test_invalid_json_missing_brace(self):
        """Reject JSON with missing closing brace."""
        invalid_json = '{"relatorio_data": "2026-04-28"'
        with pytest.raises(ParsingError, match="Invalid JSON"):
            parse_report(invalid_json)

    def test_invalid_json_trailing_comma(self):
        """Reject JSON with trailing comma."""
        invalid_json = '{"relatorio_data": "2026-04-28",}'
        with pytest.raises(ParsingError, match="Invalid JSON"):
            parse_report(invalid_json)

    def test_invalid_json_single_quotes(self):
        """Reject JSON with single quotes."""
        invalid_json = "{'relatorio_data': '2026-04-28'}"
        with pytest.raises(ParsingError, match="Invalid JSON"):
            parse_report(invalid_json)

    def test_invalid_json_unquoted_keys(self):
        """Reject JSON with unquoted keys."""
        invalid_json = '{relatorio_data: "2026-04-28"}'
        with pytest.raises(ParsingError, match="Invalid JSON"):
            parse_report(invalid_json)

    def test_non_string_input(self):
        """Reject non-string input."""
        with pytest.raises(ParsingError, match="Report must be a string"):
            parse_report(123)

    def test_non_string_input_dict(self):
        """Reject dict input (not JSON string)."""
        with pytest.raises(ParsingError, match="Report must be a string"):
            parse_report({"key": "value"})

    def test_empty_string(self):
        """Reject empty string."""
        with pytest.raises(ParsingError, match="Invalid JSON"):
            parse_report("")

    def test_json_not_dict(self):
        """Reject JSON that parses to non-dict."""
        with pytest.raises(ParsingError, match="Report must be a dictionary"):
            parse_report('["array", "not", "dict"]')


# ============================================================================
# TestEdgeCases - Date formats, type coercion, boundary conditions
# ============================================================================

class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_date_format_invalid_year(self):
        """Reject invalid date year (5 digits)."""
        report = make_report(relatorio_data="99999-04-28")
        with pytest.raises(ParsingError, match="must be in YYYY-MM-DD format"):
            parse_report(to_json(report))

    def test_date_format_invalid_month(self):
        """Reject invalid month."""
        report = make_report(relatorio_data="2026-13-28")
        with pytest.raises(ParsingError, match="not a valid date"):
            parse_report(to_json(report))

    def test_date_format_invalid_day(self):
        """Reject invalid day."""
        report = make_report(relatorio_data="2026-02-30")
        with pytest.raises(ParsingError, match="not a valid date"):
            parse_report(to_json(report))

    def test_date_format_wrong_separator(self):
        """Reject date with wrong separator."""
        report = make_report(relatorio_data="2026/04/28")
        with pytest.raises(ParsingError, match="must be in YYYY-MM-DD format"):
            parse_report(to_json(report))

    def test_datetime_format_invalid_hour(self):
        """Reject invalid hour in datetime."""
        report = make_report(gerado_em="2026-04-28T25:15:00Z")
        with pytest.raises(ParsingError, match="not a valid datetime"):
            parse_report(to_json(report))

    def test_datetime_format_missing_z(self):
        """Reject datetime without Z suffix."""
        report = make_report(gerado_em="2026-04-28T03:15:00")
        with pytest.raises(ParsingError, match="must be in ISO 8601 format"):
            parse_report(to_json(report))

    def test_resumo_float_values(self):
        """Accept float values in resumo numeric fields."""
        resumo = make_resumo(total_artigos=15.5, tempo_leitura_minutos=14.2)
        report = make_report(resumo=resumo)
        result = parse_report(to_json(report))
        assert result['resumo']['total_artigos'] == 15.5
        assert result['resumo']['tempo_leitura_minutos'] == 14.2

    def test_score_as_integer(self):
        """Accept integer score (converted from float comparison)."""
        article = make_article(classe="A", score=9)  # int, not float
        report = make_report(artigos=[article])
        result = parse_report(to_json(report))
        assert result['artigos'][0]['score'] == 9

    def test_very_large_article_count(self):
        """Accept very large article count."""
        resumo = make_resumo(total_artigos=1000)
        report = make_report(resumo=resumo)
        result = parse_report(to_json(report))
        assert result['resumo']['total_artigos'] == 1000

    def test_zero_reading_time(self):
        """Accept zero reading time."""
        resumo = make_resumo(tempo_leitura_minutos=0)
        report = make_report(resumo=resumo)
        result = parse_report(to_json(report))
        assert result['resumo']['tempo_leitura_minutos'] == 0

    def test_multiple_featured_articles(self):
        """Parse multiple featured articles."""
        featured = [
            make_article(id="featured_1", classe="A", score=9.5),
            make_article(id="featured_2", classe="A", score=9.2),
            make_article(id="featured_3", classe="A", score=8.8)
        ]
        report = make_report(featured=featured)
        result = parse_report(to_json(report))
        assert len(result['featured']) == 3
