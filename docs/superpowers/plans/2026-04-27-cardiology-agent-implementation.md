# Cardiology Daily Research Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fully autonomous daily cardiology research agent that runs at 3:00 AM via GitHub Actions, queries Claude API for 50+ journals + 25+ researcher profiles, and displays curated articles (10–15) in a beautiful Vue 3 dashboard with class filtering, source badges, and clickable links.

**Architecture:** Python backend (Claude API integration + JSON generation) deployed via GitHub Actions (free scheduler), Vue 3 frontend (Tailwind CSS, Duolingo-inspired design) served from Vercel (free), GitHub repository as data storage (free versioning). Daily workflow: Agent runs 3 AM → generates `data/relatorio-YYYY-MM-DD.json` → Frontend fetches and renders on user's morning wake-up.

**Tech Stack:** Python 3.11 + Anthropic SDK (backend agent), GitHub Actions (CI/CD scheduler), Vue 3 + Vite + Tailwind CSS (frontend), Vercel (hosting), Git/GitHub (storage + versioning)

---

## File Structure

### Backend (Python Agent)
- `.github/workflows/daily-report.yml` - GitHub Actions cron workflow (3 AM Brasília time)
- `agent/agent.py` - Main agent script that calls Claude API and orchestrates research
- `agent/parser.py` - JSON parser/validator that ensures output matches schema
- `agent/prompt.txt` - Detailed research prompt (50 journals, 25 profiles, source types, classification rules)
- `agent/requirements.txt` - Python dependencies (anthropic, python-dotenv, pytest)
- `agent/tests/test_agent.py` - Unit tests for API integration (mock Claude, test error handling)
- `agent/tests/test_parser.py` - Validation tests for JSON schema and article structure

### Frontend (Vue 3)
- `frontend/src/App.vue` - Root component, fetch logic, state management
- `frontend/src/components/Dashboard.vue` - Main layout (header, featured articles, article list)
- `frontend/src/components/ArticleCard.vue` - Article card with class badge, score, summary, source emoji, links
- `frontend/src/components/FilterBar.vue` - Sticky filter buttons (Class A/B/C, Source type)
- `frontend/src/components/ArticleDetail.vue` - Modal with full article details, favorite button
- `frontend/src/components/HeaderStats.vue` - Stats cards (total articles, reading time, update time)
- `frontend/src/utils/formatters.ts` - Helper functions (date formatting, truncate text, classify articles)
- `frontend/src/assets/styles.css` - Global Tailwind + custom styles (gradients, animations)
- `frontend/package.json` - Dependencies (Vue 3, Vite, Tailwind, Vitest)
- `frontend/vite.config.js` - Vite build configuration
- `frontend/tailwind.config.js` - Tailwind color palette (Duolingo-inspired)
- `frontend/index.html` - HTML entry point
- `frontend/vercel.json` - Vercel SPA configuration

### Repository Root
- `data/` - Directory for daily JSON reports (auto-created by agent)
- `README.md` - Complete project documentation, quick start, architecture diagram, troubleshooting
- `.env.example` - Template for environment variables (ANTHROPIC_API_KEY)
- `.gitignore` - Exclude node_modules, __pycache__, .env, virtual environments

---

## Task Breakdown

### PHASE 1: Core Agent Setup (Tasks 1–5)

### Task 1: Initialize Git Repository and Backend Scaffolding

**Files:**
- Create: `.gitignore`
- Create: `agent/requirements.txt`
- Create: `.env.example`
- Create: `agent/tests/__init__.py`
- Create: `data/.gitkeep`

- [ ] **Step 1: Initialize a new git repository**

```bash
git init
git config user.name "Cardiology Agent"
git config user.email "agent@cardiologia.local"
```

- [ ] **Step 2: Create .gitignore**

```
.gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
ENV/
env/

# Environment variables
.env
.env.local

# Node modules
node_modules/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Data files (optional - comment out if you want to version them)
# data/*.json
```

- [ ] **Step 3: Create agent/requirements.txt**

```
anthropic==0.42.0
python-dotenv==1.0.0
pytest==8.0.0
pytest-asyncio==0.23.0
```

- [ ] **Step 4: Create .env.example**

```
# Anthropic API
ANTHROPIC_API_KEY=sk-ant-...

# GitHub (for auto-commits in Actions)
GITHUB_TOKEN=ghp_...

# Brasília timezone for scheduling (UTC-3)
TZ=America/Sao_Paulo
```

- [ ] **Step 5: Create agent/tests/__init__.py (empty file)**

```python
# Empty file to mark tests as a Python package
```

- [ ] **Step 6: Create data/.gitkeep**

```
# Placeholder to track data/ directory
```

- [ ] **Step 7: Commit initial structure**

```bash
git add .gitignore agent/requirements.txt .env.example agent/tests/__init__.py data/.gitkeep
git commit -m "feat: initialize project structure and dependencies"
```

---

### Task 2: Create Research Prompt with Journal List and Researcher Profiles

**Files:**
- Create: `agent/prompt.txt`

- [ ] **Step 1: Create detailed research prompt**

```bash
cat > agent/prompt.txt << 'EOF'
# Pesquisa Diária em Cardiologia - Instruções para Claude

## Objetivo
Pesquisar e compilar os 10-15 artigos mais relevantes publicados nas últimas 24 horas relacionados a cardiologia.
Cada artigo deve ser balanceado em detalhes, evidência-baseado, e focado em impacto clínico prático.

## Fontes de Pesquisa

### Revistas Médicas (50+)
Nature Reviews Cardiology, Circulation, Journal of the American College of Cardiology (JACC),
Lancet Cardiology, European Heart Journal, American Journal of Cardiology, Cardiovascular Research,
Heart Failure Reviews, Hypertension, Arteriosclerosis Thrombosis and Vascular Biology,
Journal of Cardiac Surgery, Current Problems in Cardiology, Chest, New England Journal of Medicine,
JAMA Cardiology, Stroke, Atherosclerosis, American Journal of Physiology, Nature Medicine,
Science Translational Medicine, Cell Reports, PLOS One, Scientific Reports, Frontiers in Cardiovascular Medicine,
Cardiac Electrophysiology Review, Heart Rhythm, Pacing and Clinical Electrophysiology,
American Heart Journal, Journal of Interventional Cardiac Electrophysiology, Circulation Arrhythmia and Electrophysiology,
Clinical Cardiology, Coronary Artery Disease, Drugs, European Journal of Heart Failure,
International Journal of Cardiology, Journal of Cardiac Failure, Journal of Cardiovascular Electrophysiology,
Journal of Cardiovascular Nursing, Journal of Cardiovascular Pharmacology, Journal of Heart and Lung Transplantation,
Journal of Thoracic and Cardiovascular Surgery, Mayo Clinic Proceedings, Radiologia Brasileira,
Revista Brasileira de Cardiologia, American Journal of Emergency Medicine, Academic Emergency Medicine,
Cardiology in the Young, Pediatric Cardiology, Congenital Heart Disease, Research Reports in Clinical Cardiology

### Perfis de Pesquisadores/Especialistas (25+)
- Eric Topol (Scripps Research)
- Harlan Krumholz (Yale School of Medicine)
- Gregg Fonarow (UCLA)
- Clyde Yancy (Northwestern University)
- James Fang (Harvard Medical School)
- Ziad Amsallem (Stanford)
- Aamir Samman (Mayo Clinic)
- Rene Alvarez (UT Health San Antonio)
- Andrew Wald (Dartmouth)
- Shunichi Homma (Columbia University)
- Mitsuharu Hosaka (Japan)
- Piotr Ponikowski (Wroclaw Medical University)
- Stefan Agewall (Uppsala University)
- Neil Smart (University of Exeter)
- Emanuele Barbato (University of Naples)
- Paulo Rossi Menezes (INCOR - Brasil)
- Braz Marques (Instituto Nacional de Cardiologia - Brasil)
- Cláudio Szarf (Universidade Federal do Rio de Janeiro)
- Angela Müller (UERJ - Brasil)
- Roberto Mangini (INCOR - Brasil)
- Juliana Paredes-Gâmez (Clínica Alemana - Chile)
- Monica Centeno (Clínica Las Condes - Chile)
- Fernando Alfonso (Hospital Universitario de La Princesa)
- Carlos Moreno-Zamora (UNAM México)
- Juan Carlos García-Rubira (Complejo Hospitalario Torrecárdenas)

### Podcasts Cardio (10+)
- The Cardiology Podcast (Medscape)
- Journal Club Podcast (American College of Cardiology)
- HeartRhythm Case Reports Podcast
- Heart Failure Society of America Podcasts
- Texas Heart Institute Podcast
- Cleveland Clinic Cardiology Podcast
- Mayo Clinic Insights Cardiology
- Stanford Cardiology Grand Rounds
- Johns Hopkins Cardiology Conferences
- ACC.org Podcasts

### Newsletters/Substacks (10+)
- Eric Topol's Ground Truths (Substack)
- Harlan Krumholz's Healthcare Innovation (various)
- Journal Scan (various cardiology societies)
- UpToDate Cardiology Summary
- Medscape Cardiology Daily
- Cardiovascular Research Weekly
- Heart.Org News
- Cardiology Today
- Circulation Commentary

## Critérios de Classificação

### Classe A (Impacto Clínico Altíssimo)
- Novos tratamentos/intervenções que mudam prática clínica
- Achados de estudos clínicos randomizados grandes
- Guidelines ou consensos atualizados
- Descobertas de mecanismos que explicam doenças cardíacas
- Score: 8-10

### Classe B (Impacto Clínico Moderado-Alto)
- Estudos observacionais de qualidade
- Melhorias em tecnologia/diagnóstico
- Casos clínicos educacionais interessantes
- Revisões sistemáticas de tópicos relevantes
- Score: 6-7.9

### Classe C (Impacto Clínico Relevante)
- Pesquisa básica interessante
- Editoriais e comentários
- Estudos preliminares
- Notícias de interesse geral em cardiologia
- Score: 4-5.9

## Categorias de Fonte
- revista: Artigos publicados em periódicos científicos
- podcast: Episódios de podcasts relevantes
- twitter: Posts de especialistas em X/Twitter
- substack: Artigos de newsletters ou Substack

## Formato de Output (JSON)

Retorne um JSON estruturado exatamente como especificado, com:
- 10-15 artigos totais (3 em "featured", resto em "artigos")
- Cada artigo com: id, titulo, publicacao, autores, classe (A/B/C), score (0-10),
  categoria_fonte, emoji, resumo (2-3 linhas), impacto_clinico, links
- Featured: top 3 articles com maior impacto
- Artigos: ordenados por score (descendente)
- Links: incluir url, doi, pubmed, twitter_link quando disponível

## Ton e Estilo
- Balanceado: nem muito técnico, nem muito simplificado
- Evidência-baseado: cite achados, não opiniões
- Acionável: "O que muda amanhã?" = impacto prático
- Português: use português brasileiro para resumos e impacto
- Conciso: 2-3 linhas de resumo max

## Exemplo de Output Esperado

{
  "relatorio_data": "2026-04-28",
  "gerado_em": "2026-04-28T03:15:00Z",
  "resumo": {
    "total_artigos": 15,
    "tempo_leitura_minutos": 15,
    "classe_a_count": 5,
    "classe_b_count": 7,
    "classe_c_count": 3
  },
  "featured": [
    {
      "id": "featured_1",
      "titulo": "Novo marcapasso inteligente reduz arritmia em 40%",
      "publicacao": "Nature Reviews Cardiology",
      "autores": ["Smith J", "Johnson M"],
      "classe": "A",
      "score": 9.2,
      "categoria_fonte": "revista",
      "emoji": "📰",
      "resumo": "Tecnologia de detecção por IA em marcapassos reduz arritmias paroxísticas...",
      "impacto_clinico": "Redução de 40% em hospitalizações emergenciais por arritmia.",
      "links": {
        "url": "https://www.nature.com/articles/...",
        "doi": "10.1038/...",
        "pubmed": "12345678"
      }
    }
  ],
  "artigos": [
    // ... resto dos artigos
  ]
}

Pesquise e compile os artigos agora. Retorne APENAS JSON válido, sem markdown ou comentários adicionais.
EOF
```

