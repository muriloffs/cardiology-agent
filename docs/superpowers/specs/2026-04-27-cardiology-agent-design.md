# Cardiology Daily Research Agent — Design Specification
**Date:** April 27, 2026  
**Version:** 1.0 (Final)

---

## Executive Summary

A fully autonomous daily research agent that discovers, analyzes, and presents cardiology research across 50+ medical journals, 25+ researcher profiles, podcasts, and newsletters. The agent runs overnight via GitHub Actions (3:00 AM), generates a structured JSON report with curated articles, and displays results in a beautiful Duolingo-inspired dashboard accessible immediately upon waking.

**Core Value:** One complete cardiology research digest per morning, 10–15 prioritized articles, ~15 minutes to consume all content.

---

## 1. System Architecture

### 1.1 Execution Model

| Component | Technology | Cost | Schedule |
|-----------|-----------|------|----------|
| **Agent (Backend)** | Python 3.11+ + Anthropic SDK | ~$25–35/month (tokens) | GitHub Actions: 3:00 AM daily (Brasília time) |
| **Storage** | GitHub repository (JSON files) | Free (gratis) | Auto-commits via Actions |
| **Frontend** | Vue 3 + Tailwind CSS | Free | Vercel OR local deployment |
| **Scheduler** | GitHub Actions CI/CD | Free | Cron-based automation |

### 1.2 Daily Workflow (Autonomous)

```
03:00 AM (Brasília)
  ↓
GitHub Actions workflow triggered
  ↓
Python agent starts → Calls Claude API with detailed prompt
  ↓
Agent researches: 50+ journals, 25+ profiles, podcasts, newsletters
  ↓
Claude generates structured output (10–15 articles, classifications, links)
  ↓
Python processes output → Parses to clean JSON
  ↓
Saves: data/relatorio-2026-04-27.json
  ↓
Auto-commits to GitHub with timestamp
  ↓
08:00 AM (you wake up)
  ↓
Open dashboard → Vue app fetches latest JSON from GitHub
  ↓
Beautiful interface renders with 15 articles ready
```

### 1.3 Data Flow

1. **Agent Output** → Structured JSON with:
   - Article metadata (title, source, authors)
   - Classification (Classe A/B/C, score 0–10)
   - Source type (Revista, X/Twitter, Podcast, Substack)
   - Summary (2–3 lines, balanced detail)
   - Clinical impact statement ("O que muda amanhã")
   - Clickable links (Official URL, DOI, PubMed)

2. **Storage** → `data/relatorio-YYYY-MM-DD.json` (public GitHub repo, version history)

3. **Frontend** → Vue app:
   - Fetches JSON from GitHub (1-hour cache check)
   - Renders dashboard
   - Enables filtering, searching, favoriting (localStorage)

---

## 2. Frontend Design

### 2.1 Core Layout (Single-Page, Scrollable)

**Header Section:**
- Title: "📚 Relatório de Cardiologia"
- Date: "Segunda, 28 de Abril de 2026"
- Stats cards: "15 Artigos hoje" | "~15 min Leitura média"

**Featured Section:**
- Top 3 "Big Ones" of the day (prominent colored cards)
- Large title, publication, class badge, score highlight
- Gradient backgrounds (red, teal, orange) for visual hierarchy

**Article List (Main Content):**
- Scrollable feed of all 15 articles
- Each card contains:
  - **Class Badge** (A/B/C with color: red/yellow/green)
  - **Score** (0–10 numeric)
  - **Title** (clickable → expands/modal with full details)
  - **Source Publication** (e.g., "Nature Reviews Cardiology")
  - **Summary** (2–3 lines)
  - **Clinical Impact** ("O que muda amanhã")
  - **Source Category Badge** (📰 Revista | 🐦 X/Twitter | 🎙️ Podcast | 📝 Substack)
  - **Action Links** (context-specific):
    - 📖 Ler artigo (if article link available)
    - 🔗 DOI (if DOI available)
    - 🔍 PubMed (if applicable)

