"""JSON parser with schema validation for cardiology research reports."""

import json
import re
from datetime import datetime
from typing import Any, Dict, Optional


class ParsingError(ValueError):
    """Custom exception for JSON parsing and validation errors."""
    pass


def parse_report(raw: str) -> Dict[str, Any]:
    """
    Parse and validate a cardiology research report from Claude's output.

    Args:
        raw: Raw string output from Claude API (may include markdown fences)

    Returns:
        Validated report dictionary

    Raises:
        ParsingError: If parsing or validation fails
    """
    if not isinstance(raw, str):
        raise ParsingError("Report must be a string")

    # Strip markdown fences if present
    json_str = _strip_markdown_fences(raw)

    # Parse JSON
    try:
        report = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ParsingError(f"Invalid JSON: {e}")

    # Validate structure
    _validate(report)

    return report


def _strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences (```json ... ```) from text."""
    # Match ```json followed by newline, content, then ``` on its own line
    pattern = r'```json\s*\n(.*?)\n```'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1)

    # Also handle case where there's just ``` without json specifier
    pattern = r'```\s*\n(.*?)\n```'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1)

    # No fences found, return as-is
    return text


def _validate(report: Dict[str, Any]) -> None:
    """Validate top-level report structure."""

    # Ensure report is a dictionary
    if not isinstance(report, dict):
        raise ParsingError("Report must be a dictionary")

    # Check required top-level fields
    required_fields = {'relatorio_data', 'gerado_em', 'resumo', 'featured', 'artigos'}
    missing = required_fields - set(report.keys())
    if missing:
        raise ParsingError(f"Missing required fields: {', '.join(sorted(missing))}")

    # Validate data types
    if not isinstance(report['relatorio_data'], str):
        raise ParsingError("Field 'relatorio_data' must be a string")
    if not isinstance(report['gerado_em'], str):
        raise ParsingError("Field 'gerado_em' must be a string")
    if not isinstance(report['resumo'], dict):
        raise ParsingError("Field 'resumo' must be a dictionary")
    if not isinstance(report['featured'], list):
        raise ParsingError("Field 'featured' must be a list")
    if not isinstance(report['artigos'], list):
        raise ParsingError("Field 'artigos' must be a list")

    # Validate date formats
    _validate_date_format(report['relatorio_data'], 'relatorio_data')
    _validate_datetime_format(report['gerado_em'], 'gerado_em')

    # Validate resumo
    _validate_resumo(report['resumo'])

    # Validate featured articles
    for i, article in enumerate(report['featured']):
        _validate_article(article, context=f"featured[{i}]")

    # Validate articles
    for i, article in enumerate(report['artigos']):
        _validate_article(article, context=f"artigos[{i}]")

    # Validate X discussions (optional field)
    if 'discussoes_x' in report:
        if not isinstance(report['discussoes_x'], list):
            raise ParsingError("Field 'discussoes_x' must be a list")
        for i, item in enumerate(report['discussoes_x']):
            _validate_x_discussion(item, context=f"discussoes_x[{i}]")


def _validate_resumo(resumo: Dict[str, Any]) -> None:
    """Validate resumo (summary) object."""

    required_fields = {'total_artigos', 'tempo_leitura_minutos', 'classe_a_count', 'classe_b_count', 'classe_c_count'}
    missing = required_fields - set(resumo.keys())
    if missing:
        raise ParsingError(f"Field 'resumo' missing required fields: {', '.join(sorted(missing))}")

    # Validate types and ranges
    for field in ['total_artigos', 'tempo_leitura_minutos', 'classe_a_count', 'classe_b_count', 'classe_c_count']:
        value = resumo[field]

        # Reject boolean values (bool is subclass of int in Python)
        if isinstance(value, bool):
            raise ParsingError(f"Field 'resumo.{field}' must be a number, not boolean")

        if not isinstance(value, (int, float)):
            raise ParsingError(f"Field 'resumo.{field}' must be a number")

        if value < 0:
            raise ParsingError(f"Field 'resumo.{field}' must be non-negative")


def _validate_article(article: Dict[str, Any], context: str = "article") -> None:
    """Validate article structure (featured or artigos item)."""

    required_fields = {'id', 'titulo', 'publicacao', 'classe', 'score', 'categoria_fonte', 'emoji', 'resumo', 'impacto_clinico', 'links'}
    missing = required_fields - set(article.keys())
    if missing:
        raise ParsingError(f"Field '{context}' missing required fields: {', '.join(sorted(missing))}")

    # Validate string fields
    for field in ['id', 'titulo', 'publicacao', 'classe', 'categoria_fonte', 'emoji', 'resumo', 'impacto_clinico']:
        _require_non_empty_string(article[field], f"{context}.{field}")

    # Validate authors if present — filter out empty strings silently
    if 'autores' in article:
        if not isinstance(article['autores'], list):
            article['autores'] = []
        else:
            article['autores'] = [a for a in article['autores'] if isinstance(a, str) and a.strip()]

    # Validate score and classe
    if isinstance(article['score'], bool):
        raise ParsingError(f"Field '{context}.score' must be a number, not boolean")
    if not isinstance(article['score'], (int, float)):
        raise ParsingError(f"Field '{context}.score' must be a number")

    _validate_score_classe(article['score'], article['classe'], context)

    # Normalize categoria_fonte — map any unknown value to 'revista'
    valid_categories = {'revista', 'noticias', 'podcast', 'twitter', 'substack', 'x/twitter'}
    cat = article['categoria_fonte'].lower()
    if cat not in valid_categories:
        article['categoria_fonte'] = 'noticias' if article.get('source_type') == 'rss' else 'revista'

    # Override to 'noticias' for known news/website sources regardless of what Claude returned
    _NEWS_PUBLICATIONS = {'tctmd', 'healio', 'healio cardiology', 'cardiometabolic health', 'medscape'}
    if article['publicacao'].lower() in _NEWS_PUBLICATIONS:
        article['categoria_fonte'] = 'noticias'

    # Validate links
    _validate_links(article['links'], context)


def _validate_x_discussion(item: Dict[str, Any], context: str) -> None:
    """Validate a single discussoes_x item."""
    if not isinstance(item, dict):
        raise ParsingError(f"Field '{context}' must be a dictionary")

    required_fields = {'id', 'titulo', 'autor', 'emoji', 'classe', 'score', 'resumo', 'impacto_clinico', 'links'}
    missing = required_fields - set(item.keys())
    if missing:
        raise ParsingError(f"Field '{context}' missing required fields: {', '.join(sorted(missing))}")

    for field in ['id', 'titulo', 'autor', 'emoji', 'resumo', 'impacto_clinico']:
        _require_non_empty_string(item[field], f"{context}.{field}")

    if isinstance(item['score'], bool):
        raise ParsingError(f"Field '{context}.score' must be a number, not boolean")
    if not isinstance(item['score'], (int, float)):
        raise ParsingError(f"Field '{context}.score' must be a number")

    _validate_score_classe(item['score'], item['classe'], context)

    # aplicabilidade_brasil is optional — normalize if present
    if 'aplicabilidade_brasil' in item:
        if not isinstance(item['aplicabilidade_brasil'], str):
            item['aplicabilidade_brasil'] = ''

    _validate_x_links(item['links'], context)


def _validate_x_links(links: Dict[str, Any], context: str) -> None:
    """Validate links object for discussoes_x — must have post_url or url."""
    if not isinstance(links, dict):
        raise ParsingError(f"Field '{context}.links' must be a dictionary")

    known_fields = {'post_url', 'url', 'doi', 'pubmed'}
    for field in list(links.keys()):
        if field not in known_fields:
            del links[field]
            continue
        value = links[field]
        if value is not None and not isinstance(value, str):
            links[field] = None
        elif isinstance(value, str) and not value.strip():
            links[field] = None

    # At least one of post_url or url must be present (can be null, but key must exist)
    if not links.get('post_url') and not links.get('url'):
        links.setdefault('post_url', None)


def _validate_score_classe(score: float, classe: str, context: str) -> None:
    """Validate score and classe consistency."""

    if classe not in {'A', 'B', 'C'}:
        raise ParsingError(f"Field '{context}.classe' must be 'A', 'B', or 'C'")

    if not (0 <= score <= 10):
        raise ParsingError(f"Field '{context}.score' must be between 0 and 10")

    # Enforce score ranges per classe (inclusive boundaries)
    if classe == 'A':
        if not (8.0 <= score <= 10.0):
            raise ParsingError(f"Field '{context}': Classe A requires score between 8.0 and 10.0, got {score}")
    elif classe == 'B':
        if not (6.0 <= score < 8.0):
            raise ParsingError(f"Field '{context}': Classe B requires score between 6.0 and 7.9, got {score}")
    elif classe == 'C':
        if not (4.0 <= score < 6.0):
            raise ParsingError(f"Field '{context}': Classe C requires score between 4.0 and 5.9, got {score}")


def _validate_links(links: Dict[str, Any], context: str) -> None:
    """Validate links object structure."""

    if not isinstance(links, dict):
        raise ParsingError(f"Field '{context}.links' must be a dictionary")

    # At least one link must be present
    if not links:
        raise ParsingError(f"Field '{context}.links' must have at least one link")

    # Validate present link fields — ignore unknown fields, normalize empty strings
    known_fields = {'url', 'doi', 'pubmed', 'twitter_link'}
    for field in list(links.keys()):
        if field not in known_fields:
            del links[field]
            continue

        value = links[field]
        if value is not None and not isinstance(value, str):
            links[field] = None
        elif isinstance(value, str) and not value.strip():
            links[field] = None


def _require_non_empty_string(value: Any, field_name: str) -> None:
    """Validate that a value is a non-empty string."""

    if not isinstance(value, str):
        raise ParsingError(f"Field '{field_name}' must be a string")

    if not value.strip():
        raise ParsingError(f"Field '{field_name}' must not be empty")


def _validate_date_format(date_str: str, field_name: str) -> None:
    """Validate YYYY-MM-DD date format."""

    pattern = r'^\d{4}-\d{2}-\d{2}$'
    if not re.match(pattern, date_str):
        raise ParsingError(f"Field '{field_name}' must be in YYYY-MM-DD format")

    # Also verify it's a valid date
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        raise ParsingError(f"Field '{field_name}' is not a valid date")


def _validate_datetime_format(datetime_str: str, field_name: str) -> None:
    """Validate ISO 8601 datetime — accept common variations and normalize."""

    # Accept formats: with Z, with +00:00, with milliseconds
    pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'
    if not re.match(pattern, datetime_str):
        raise ParsingError(f"Field '{field_name}' must be in ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ)")