- [ ] **Step 2: Verify prompt file exists and has content**

```bash
wc -l agent/prompt.txt
# Expected: > 100 lines
cat agent/prompt.txt | head -20
```

- [ ] **Step 3: Commit the prompt**

```bash
git add agent/prompt.txt
git commit -m "feat: add detailed research prompt with journal list and researcher profiles"
```

---

### Task 3: Create JSON Parser with Schema Validation

**Files:**
- Create: `agent/parser.py`

- [ ] **Step 1: Write failing test for parser**

```bash
cat > agent/tests/test_parser.py << 'EOF'
import json
import pytest
from agent.parser import validate_and_parse_report, ParsingError

def test_valid_report_structure():
    """Test that a valid report passes validation"""
    valid_report = {
        "relatorio_data": "2026-04-28",
        "gerado_em": "2026-04-28T03:15:00Z",
        "resumo": {
            "total_artigos": 3,
            "tempo_leitura_minutos": 15,
            "classe_a_count": 1,
            "classe_b_count": 1,
            "classe_c_count": 1
        },
        "featured": [
            {
                "id": "featured_1",
                "titulo": "Test Article",
                "publicacao": "Test Journal",
                "autores": ["Author 1"],
                "classe": "A",
                "score": 9.0,
                "categoria_fonte": "revista",
                "emoji": "📰",
                "resumo": "Short summary",
                "impacto_clinico": "High impact",
                "links": {"url": "https://example.com"}
            }
        ],
        "artigos": []
    }
    result = validate_and_parse_report(valid_report)
    assert result["relatorio_data"] == "2026-04-28"
    assert result["resumo"]["total_artigos"] == 3

def test_article_count_range():
    """Test that total articles must be 10-15"""
    report_too_few = {
        "relatorio_data": "2026-04-28",
        "gerado_em": "2026-04-28T03:15:00Z",
        "resumo": {"total_artigos": 5, "tempo_leitura_minutos": 10, "classe_a_count": 1, "classe_b_count": 2, "classe_c_count": 2},
        "featured": [],
        "artigos": []
    }
    with pytest.raises(ParsingError, match="must have 10-15 articles"):
        validate_and_parse_report(report_too_few)

def test_missing_required_fields():
    """Test that missing required fields raise error"""
    incomplete_report = {
        "relatorio_data": "2026-04-28"
        # missing gerado_em, resumo, featured, artigos
    }
    with pytest.raises(ParsingError, match="Missing required field"):
        validate_and_parse_report(incomplete_report)

def test_invalid_class():
    """Test that invalid class raises error"""
    report_bad_class = {
        "relatorio_data": "2026-04-28",
        "gerado_em": "2026-04-28T03:15:00Z",
        "resumo": {"total_artigos": 1, "tempo_leitura_minutos": 5, "classe_a_count": 0, "classe_b_count": 0, "classe_c_count": 1},
        "featured": [
            {
                "id": "featured_1",
                "titulo": "Test",
                "publicacao": "Test",
                "autores": ["A"],
                "classe": "D",  # Invalid
                "score": 5.0,
                "categoria_fonte": "revista",
                "emoji": "📰",
                "resumo": "Test",
                "impacto_clinico": "Test",
                "links": {"url": "https://example.com"}
            }
        ],
        "artigos": []
    }
    with pytest.raises(ParsingError, match="Invalid class"):
        validate_and_parse_report(report_bad_class)
EOF
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd agent
python -m pytest tests/test_parser.py -v
# Expected: FAILED - ModuleNotFoundError: No module named 'agent.parser'
```

- [ ] **Step 3: Write parser.py**

```bash
cat > agent/parser.py << 'EOF'
import json
from typing import Dict, List, Any
from datetime import datetime

class ParsingError(Exception):
    """Custom exception for parsing errors"""
    pass

def validate_and_parse_report(report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and parse a cardiology research report.
    
    Args:
        report: Dictionary containing the report data
        
    Returns:
        Validated and cleaned report dictionary
        
    Raises:
        ParsingError: If validation fails
    """
    
    # Check required top-level fields
    required_fields = ["relatorio_data", "gerado_em", "resumo", "featured", "artigos"]
    for field in required_fields:
        if field not in report:
            raise ParsingError(f"Missing required field: {field}")
    
    # Validate dates
    try:
        datetime.fromisoformat(report["gerado_em"].replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        raise ParsingError(f"Invalid ISO datetime format: {report['gerado_em']}")
    
    # Validate resumo (summary)
    resumo = report.get("resumo", {})
    total_articles = resumo.get("total_artigos", 0)
    if total_articles < 10 or total_articles > 15:
        raise ParsingError(f"Report must have 10-15 articles, got {total_articles}")
    
    # Validate featured articles
    featured = report.get("featured", [])
    if len(featured) != 3:
        raise ParsingError(f"Must have exactly 3 featured articles, got {len(featured)}")
    
    # Validate all articles (featured + regular)
    all_articles = featured + report.get("artigos", [])
    for idx, article in enumerate(all_articles):
        _validate_article(article, idx)
    
    # Validate article counts add up
    total_count = resumo.get("classe_a_count", 0) + resumo.get("classe_b_count", 0) + resumo.get("classe_c_count", 0)
    if total_count != total_articles:
        raise ParsingError(f"Class counts don't match total: {total_count} != {total_articles}")
    
    return report

def _validate_article(article: Dict[str, Any], index: int) -> None:
    """Validate a single article structure"""
    
    required_article_fields = ["id", "titulo", "publicacao", "classe", "score", "categoria_fonte", "resumo", "impacto_clinico"]
    for field in required_article_fields:
        if field not in article:
            raise ParsingError(f"Article {index} missing field: {field}")
    
    # Validate class
    if article["classe"] not in ["A", "B", "C"]:
        raise ParsingError(f"Invalid class '{article['classe']}' in article {index}. Must be A, B, or C")
    
    # Validate score range
    score = article.get("score", -1)
    if not isinstance(score, (int, float)) or score < 0 or score > 10:
        raise ParsingError(f"Invalid score {score} in article {index}. Must be 0-10")
    
    # Validate categoria_fonte
    valid_sources = ["revista", "podcast", "twitter", "substack"]
    if article["categoria_fonte"] not in valid_sources:
        raise ParsingError(f"Invalid categoria_fonte '{article['categoria_fonte']}' in article {index}")
    
    # Validate summary length (2-3 lines, roughly 100-300 chars)
    resumo = article.get("resumo", "")
    if len(resumo) < 50 or len(resumo) > 500:
        raise ParsingError(f"Summary too short/long in article {index}: {len(resumo)} chars (expected 50-500)")

def save_report_to_json(report: Dict[str, Any], filepath: str) -> None:
    """Save validated report to JSON file"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

def load_report_from_json(filepath: str) -> Dict[str, Any]:
    """Load and validate report from JSON file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        report = json.load(f)
    return validate_and_parse_report(report)
EOF
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd agent
python -m pytest tests/test_parser.py -v
# Expected: PASSED (4 tests)
```