**Filters & Navigation (Sticky Header or Sidebar):**
- **Class Filter** (buttons): A | B | C | All
- **Source Type Filter** (buttons): Revistas | X/Twitter | Podcasts | Substacks | All
- **Search** (keyword search by title, author)
- **History** (date picker to see previous reports)
- **Manual Refresh** (check for new data)

### 2.2 Design System (Duolingo Inspiration)

**Color Palette:**
- Primary: Purple/Blue gradient (#667eea → #764ba2)
- Class A: Red (#FF6B6B)
- Class B: Orange (#FFA500)
- Class C: Green (#4CAF50)
- Featured gradient backgrounds:
  - Big One 1: Red (#FF6B6B)
  - Big One 2: Teal (#20B2AA)
  - Big One 3: Orange (#FF9800)

**Typography:**
- Readable sans-serif (Segoe UI, -apple-system)
- Headers: Bold, clear hierarchy
- Body: 13–14px, high readability
- Spacing: 8px, 16px, 24px grid

**Component Style:**
- Rounded corners (6–8px)
- Subtle shadows (elevation)
- Hover effects (slight scale, color shift)
- Card padding: 16px standard
- Mobile-first, responsive design (< 768px: single column)

### 2.3 Mobile Responsiveness

- **Desktop (> 768px):** 2-column layout for featured cards, full grid
- **Tablet (768px–480px):** 1-column stacked featured, single article list
- **Mobile (< 480px):** 100% width, optimized touch targets
- Safe zones: Article content respects 9:16 and 4:5 viewport margins

---

## 3. Agent (Backend) Specification

### 3.1 Inputs

**Prompt to Claude API:**
- User's detailed daily research requirements
- List of 50+ medical journals to search
- 25+ researcher/expert profiles to monitor
- Podcast feeds and newsletters to include
- Classification criteria (what makes Classe A vs B vs C)
- Tone & style guidance (balanced, evidence-based, actionable)

**Research Scope:**
- Last 24 hours of publications
- Recent X/Twitter posts from key cardiologists
- Latest podcast episodes (filtered)
- Substack articles from trusted sources
- Focus on: new treatments, clinical trials, research breakthroughs, policy changes

### 3.2 Processing

1. Parse Claude's structured output (markdown or JSON)
2. Extract and validate:
   - Article title, source, authors
   - Classification (Classe A/B/C)
   - Score (0–10)
   - Summary (enforce 2–3 lines)
   - Clinical impact statement
   - Links (URL, DOI, PubMed ID)
   - Source type (infer from source or explicit tagging)
3. Generate clean JSON structure
4. Ensure 10–15 articles (filter out marginal pieces)

### 3.3 Output Structure (JSON)

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
  "artigos": [
    {
      "id": "art_001",
      "titulo": "...",
      "publicacao": "...",
      "autores": ["..."],
      "classe": "A",
      "score": 8.5,
      "categoria_fonte": "revista|podcast|twitter|substack",
      "emoji": "📰|🎙️|🐦|📝",
      "resumo": "...",
      "impacto_clinico": "...",
      "links": {
        "url": "https://...",
        "doi": "...",
        "pubmed": "...",
        "twitter_link": "..." 
      }
    }
  ]
}
```

---

## 4. User Workflows

### 4.1 Daily User Flow (Fully Automated)

1. **3:00 AM:** Agent runs autonomously (you're sleeping)
2. **8:00 AM:** Wake up, open dashboard
3. **Home Page:** See top 3 featured articles + stats at a glance
4. **Scroll:** Browse all 15 articles with summaries
5. **Decide:** Filter by Class or Source Type if interested in specific category
6. **Deep Dive:** Click article → see full summary + clinical impact + links
7. **Verify:** Click links to read original source (DOI, PubMed, official URL)
8. **Learn:** ~15 minutes total to consume all curated research

### 4.2 Advanced Features (Optional)

- **Favorites:** Star articles to save to personal list (localStorage)
- **Dark Mode:** Toggle for evening reading
- **History:** Date picker to view past reports (7–30 days back)
- **Search:** Keyword search across all articles in history
- **Export:** (Optional future) Save day's report as PDF or email

---

## 5. Implementation Phases

### Phase 1: Core Agent (Week 1)
- Python script with Claude API integration
- GitHub Actions workflow (cron scheduler)
- JSON output generation
- Basic error handling & logging

### Phase 2: Frontend (Week 2)
- Vue 3 app scaffold
- Dashboard layout & components
- Styling with Tailwind CSS
- Fetch & render JSON

### Phase 3: Polish & Deploy (Week 3)
- Mobile responsiveness
- Filter & search functionality
- UI refinements (hover states, animations)
- Deploy to Vercel (or local)

---

## 6. Success Criteria

✅ **Functional:**
- Agent runs daily at 3:00 AM without manual intervention
- Generates 10–15 articles per day
- Dashboard loads in < 2 seconds
- All links verified and working
- Mobile responsive on all devices

✅ **User Experience:**
- User wakes up with complete digest ready
- Can consume all content in ~15 minutes
- Easy filtering and searching
- Beautiful, intuitive interface

✅ **Operational:**
- Cost: ~$25–35/month (well within $100 API budget)
- No ongoing maintenance required
- Historical data preserved (GitHub)
- Clear debugging via GitHub Actions logs

---

## 7. Constraints & Assumptions

| Constraint | Value |
|-----------|-------|
| **Daily articles** | 10–15 (target) |
| **Update frequency** | Once daily, 3:00 AM Brasília time |
| **Reading time** | ~15 minutes for full digest |
| **Token budget** | ~$25–35/month (within $100 API plan) |
| **Repository** | Public GitHub (free, enables version history) |
| **User GitHub account** | Required (for repository + Actions) |
| **Internet connectivity** | Required for frontend to fetch JSON |

**Assumption:** User will validate agent output manually 1–2x per week to ensure quality (optional QA gate).

---

## 8. Deployment Options

1. **Frontend: Vercel (Recommended)**
   - Free tier supports this use case
   - Auto-deploys on commit
   - Global CDN for fast loading
   - Alternative: Run locally on your PC

2. **Agent: GitHub Actions (Built-in)**
   - No additional infrastructure needed
   - Logs accessible in GitHub repo
   - Reliable cron scheduling

3. **Storage: GitHub (Built-in)**
   - Data files versioned
   - Public OR private (your choice)
   - No additional cost

---

## 9. Technical Stack Summary

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Scheduler** | GitHub Actions | Free, reliable, no server needed |
| **Agent** | Python 3.11 + Anthropic SDK | Simple, maintainable, direct API access |
| **LLM** | Claude 3.5 Sonnet (your API Max plan) | Best for research + structured output |
| **Storage** | JSON + GitHub | Version history, free, accessible |
| **Frontend** | Vue 3 + Tailwind CSS | Fast, responsive, Duolingo aesthetic |
| **Deployment** | Vercel (or local) | Free, simple, fast |

---

## 10. Known Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Agent occasionally outputs off-topic articles | Manual validation 1–2x/week; refine prompt over time |
| GitHub API rate limits | Unlikely at 1 request/day; monitor if scaling |
| Link rot (broken URLs) | Verify links before storing; note source-specific handling |
| Token cost overrun | Monitor daily; start with 10–15 articles; adjust scope if needed |
| Dashboard cache stale | Manual refresh button; auto-check every 1 hour |

---

## 11. Future Enhancements (Out of Scope v1.0)

- Multi-specialty support (add neurology, oncology, etc.)
- Email digest delivery
- Slack/Teams integration
- PDF report generation
- Social sharing (Twitter, LinkedIn)
- Advanced NLP summarization
- Comparative analysis across sources

---

**Sign-off:** Design complete and ready for implementation planning.