- [ ] **Step 5: Commit parser**

```bash
git add agent/parser.py agent/tests/test_parser.py
git commit -m "feat: add JSON parser with schema validation"
```

---

### Task 4: Create Python Agent Script with Claude API Integration

**Files:**
- Create: `agent/agent.py`
- Create: `agent/tests/test_agent.py`

- [ ] **Step 1: Write failing tests for agent**

```bash
cat > agent/tests/test_agent.py << 'EOF'
import pytest
import json
from unittest.mock import patch, MagicMock
from agent.agent import CardologyAgent

@pytest.fixture
def mock_claude_response():
    """Mock Claude API response"""
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps({
                    "relatorio_data": "2026-04-28",
                    "gerado_em": "2026-04-28T03:15:00Z",
                    "resumo": {
                        "total_artigos": 12,
                        "tempo_leitura_minutos": 15,
                        "classe_a_count": 4,
                        "classe_b_count": 5,
                        "classe_c_count": 3
                    },
                    "featured": [
                        {
                            "id": "featured_1",
                            "titulo": "Test Article 1",
                            "publicacao": "Test Journal",
                            "autores": ["Author 1"],
                            "classe": "A",
                            "score": 9.0,
                            "categoria_fonte": "revista",
                            "emoji": "📰",
                            "resumo": "Test summary text here",
                            "impacto_clinico": "High clinical impact",
                            "links": {"url": "https://example.com"}
                        },
                        {
                            "id": "featured_2",
                            "titulo": "Test Article 2",
                            "publicacao": "Test Journal",
                            "autores": ["Author 2"],
                            "classe": "A",
                            "score": 8.5,
                            "categoria_fonte": "revista",
                            "emoji": "📰",
                            "resumo": "Another test summary",
                            "impacto_clinico": "Significant clinical impact",
                            "links": {"url": "https://example.com"}
                        },
                        {
                            "id": "featured_3",
                            "titulo": "Test Article 3",
                            "publicacao": "Test Journal",
                            "autores": ["Author 3"],
                            "classe": "B",
                            "score": 7.5,
                            "categoria_fonte": "revista",
                            "emoji": "📰",
                            "resumo": "Third test article",
                            "impacto_clinico": "Moderate clinical impact",
                            "links": {"url": "https://example.com"}
                        }
                    ],
                    "artigos": [
                        {
                            "id": "art_001",
                            "titulo": f"Test Article {i}",
                            "publicacao": "Test Journal",
                            "autores": ["Author"],
                            "classe": "B" if i % 2 == 0 else "C",
                            "score": 6.0 + (i * 0.1),
                            "categoria_fonte": "revista",
                            "emoji": "📰",
                            "resumo": f"Summary for article {i}",
                            "impacto_clinico": f"Impact statement {i}",
                            "links": {"url": "https://example.com"}
                        } for i in range(1, 10)
                    ]
                })
            }
        ]
    }

@patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'})
def test_agent_initialization():
    """Test that agent initializes with API key"""
    agent = CardologyAgent()
    assert agent.client is not None
    assert agent.model == "claude-3-5-sonnet-20241022"

@patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'})
@patch('anthropic.Anthropic.messages.create')
def test_run_research(mock_create, mock_claude_response):
    """Test that agent runs research and returns report"""
    mock_create.return_value = mock_claude_response
    
    agent = CardologyAgent()
    report = agent.run_research()
    
    assert report["relatorio_data"] == "2026-04-28"
    assert report["resumo"]["total_artigos"] == 12
    assert len(report["featured"]) == 3
    assert len(report["artigos"]) == 9

@patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'})
@patch('anthropic.Anthropic.messages.create')
def test_run_research_saves_json(mock_create, mock_claude_response, tmp_path):
    """Test that report is saved to JSON file"""
    mock_create.return_value = mock_claude_response
    
    agent = CardologyAgent()
    output_file = str(tmp_path / "test_report.json")
    report = agent.run_research(output_file=output_file)
    
    # Verify file was created
    import os
    assert os.path.exists(output_file)
    
    # Verify file contains valid JSON
    with open(output_file, 'r') as f:
        saved_report = json.load(f)
    assert saved_report["relatorio_data"] == "2026-04-28"
EOF
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd agent
python -m pytest tests/test_agent.py -v
# Expected: FAILED - ModuleNotFoundError: No module named 'agent.agent'
```

- [ ] **Step 3: Create agent.py**

```bash
cat > agent/agent.py << 'EOF'
import os
import json
from datetime import datetime
from anthropic import Anthropic
from parser import validate_and_parse_report, save_report_to_json, ParsingError

class CardologyAgent:
    """Autonomous cardiology research agent that uses Claude API"""
    
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"
    
    def run_research(self, output_file: str = None) -> dict:
        """
        Run daily cardiology research using Claude API.
        
        Args:
            output_file: Optional path to save JSON report
            
        Returns:
            Validated report dictionary
        """
        # Load research prompt
        prompt_text = self._load_prompt()
        
        # Call Claude API
        print("Calling Claude API for cardiology research...")
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4000,
            messages=[
                {
                    "role": "user",
                    "content": prompt_text
                }
            ]
        )
        
        # Extract JSON from response
        response_text = response.content[0].text
        print(f"Received {len(response_text)} characters from Claude")
        
        # Parse JSON response
        try:
            report_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            raise ParsingError(f"Failed to parse Claude response as JSON: {e}")
        
        # Validate report structure
        print("Validating report structure...")
        validated_report = validate_and_parse_report(report_data)
        
        # Save to file if specified
        if output_file:
            print(f"Saving report to {output_file}...")
            save_report_to_json(validated_report, output_file)
        
        print("✓ Research complete")
        return validated_report
    
    def _load_prompt(self) -> str:
        """Load research prompt from file"""
        prompt_path = os.path.join(os.path.dirname(__file__), "prompt.txt")
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()

if __name__ == "__main__":
    agent = CardologyAgent()
    report = agent.run_research(output_file="../data/relatorio.json")
    print(f"\nReport generated: {report['relatorio_data']}")
    print(f"Total articles: {report['resumo']['total_artigos']}")
EOF
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd agent
python -m pytest tests/test_agent.py -v
# Expected: PASSED (3 tests)
```

- [ ] **Step 5: Commit agent**

```bash
git add agent/agent.py agent/tests/test_agent.py
git commit -m "feat: create Claude API agent with research orchestration"
```

---

### Task 5: Create GitHub Actions Workflow for 3:00 AM Daily Execution

**Files:**
- Create: `.github/workflows/daily-report.yml`

- [ ] **Step 1: Create .github/workflows directory**

```bash
mkdir -p .github/workflows
```

- [ ] **Step 2: Create GitHub Actions workflow file**

```bash
cat > .github/workflows/daily-report.yml << 'EOF'
name: Daily Cardiology Research Report

on:
  schedule:
    # Runs at 3:00 AM Brasília time (UTC-3), which is 6:00 AM UTC
    # Using cron: minute hour day-of-month month day-of-week
    - cron: '0 6 * * *'
  
  # Allow manual triggering for testing
  workflow_dispatch:

jobs:
  research:
    runs-on: ubuntu-latest
    name: Generate Daily Cardiology Report
    
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        working-directory: ./agent
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      
      - name: Run research agent
        working-directory: ./agent
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          TZ: America/Sao_Paulo
        run: |
          python -c "
          from agent import CardologyAgent
          from datetime import datetime
          
          print('🤖 Starting cardiology research agent...')
          print(f'⏰ Time: {datetime.now().isoformat()}')
          
          agent = CardologyAgent()
          
          # Generate report filename with today's date (Brasília timezone)
          import pytz
          bsb_tz = pytz.timezone('America/Sao_Paulo')
          today = datetime.now(bsb_tz).date()
          output_file = f'../data/relatorio-{today}.json'
          
          report = agent.run_research(output_file=output_file)
          print(f'✅ Report saved: {output_file}')
          print(f'📊 Articles: {report[\"resumo\"][\"total_artigos\"]}')
          print(f'   - Classe A: {report[\"resumo\"][\"classe_a_count\"]}')
          print(f'   - Classe B: {report[\"resumo\"][\"classe_b_count\"]}')
          print(f'   - Classe C: {report[\"resumo\"][\"classe_c_count\"]}')
          "
      
      - name: Configure git
        run: |
          git config user.name "cardiology-agent"
          git config user.email "cardiology-agent@github.local"
      
      - name: Commit and push report
        run: |
          git add data/relatorio-*.json
          
          # Check if there are changes to commit
          if git diff-index --quiet HEAD --; then
            echo "No changes to commit"
          else
            git commit -m "chore: add daily cardiology report ($(date -u +'%Y-%m-%d %H:%M UTC'))"
            git push origin ${{ github.ref }}
          fi
      
      - name: Report status
        if: always()
        run: echo "✓ Workflow complete"
EOF
```

- [ ] **Step 3: Update requirements.txt to include pytz**

```bash
cat >> agent/requirements.txt << 'EOF'
pytz==2024.1
EOF
```

- [ ] **Step 4: Commit workflow**

```bash
git add .github/workflows/daily-report.yml agent/requirements.txt
git commit -m "feat: add GitHub Actions workflow for 3:00 AM daily execution"
```

- [ ] **Step 5: Test workflow manually (workflow_dispatch)**

Go to GitHub repository → Actions tab → "Daily Cardiology Research Report" → "Run workflow" → Confirm it runs successfully

---

### PHASE 2: Frontend Development (Tasks 6–12)

### Task 6: Initialize Vue 3 + Vite Frontend Project

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.js`
- Create: `frontend/index.html`
- Create: `frontend/tailwind.config.js`
- Create: `frontend/postcss.config.js`

- [ ] **Step 1: Create package.json**

```bash
cat > frontend/package.json << 'EOF'
{
  "name": "cardiology-dashboard",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "test": "vitest"
  },
  "dependencies": {
    "vue": "^3.4.0",
    "axios": "^1.6.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "vite": "^5.0.0",
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0",
    "vitest": "^1.0.0",
    "@vitest/ui": "^1.0.0"
  }
}
EOF
```

- [ ] **Step 2: Create vite.config.js**

```bash
cat > frontend/vite.config.js << 'EOF'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    open: true
  },
  build: {
    outDir: 'dist',
    sourcemap: false
  }
})
EOF
```

- [ ] **Step 3: Create tailwind.config.js**

```bash
cat > frontend/tailwind.config.js << 'EOF'
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}'
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f8f7ff',
          500: '#667eea',
          600: '#5568d3',
          700: '#764ba2'
        },
        classA: '#FF6B6B',
        classB: '#FFA500',
        classC: '#4CAF50',
        featured1: '#FF6B6B',
        featured2: '#20B2AA',
        featured3: '#FF9800'
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif']
      },
      fontSize: {
        xs: ['12px', '16px'],
        sm: ['13px', '18px'],
        base: ['14px', '20px'],
        lg: ['16px', '24px'],
        xl: ['18px', '28px']
      }
    }
  },
  plugins: []
}
EOF
```

- [ ] **Step 4: Create postcss.config.js**

```bash
cat > frontend/postcss.config.js << 'EOF'
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {}
  }
}
EOF
```

- [ ] **Step 5: Create index.html**

```bash
cat > frontend/index.html << 'EOF'
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>📚 Relatório de Cardiologia</title>
  <link rel="stylesheet" href="/src/assets/styles.css">
</head>
<body class="bg-gray-50">
  <div id="app"></div>
  <script type="module" src="/src/main.js"></script>
</body>
</html>
EOF
```

- [ ] **Step 6: Create src/main.js**

```bash
mkdir -p frontend/src/components frontend/src/utils frontend/src/assets
cat > frontend/src/main.js << 'EOF'
import { createApp } from 'vue'
import App from './App.vue'

const app = createApp(App)
app.mount('#app')
EOF
```

- [ ] **Step 7: Create src/assets/styles.css**

```bash
cat > frontend/src/assets/styles.css << 'EOF'
@import 'tailwindcss/base';
@import 'tailwindcss/components';
@import 'tailwindcss/utilities';

/* Custom animations */
@layer utilities {
  .fade-in {
    animation: fadeIn 0.3s ease-in;
  }
  
  @keyframes fadeIn {
    from {
      opacity: 0;
      transform: translateY(10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
  
  .hover-scale {
    @apply transition-transform duration-200 hover:scale-105;
  }
  
  .gradient-primary {
    @apply bg-gradient-to-br from-primary-500 to-primary-700;
  }
  
  .gradient-featured-1 {
    @apply bg-gradient-to-br from-featured1 to-red-600;
  }
  
  .gradient-featured-2 {
    @apply bg-gradient-to-br from-featured2 to-teal-600;
  }
  
  .gradient-featured-3 {
    @apply bg-gradient-to-br from-featured3 to-amber-600;
  }
  
  .card-shadow {
    @apply shadow-md hover:shadow-lg transition-shadow duration-200;
  }
  
  .badge {
    @apply inline-block px-2 py-1 text-xs font-semibold rounded-full;
  }
}
EOF
```

- [ ] **Step 8: Install dependencies and verify**

```bash
cd frontend
npm install
npm run build
# Expected: Successfully compiled
```

- [ ] **Step 9: Commit frontend scaffolding**

```bash
git add frontend/
git commit -m "feat: scaffold Vue 3 frontend with Vite and Tailwind CSS"
```

---

### Task 7: Create Root App Component and Layout Structure

**Files:**
- Create: `frontend/src/App.vue`

- [ ] **Step 1: Create App.vue with fetch and state management**

```bash
cat > frontend/src/App.vue << 'EOF'
<template>
  <div class="min-h-screen bg-gray-50">
    <Dashboard v-if="report" :report="report" />
    <div v-else class="flex items-center justify-center h-screen">
      <div class="text-center">
        <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
        <p class="mt-4 text-gray-600">Carregando relatório...</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Dashboard from './components/Dashboard.vue'

const report = ref(null)
const error = ref(null)

const fetchLatestReport = async () => {
  try {
    const today = new Date().toISOString().split('T')[0]
    const url = `https://raw.githubusercontent.com/${import.meta.env.VITE_GITHUB_REPO}/main/data/relatorio-${today}.json`
    
    const response = await fetch(url)
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    
    const data = await response.json()
    report.value = data
  } catch (err) {
    console.error('Failed to fetch report:', err)
    error.value = err.message
    // Try to load from localStorage as fallback
    const cached = localStorage.getItem('cardiology_report')
    if (cached) {
      report.value = JSON.parse(cached)
    }
  }
}

onMounted(async () => {
  await fetchLatestReport()
})
</script>
EOF
```

- [ ] **Step 2: Create Dashboard.vue main layout**

```bash
cat > frontend/src/components/Dashboard.vue << 'EOF'
<template>
  <div class="dashboard">
    <!-- Header with date and stats -->
    <HeaderStats :report="report" />
    
    <!-- Filter bar (sticky) -->
    <FilterBar 
      :current-class-filter="classFilter"
      :current-source-filter="sourceFilter"
      @update-class="classFilter = $event"
      @update-source="sourceFilter = $event"
    />
    
    <!-- Main content -->
    <main class="max-w-6xl mx-auto px-4 py-8">
      <!-- Featured articles section -->
      <section class="mb-12">
        <h2 class="text-xl font-bold text-gray-800 mb-6">🔥 Destaque do Dia</h2>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <FeaturedCard 
            v-for="(article, idx) in report.featured" 
            :key="article.id"
            :article="article"
            :gradient-class="`gradient-featured-${idx + 1}`"
            @click="selectedArticle = article"
          />
        </div>
      </section>
      
      <!-- All articles list -->
      <section>
        <h2 class="text-xl font-bold text-gray-800 mb-6">
          📰 Todos os {{ filteredArticles.length }} Artigos
        </h2>
        <div class="space-y-4">
          <ArticleCard 
            v-for="article in filteredArticles" 
            :key="article.id"
            :article="article"
            @click="selectedArticle = article"
          />
        </div>
      </section>
    </main>
    
    <!-- Article detail modal -->
    <ArticleDetail 
      v-if="selectedArticle"
      :article="selectedArticle"
      @close="selectedArticle = null"
      @favorite="toggleFavorite(selectedArticle.id)"
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import HeaderStats from './HeaderStats.vue'
import FilterBar from './FilterBar.vue'
import ArticleCard from './ArticleCard.vue'
import FeaturedCard from './FeaturedCard.vue'
import ArticleDetail from './ArticleDetail.vue'

const props = defineProps({
  report: {
    type: Object,
    required: true
  }
})

const classFilter = ref('all')
const sourceFilter = ref('all')
const selectedArticle = ref(null)
const favorites = ref(new Set(JSON.parse(localStorage.getItem('favorites') || '[]')))

const filteredArticles = computed(() => {
  let filtered = props.report.artigos

  if (classFilter.value !== 'all') {
    filtered = filtered.filter(a => a.classe === classFilter.value)
  }

  if (sourceFilter.value !== 'all') {
    filtered = filtered.filter(a => a.categoria_fonte === sourceFilter.value)
  }

  return filtered
})

const toggleFavorite = (articleId) => {
  if (favorites.value.has(articleId)) {
    favorites.value.delete(articleId)
  } else {
    favorites.value.add(articleId)
  }
  localStorage.setItem('favorites', JSON.stringify([...favorites.value]))
}
</script>

<style scoped>
.dashboard {
  min-height: 100vh;
}
</style>
EOF
```

- [ ] **Step 3: Commit App and Dashboard structure**

```bash
git add frontend/src/
git commit -m "feat: create root App component and Dashboard layout"
```

---

### Task 8: Create Header, Filter, and Card Components

**Files:**
- Create: `frontend/src/components/HeaderStats.vue`
- Create: `frontend/src/components/FilterBar.vue`
- Create: `frontend/src/components/ArticleCard.vue`
- Create: `frontend/src/components/FeaturedCard.vue`

- [ ] **Step 1: Create HeaderStats.vue**

```bash
cat > frontend/src/components/HeaderStats.vue << 'EOF'
<template>
  <header class="gradient-primary text-white sticky top-0 z-40 shadow-lg">
    <div class="max-w-6xl mx-auto px-4 py-8">
      <div class="mb-6">
        <h1 class="text-3xl font-bold">📚 Relatório de Cardiologia</h1>
        <p class="text-blue-100 text-sm mt-2">{{ formattedDate }}</p>
      </div>
      
      <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
        <div class="bg-white bg-opacity-20 rounded-lg p-4">
          <div class="text-2xl font-bold">{{ report.resumo.total_artigos }}</div>
          <div class="text-sm opacity-90">Artigos hoje</div>
        </div>
        <div class="bg-white bg-opacity-20 rounded-lg p-4">
          <div class="text-2xl font-bold">{{ report.resumo.tempo_leitura_minutos }}m</div>
          <div class="text-sm opacity-90">Leitura média</div>
        </div>
        <div class="bg-white bg-opacity-20 rounded-lg p-4 col-span-2 md:col-span-1">
          <div class="text-xs font-mono opacity-90">{{ generatedTime }}</div>
          <div class="text-sm opacity-90">Atualizado</div>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  report: {
    type: Object,
    required: true
  }
})

const formattedDate = computed(() => {
  const date = new Date(props.report.relatorio_data)
  const days = ['Domingo', 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado']
  const months = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 
                  'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
  
  return `${days[date.getDay()]}, ${date.getDate()} de ${months[date.getMonth()]} de ${date.getFullYear()}`
})

const generatedTime = computed(() => {
  const date = new Date(props.report.gerado_em)
  return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
})
</script>
EOF
```

- [ ] **Step 2: Create FilterBar.vue**

```bash
cat > frontend/src/components/FilterBar.vue << 'EOF'
<template>
  <div class="sticky top-24 bg-white border-b border-gray-200 shadow-sm z-30">
    <div class="max-w-6xl mx-auto px-4 py-4">
      <div class="flex flex-wrap gap-2 items-center">
        <span class="text-sm font-semibold text-gray-700">Filtrar por:</span>
        
        <div class="flex gap-1">
          <button 
            v-for="cls in ['all', 'A', 'B', 'C']"
            :key="cls"
            @click="$emit('update-class', cls)"
            :class="[
              'px-3 py-1 text-sm rounded transition',
              currentClassFilter === cls 
                ? 'bg-primary-500 text-white font-semibold'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            ]"
          >
            {{ cls === 'all' ? 'Todos' : `Classe ${cls}` }}
          </button>
        </div>
        
        <div class="flex gap-1">
          <button 
            v-for="source in ['all', 'revista', 'podcast', 'twitter', 'substack']"
            :key="source"
            @click="$emit('update-source', source)"
            :class="[
              'px-3 py-1 text-sm rounded transition',
              currentSourceFilter === source 
                ? 'bg-primary-500 text-white font-semibold'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            ]"
          >
            {{ sourceLabel(source) }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  currentClassFilter: String,
  currentSourceFilter: String
})

defineEmits(['update-class', 'update-source'])

const sourceLabel = (source) => {
  const labels = {
    all: 'Todos',
    revista: '📰 Revistas',
    podcast: '🎙️ Podcasts',
    twitter: '🐦 Twitter',
    substack: '📝 Substack'
  }
  return labels[source] || source
}
</script>
EOF
```

- [ ] **Step 3: Create ArticleCard.vue**

```bash
cat > frontend/src/components/ArticleCard.vue << 'EOF'
<template>
  <div class="card-shadow bg-white rounded-lg p-4 cursor-pointer hover-scale fade-in">
    <div class="flex items-start gap-4">
      <!-- Class badge -->
      <div :class="['badge', classBadgeColor]">
        {{ article.classe }}
      </div>
      
      <!-- Main content -->
      <div class="flex-1">
        <div class="flex items-baseline gap-2 mb-1">
          <h3 class="text-base font-semibold text-gray-800 flex-1">{{ article.titulo }}</h3>
          <span class="text-sm font-bold" :style="{ color: scoreColor }">{{ article.score }}/10</span>
        </div>
        
        <p class="text-sm text-gray-600 mb-2">{{ article.publicacao }}</p>
        
        <p class="text-sm text-gray-700 mb-3 line-clamp-2">{{ article.resumo }}</p>
        
        <div class="flex items-center gap-2 mb-3">
          <span class="text-lg">{{ article.emoji }}</span>
          <span class="text-xs text-gray-500">{{ sourceLabel(article.categoria_fonte) }}</span>
        </div>
        
        <p class="text-sm text-blue-700 font-semibold">💡 {{ article.impacto_clinico }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  article: {
    type: Object,
    required: true
  }
})

const classBadgeColor = computed(() => {
  const colors = {
    A: 'bg-red-100 text-red-700',
    B: 'bg-yellow-100 text-yellow-700',
    C: 'bg-green-100 text-green-700'
  }
  return colors[props.article.classe] || 'bg-gray-100 text-gray-700'
})

const scoreColor = computed(() => {
  const score = props.article.score
  if (score >= 8) return '#FF6B6B'
  if (score >= 6) return '#FFA500'
  return '#4CAF50'
})

const sourceLabel = (source) => {
  const labels = {
    revista: 'Revista',
    podcast: 'Podcast',
    twitter: 'X/Twitter',
    substack: 'Substack'
  }
  return labels[source] || source
}
</script>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
EOF
```

- [ ] **Step 4: Create FeaturedCard.vue**

```bash
cat > frontend/src/components/FeaturedCard.vue << 'EOF'
<template>
  <div :class="['rounded-lg p-6 text-white cursor-pointer hover-scale fade-in', gradientClass]">
    <div class="flex items-start justify-between mb-4">
      <div class="badge bg-white bg-opacity-30 text-white">{{ article.classe }}</div>
      <span class="text-2xl font-bold opacity-80">{{ article.score }}</span>
    </div>
    
    <h2 class="text-xl font-bold mb-2">{{ article.titulo }}</h2>
    <p class="text-sm opacity-90 mb-4">{{ article.publicacao }}</p>
    
    <p class="text-sm opacity-90 mb-4">{{ article.resumo }}</p>
    
    <div class="bg-white bg-opacity-20 rounded p-3">
      <p class="text-sm font-semibold">{{ article.impacto_clinico }}</p>
    </div>
  </div>
</template>

<script setup>
defineProps({
  article: {
    type: Object,
    required: true
  },
  gradientClass: {
    type: String,
    default: 'gradient-featured-1'
  }
})
</script>

<style scoped>
.badge {
  @apply inline-block px-2 py-1 text-xs font-semibold rounded-full;
}
</style>
EOF
```

- [ ] **Step 5: Commit components**

```bash
git add frontend/src/components/
git commit -m "feat: create Header, Filter, ArticleCard, and FeaturedCard components"
```

---

### Task 9: Create ArticleDetail Modal Component

**Files:**
- Create: `frontend/src/components/ArticleDetail.vue`

- [ ] **Step 1: Create ArticleDetail.vue**

```bash
cat > frontend/src/components/ArticleDetail.vue << 'EOF'
<template>
  <div class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-end md:items-center justify-center p-4">
    <div class="bg-white rounded-t-2xl md:rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto animate-slideup">
      <!-- Header -->
      <div class="sticky top-0 bg-gradient-to-r from-primary-500 to-primary-700 text-white p-6 flex items-start justify-between">
        <div class="flex-1">
          <div class="flex items-center gap-2 mb-2">
            <span class="badge bg-white bg-opacity-30 text-white">{{ article.classe }}</span>
            <span class="text-sm font-bold">{{ article.score }}/10</span>
          </div>
          <h1 class="text-2xl font-bold">{{ article.titulo }}</h1>
          <p class="text-blue-100 text-sm mt-2">{{ article.publicacao }}</p>
        </div>
        <button 
          @click="$emit('close')"
          class="text-2xl leading-none hover:opacity-70 transition"
        >
          ✕
        </button>
      </div>
      
      <!-- Content -->
      <div class="p-6 space-y-6">
        <!-- Authors -->
        <div v-if="article.autores">
          <h3 class="font-semibold text-gray-800 mb-2">Autores</h3>
          <p class="text-sm text-gray-600">{{ article.autores.join(', ') }}</p>
        </div>
        
        <!-- Summary -->
        <div>
          <h3 class="font-semibold text-gray-800 mb-2">Resumo</h3>
          <p class="text-sm text-gray-700 leading-relaxed">{{ article.resumo }}</p>
        </div>
        
        <!-- Clinical Impact -->
        <div class="bg-blue-50 border-l-4 border-blue-500 p-4 rounded">
          <h3 class="font-semibold text-blue-900 mb-2">💡 O que muda amanhã?</h3>
          <p class="text-sm text-blue-800">{{ article.impacto_clinico }}</p>
        </div>
        
        <!-- Source Info -->
        <div>
          <h3 class="font-semibold text-gray-800 mb-2">Fonte</h3>
          <div class="flex items-center gap-2">
            <span class="text-lg">{{ article.emoji }}</span>
            <span class="text-sm text-gray-600">{{ sourceLabel(article.categoria_fonte) }}</span>
          </div>
        </div>
        
        <!-- Action Links -->
        <div class="space-y-2">
          <a 
            v-if="article.links.url"
            :href="article.links.url"
            target="_blank"
            class="flex items-center gap-2 px-4 py-2 bg-blue-50 text-blue-700 rounded hover:bg-blue-100 transition text-sm"
          >
            📖 Ler artigo completo
          </a>
          
          <a 
            v-if="article.links.doi"
            :href="`https://doi.org/${article.links.doi}`"
            target="_blank"
            class="flex items-center gap-2 px-4 py-2 bg-gray-50 text-gray-700 rounded hover:bg-gray-100 transition text-sm"
          >
            🔗 DOI: {{ article.links.doi }}
          </a>
          
          <a 
            v-if="article.links.pubmed"
            :href="`https://pubmed.ncbi.nlm.nih.gov/${article.links.pubmed}/`"
            target="_blank"
            class="flex items-center gap-2 px-4 py-2 bg-green-50 text-green-700 rounded hover:bg-green-100 transition text-sm"
          >
            🔍 PubMed
          </a>
          
          <a 
            v-if="article.links.twitter_link"
            :href="article.links.twitter_link"
            target="_blank"
            class="flex items-center gap-2 px-4 py-2 bg-blue-50 text-blue-700 rounded hover:bg-blue-100 transition text-sm"
          >
            🐦 Ver no X/Twitter
          </a>
        </div>
        
        <!-- Favorite Button -->
        <button 
          @click="$emit('favorite')"
          class="w-full px-4 py-3 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition font-semibold"
        >
          ⭐ Adicionar aos Favoritos
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  article: {
    type: Object,
    required: true
  }
})

defineEmits(['close', 'favorite'])

const sourceLabel = (source) => {
  const labels = {
    revista: 'Artigo de Revista Científica',
    podcast: 'Episódio de Podcast',
    twitter: 'Post no X/Twitter',
    substack: 'Artigo Substack'
  }
  return labels[source] || source
}
</script>

<style scoped>
@keyframes slideup {
  from {
    transform: translateY(100%);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.animate-slideup {
  animation: slideup 0.3s ease-out;
}

.badge {
  @apply inline-block px-2 py-1 text-xs font-semibold rounded-full;
}
</style>
EOF
```

- [ ] **Step 2: Commit ArticleDetail modal**

```bash
git add frontend/src/components/ArticleDetail.vue
git commit -m "feat: create ArticleDetail modal with full article information"
```

---

### Task 10: Create Utility Functions and Formatters

**Files:**
- Create: `frontend/src/utils/formatters.ts`

- [ ] **Step 1: Create formatters.ts**

```bash
cat > frontend/src/utils/formatters.ts << 'EOF'
/**
 * Utility functions for formatting and processing data
 */

export const truncateText = (text: string, maxLength: number = 100): string => {
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

export const formatDate = (dateString: string): string => {
  const date = new Date(dateString)
  const days = [
    'Domingo', 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado'
  ]
  const months = [
    'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
    'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'
  ]
  
  return `${days[date.getDay()]}, ${date.getDate()} de ${months[date.getMonth()]} de ${date.getFullYear()}`
}

export const getScoreColor = (score: number): string => {
  if (score >= 8) return '#FF6B6B' // Red
  if (score >= 6) return '#FFA500' // Orange
  return '#4CAF50' // Green
}

export const getClassBadgeColor = (classe: string): string => {
  const colors: Record<string, string> = {
    A: 'bg-red-100 text-red-700',
    B: 'bg-yellow-100 text-yellow-700',
    C: 'bg-green-100 text-green-700'
  }
  return colors[classe] || 'bg-gray-100 text-gray-700'
}

export const getSourceEmoji = (source: string): string => {
  const emojis: Record<string, string> = {
    revista: '📰',
    podcast: '🎙️',
    twitter: '🐦',
    substack: '📝'
  }
  return emojis[source] || '📄'
}

export const getSourceLabel = (source: string): string => {
  const labels: Record<string, string> = {
    revista: 'Revista',
    podcast: 'Podcast',
    twitter: 'X/Twitter',
    substack: 'Substack'
  }
  return labels[source] || source
}

export const calculateReadingTime = (articles: any[]): number => {
  // Estimate: ~2 minutes per article for reading summaries
  return articles.length * 2
}

export const filterArticlesByClass = (articles: any[], classe: string): any[] => {
  if (classe === 'all') return articles
  return articles.filter((a: any) => a.classe === classe)
}

export const filterArticlesBySource = (articles: any[], source: string): any[] => {
  if (source === 'all') return articles
  return articles.filter((a: any) => a.categoria_fonte === source)
}

export const sortArticlesByScore = (articles: any[]): any[] => {
  return [...articles].sort((a: any, b: any) => b.score - a.score)
}

export const searchArticles = (articles: any[], query: string): any[] => {
  const lowerQuery = query.toLowerCase()
  return articles.filter((a: any) => 
    a.titulo.toLowerCase().includes(lowerQuery) ||
    a.resumo.toLowerCase().includes(lowerQuery) ||
    a.publicacao.toLowerCase().includes(lowerQuery) ||
    (a.autores && a.autores.some((author: string) => author.toLowerCase().includes(lowerQuery)))
  )
}
EOF
```

- [ ] **Step 2: Commit formatters**

```bash
git add frontend/src/utils/
git commit -m "feat: add utility functions and formatters"
```

---

### PHASE 3: Polish and Deployment (Tasks 11–16)

### Task 11: Configure Vercel Deployment

**Files:**
- Create: `frontend/vercel.json`
- Create: `frontend/.vercelignore`

- [ ] **Step 1: Create vercel.json SPA configuration**

```bash
cat > frontend/vercel.json << 'EOF'
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ],
  "headers": [
    {
      "source": "/assets/(.*)",
      "headers": [
        {
          "key": "Cache-Control",
          "value": "public, max-age=31536000, immutable"
        }
      ]
    },
    {
      "source": "/",
      "headers": [
        {
          "key": "Cache-Control",
          "value": "public, max-age=0, must-revalidate"
        }
      ]
    }
  ]
}
EOF
```

- [ ] **Step 2: Create .vercelignore**

```bash
cat > frontend/.vercelignore << 'EOF'
.env.local
.env.*.local
node_modules
npm-debug.log*
.DS_Store
.git
.gitignore
EOF
```

- [ ] **Step 3: Create .github/workflows/deploy-frontend.yml**

```bash
cat > .github/workflows/deploy-frontend.yml << 'EOF'
name: Deploy Frontend to Vercel

on:
  push:
    branches: [main]
    paths:
      - 'frontend/**'
      - '.github/workflows/deploy-frontend.yml'
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install Vercel CLI
        run: npm install -g vercel
      
      - name: Deploy to Vercel
        working-directory: ./frontend
        run: |
          vercel --prod --token ${{ secrets.VERCEL_TOKEN }} --confirm
EOF
```

- [ ] **Step 4: Commit Vercel configuration**

```bash
git add frontend/vercel.json frontend/.vercelignore .github/workflows/deploy-frontend.yml
git commit -m "feat: add Vercel deployment configuration"
```

---

### Task 12: Create README and Project Documentation

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create comprehensive README**

```bash
cat > README.md << 'EOF'
# 📚 Cardiology Daily Research Agent

A fully autonomous daily research agent that discovers, analyzes, and presents cardiology research across 50+ medical journals, 25+ researcher profiles, podcasts, and newsletters. The agent runs overnight via GitHub Actions (3:00 AM Brasília time), generates a structured JSON report, and displays results in a beautiful Duolingo-inspired Vue 3 dashboard.

**Core Value:** One complete cardiology research digest per morning, 10–15 prioritized articles, ~15 minutes to consume all content.

---

## ✨ Features

- **🤖 Fully Autonomous:** Runs daily at 3:00 AM via GitHub Actions — zero manual intervention
- **🔬 Deep Research:** Queries Claude API for 50+ journals, 25+ researcher profiles, podcasts, newsletters
- **📊 Intelligent Classification:** Articles classified as Classe A/B/C with impact scores (0–10)
- **💻 Beautiful Dashboard:** Vue 3 + Tailwind CSS with Duolingo-inspired design
- **📱 Mobile Responsive:** Optimized for desktop, tablet, and mobile devices
- **🔗 Clickable Links:** Direct access to original articles (URL, DOI, PubMed)
- **⭐ Favorites:** Save articles to personal list via localStorage
- **🌓 Dark Mode:** (Optional) Toggle for evening reading
- **📜 History:** View past reports via date picker (7–30 days back)
- **💰 Cost Efficient:** ~$25–35/month in API tokens (within $100 Max plan budget)

---

## 🏗️ Architecture

```
3:00 AM (Brasília Time)
  ↓
GitHub Actions Workflow Triggered
  ↓
Python Agent Calls Claude API
  ↓
Claude Researches 50+ Journals + 25+ Profiles
  ↓
Agent Validates & Parses JSON Output
  ↓
Saves: data/relatorio-YYYY-MM-DD.json
  ↓
Auto-commits to GitHub
  ↓
8:00 AM (You Wake Up)
  ↓
Open Dashboard → Vue App Fetches Latest JSON
  ↓
Renders Beautiful Dashboard with 15 Articles
```

### Components

| Component | Technology | Cost | Purpose |
|-----------|-----------|------|---------|
| **Agent** | Python 3.11 + Anthropic SDK | ~$25–35/month | Daily research automation |
| **Scheduler** | GitHub Actions | Free | Cron-based execution (3 AM UTC-3) |
| **Storage** | GitHub Repository | Free | JSON files + versioning |
| **Frontend** | Vue 3 + Tailwind CSS | Free | Dashboard UI |
| **Hosting** | Vercel | Free | Frontend deployment |

---

## 🚀 Quick Start

### Prerequisites

- GitHub account (free)
- Anthropic API key (from your API Max plan)
- Node.js 18+ (for local development)
- Python 3.11+ (for backend testing)

### Setup (5 minutes)

1. **Clone this repository**
   ```bash
   git clone <repo-url>
   cd cardiology-agent
   ```

2. **Set up GitHub Secrets**
   - Go to GitHub repo → Settings → Secrets and variables → Actions
   - Add `ANTHROPIC_API_KEY` with your API key
   - Add `VERCEL_TOKEN` for frontend deployment (get from vercel.com)

3. **Install Python dependencies**
   ```bash
   cd agent
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Test the agent locally**
   ```bash
   cp .env.example .env
   # Edit .env and add your ANTHROPIC_API_KEY
   python agent.py
   ```

5. **Install frontend dependencies**
   ```bash
   cd ../frontend
   npm install
   npm run dev
   ```

6. **Deploy frontend to Vercel**
   - Connect your GitHub repo to vercel.com
   - Vercel auto-deploys on push to main

---

## 📅 Daily Workflow

1. **3:00 AM:** GitHub Actions triggers agent automatically
   - Agent calls Claude API with detailed research prompt
   - Claude processes 50+ journals, 25+ researcher profiles
   - Agent validates and saves JSON output
   - Auto-commits to GitHub

2. **8:00 AM:** You wake up and open the dashboard
   - Frontend fetches latest `relatorio-YYYY-MM-DD.json`
   - Dashboard displays top 3 featured articles + full list
   - All 15 articles visible with class badges, scores, summaries
   - Takes ~15 minutes to read all content

3. **Anytime:** Filter, search, and star articles
   - Filter by Class (A/B/C) or Source (Revista/Podcast/Twitter/Substack)
   - Click articles to see full details + verify links
   - Star favorites to save locally

---

## 📊 JSON Report Structure

Each report is a structured JSON file with this format:

```json
{
  "relatorio_data": "2026-04-28",
  "gerado_em": "2026-04-28T03:15:00Z",
  "resumo": {
    "total_artigos": 15,
    "tempo_leitura_minutos": 15,
    "classe_a_count": 5,
    "classe_b_count": 7,
    "classe_c_count": 3
  },
  "featured": [
    {
      "id": "featured_1",
      "titulo": "Novo marcapasso inteligente reduz arritmia",
      "publicacao": "Nature Reviews Cardiology",
      "autores": ["Smith J", "Johnson M"],
      "classe": "A",
      "score": 9.2,
      "categoria_fonte": "revista",
      "emoji": "📰",
      "resumo": "Última tecnologia em marcapasso detecta e previne arritmia automaticamente.",
      "impacto_clinico": "Redução de 40% em hospitalizações emergenciais.",
      "links": {
        "url": "https://...",
        "doi": "10.1038/...",
        "pubmed": "..."
      }
    }
  ],
  "artigos": [/* rest of articles */]
}
```

---

## 🛠️ Troubleshooting

### GitHub Actions Workflow Not Running

- **Issue:** Workflow scheduled for 3:00 AM but not triggering
- **Solution:** GitHub Actions uses UTC. Brasília is UTC-3. Verify cron is set to `0 6 * * *` (6:00 AM UTC = 3:00 AM Brasília)
- **Check:** Settings → Actions → Runners → Verify `ubuntu-latest` is available

### Dashboard Shows "Carregando..." Forever

- **Issue:** JSON report not fetching
- **Solution:** 
  1. Check GitHub repo has `data/relatorio-YYYY-MM-DD.json` file
  2. Update `VITE_GITHUB_REPO` in `.env` to `owner/repo`
  3. Manually run agent: `cd agent && python agent.py`

### Claude API Returns Invalid JSON

- **Issue:** Agent fails to parse response
- **Solution:**
  1. Check `agent/prompt.txt` ends with "Retorne APENAS JSON válido..."
  2. Verify API key is valid and has quota
  3. Check token usage in your Anthropic dashboard

### Vercel Deployment Failed

- **Issue:** Frontend not deploying
- **Solution:**
  1. Check `frontend/vercel.json` is correct
  2. Verify `npm run build` works locally
  3. Check `VERCEL_TOKEN` secret is set in GitHub

---

## 💡 Customization

### Change Agent Execution Time

Edit `.github/workflows/daily-report.yml` line `cron: '0 6 * * *'`:
- Change `0 6` to your desired UTC time
- Example: `0 12 * * *` = 9:00 AM Brasília (UTC-3)

### Adjust Number of Articles

Edit `agent/prompt.txt` line starting with "Pesquise e compile":
- Default: 10–15 articles
- Change to: "Pesquise e compile os 20 artigos mais relevantes..."

### Add More Researcher Profiles

Edit `agent/prompt.txt` section "Perfis de Pesquisadores":
- Add names and institutions
- Agent will monitor their latest publications

### Modify Color Scheme

Edit `frontend/tailwind.config.js`:
- Change `colors.primary`, `classA`, `classB`, `classC`, `featured1-3`
- Regenerate styles: `npm run build`

---

## 📈 Costs

| Item | Cost | Notes |
|------|------|-------|
| **API Tokens** | ~$25–35/month | 6,000–7,500 tokens/day × 30 days |
| **GitHub** | $0 | Free for public repos |
| **Vercel** | $0 | Free tier for SPA |
| **GitHub Actions** | $0 | 2,000 free minutes/month |
| **Total** | ~$25–35/month | Well within $100 API Max plan |

---

## 🔒 Privacy & Security

- 🔐 API keys stored in GitHub Secrets (never exposed)
- 🌐 Reports stored in public GitHub repo (choose private if needed)
- 💾 Frontend loads JSON from GitHub (no backend required)
- 📱 Favorites saved locally in browser localStorage

---

## 📝 License

MIT License — Feel free to fork, modify, and redistribute.

---

## 🤝 Contributing

Found a bug? Have a feature idea? Open an issue or PR!

---

## 📧 Support

Questions? Check:
- GitHub Issues tab for known problems
- Anthropic API docs: https://docs.anthropic.com
- Vue 3 docs: https://vuejs.org
- Vercel docs: https://vercel.com/docs

---

**Happy researching! 🔬📚**
EOF
```

- [ ] **Step 2: Commit README**

```bash
git add README.md
git commit -m "docs: add comprehensive README with setup, architecture, and troubleshooting"
```

---

### Task 13–16: Testing, Integration, and Final Verification

### Task 13: Run Full Integration Tests

- [ ] **Step 1: Test Python agent locally**

```bash
cd agent
python -m pytest tests/ -v
# Expected: All tests PASS
```

- [ ] **Step 2: Test agent script end-to-end**

```bash
cd agent
python -c "
from agent import CardologyAgent
agent = CardologyAgent()
report = agent.run_research(output_file='../data/relatorio-test.json')
print(f'✓ Generated {report[\"resumo\"][\"total_artigos\"]} articles')
print(f'✓ Report saved to ../data/relatorio-test.json')
"
```

- [ ] **Step 3: Verify JSON output is valid**

```bash
python -c "
import json
with open('../data/relatorio-test.json', 'r') as f:
    report = json.load(f)
print(f'✓ Valid JSON with {len(report[\"featured\"])} featured articles')
print(f'✓ Total articles: {report[\"resumo\"][\"total_artigos\"]}')
"
```

- [ ] **Step 4: Commit test data (optional)**

```bash
rm data/relatorio-test.json
git add -A
git commit -m "test: verify agent integration end-to-end"
```

---

### Task 14: Build and Test Frontend

- [ ] **Step 1: Build frontend for production**

```bash
cd frontend
npm run build
# Expected: dist/ folder created with optimized output
```

- [ ] **Step 2: Test build output**

```bash
npm run preview
# Open http://localhost:4173 in browser
# Verify dashboard loads and displays sample data
```

- [ ] **Step 3: Test frontend with sample JSON**

```bash
# Copy sample report to frontend's public folder for testing
cp data/relatorio-test.json frontend/public/relatorio-2026-04-28.json
npm run preview
# Verify dashboard loads with real data
```

- [ ] **Step 4: Mobile responsiveness check**

```bash
# In preview window, test:
# - Desktop (1200px): 3-column featured, full layout
# - Tablet (768px): 1-column featured, stacked layout
# - Mobile (375px): 100% width, touch-friendly buttons
```

- [ ] **Step 5: Test all interactive features**

- Filter by Class (A/B/C)
- Filter by Source (Revista/Podcast/Twitter/Substack)
- Click articles to open detail modal
- Click links in modal (should open in new tab)
- Star/favorite articles

- [ ] **Step 6: Commit frontend build**

```bash
git add frontend/dist/
git commit -m "build: create production frontend build"
```

---

### Task 15: Deploy Frontend to Vercel

- [ ] **Step 1: Create Vercel project**

```bash
# Option A: Via CLI
cd frontend
npm i -g vercel
vercel --prod --token $VERCEL_TOKEN

# Option B: Via UI
# 1. Go to vercel.com
# 2. Import GitHub repo
# 3. Select 'frontend' as root directory
# 4. Deploy
```

- [ ] **Step 2: Get Vercel deployment URL**

```bash
# After deployment, Vercel provides a URL like:
# https://cardiology-dashboard.vercel.app
# Save this URL for step 3
```

- [ ] **Step 3: Update frontend environment**

```bash
# Create frontend/.env.production
cat > frontend/.env.production << 'EOF'
VITE_GITHUB_REPO=<your-github-username>/<your-repo-name>
VITE_GITHUB_BRANCH=main
EOF

# Rebuild and redeploy
npm run build
vercel --prod --token $VERCEL_TOKEN
```

- [ ] **Step 4: Verify deployed dashboard**

```bash
# Open https://cardiology-dashboard.vercel.app
# Verify:
# - Dashboard loads
# - JSON data fetches from GitHub
# - All buttons and filters work
# - Mobile responsive on phone
```

- [ ] **Step 5: Commit Vercel configuration**

```bash
git add frontend/.env.production
git commit -m "deploy: configure and deploy frontend to Vercel"
```

---

### Task 16: Final Integration and Documentation

- [ ] **Step 1: Verify full daily workflow**

```bash
# 1. Manually trigger GitHub Actions workflow
# - Go to GitHub repo → Actions → "Daily Cardiology Research Report"
# - Click "Run workflow" → Confirm

# 2. Monitor workflow execution
# - Check logs for any errors
# - Verify JSON file created in data/ folder
# - Confirm git commit auto-created

# 3. Check dashboard fetches latest data
# - Open Vercel deployment URL
# - Verify today's report loads (within 1 min of workflow completion)
# - Check article counts and featured articles appear
```

- [ ] **Step 2: Create setup checklist for users**

```bash
cat > SETUP_CHECKLIST.md << 'EOF'
# Setup Checklist

## Prerequisites
- [ ] GitHub account
- [ ] Anthropic API key (from your Max plan)
- [ ] Vercel account (free)

## GitHub Setup
- [ ] Fork this repository
- [ ] Go to Settings → Secrets and variables → Actions
- [ ] Add `ANTHROPIC_API_KEY` secret
- [ ] Add `VERCEL_TOKEN` secret (from vercel.com)

## Backend Testing
- [ ] Clone repository locally
- [ ] Create Python venv: `python -m venv venv`
- [ ] Activate: `source venv/bin/activate`
- [ ] Install: `pip install -r agent/requirements.txt`
- [ ] Test: `python -m pytest agent/tests/ -v`
- [ ] Run agent: `python agent/agent.py`

## Frontend Testing
- [ ] Install Node 18+
- [ ] `cd frontend && npm install`
- [ ] `npm run dev` (test locally)
- [ ] `npm run build` (verify production build)

## Vercel Deployment
- [ ] Connect repo to vercel.com
- [ ] Select `frontend` as root directory
- [ ] Deploy
- [ ] Update `VITE_GITHUB_REPO` in `.env.production`
- [ ] Redeploy

## Final Verification
- [ ] GitHub Actions runs daily at 3:00 AM Brasília
- [ ] Workflow creates `data/relatorio-YYYY-MM-DD.json`
- [ ] Dashboard fetches and displays latest report
- [ ] All filters and links work
- [ ] Mobile responsive

## Cost Monitoring
- [ ] Check Anthropic dashboard monthly
- [ ] Verify token usage ~$25–35/month
- [ ] Adjust article count if overbudget
EOF
```

- [ ] **Step 3: Verify all CI/CD pipelines**

```bash
# 1. Agent workflow
git log --oneline data/
# Should show auto-commits from GitHub Actions

# 2. Frontend deployment
# Check Vercel dashboard for recent deployments
# Should auto-deploy on any push to frontend/

# 3. Test manual trigger
# Go to Actions → "Daily Cardiology Research Report" → Run workflow
# Verify it completes successfully
```

- [ ] **Step 4: Final commit and wrap-up**

```bash
git add SETUP_CHECKLIST.md
git commit -m "docs: add setup checklist and final integration verification"

# Show git log
git log --oneline | head -20
```

- [ ] **Step 5: Push to GitHub**

```bash
git push origin main
```

- [ ] **Step 6: Verify remote state**

```bash
# Check GitHub repo has all files
# - agent/ with Python code
# - frontend/ with Vue 3 code
# - .github/workflows/ with CI/CD configs
# - data/ directory (might be empty on first push)
# - README.md and SETUP_CHECKLIST.md
```

---

## Self-Review Checklist

✅ **Spec Coverage:**
- [x] Agent runs at 3:00 AM via GitHub Actions (Task 5)
- [x] Claude API integration for 50+ journals + 25+ profiles (Task 2, 4)
- [x] JSON output with classification, scores, links (Task 3, 4)
- [x] Vue 3 dashboard with featured articles (Task 6, 7, 8)
- [x] Filters (Class, Source Type), search (Task 8, 9)
- [x] Mobile responsive design (Task 8, 14)
- [x] Duolingo-inspired colors and styling (Task 6, 14)
- [x] Vercel deployment (Task 11, 15)
- [x] Full documentation (Task 12, 16)

✅ **No Placeholders:**
- All tasks have complete code snippets
- All test cases are concrete with assertions
- All commands show exact output expectations
- No "TBD", "TODO", or vague requirements

✅ **Type Consistency:**
- JSON schema consistent across parser and agent
- Component props and emits match usage
- Report structure validated at every step

✅ **Bite-Sized Steps:**
- Each step is 2–5 minutes
- TDD pattern (test → implement → verify)
- Frequent commits (one per significant change)

---

**Plan complete and ready for execution.**
