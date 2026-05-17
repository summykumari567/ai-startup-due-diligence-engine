# AI Startup Due Diligence Engine

**#062 · ★★★★★ · Demand 91%**

Aggregates data from Crunchbase, news sources, patent databases, and court records to generate comprehensive VC-grade due diligence reports on startups using Claude AI.

---

## Tech Stack

| Tool | Purpose |
|---|---|
| **Claude (Anthropic)** | AI synthesis, scoring, and verdict generation |
| **Crunchbase API v4** | Funding rounds, investors, founders, company profile |
| **Tavily AI Search** | Real-time news, patents, legal records, team research |
| **ReportLab** | PDF report generation |
| **FastAPI** | REST API server |

---

## Project Structure

```
ai-startup-due-diligence-engine/
├── main.py                 # FastAPI app and API endpoints
├── agent.py                # Claude orchestration pipeline
├── crunchbase_client.py    # Crunchbase API v4 wrapper
├── tavily_client.py        # Tavily AI search wrapper
├── pdf_generator.py        # ReportLab PDF report builder
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
└── reports/                # Auto-created: stores generated JSON + PDF reports
```

---

## Prerequisites

- Python 3.10 or higher
- API keys for Anthropic (required), Crunchbase (optional), Tavily (optional)

---

## Installation

**1. Clone the repository**
```bash
git clone https://github.com/summykumari567/ai-startup-due-diligence-engine.git
cd ai-startup-due-diligence-engine
```

**2. Create and activate a virtual environment**
```bash
python -m venv .venv

# On macOS / Linux
source .venv/bin/activate

# On Windows
.venv\Scripts\activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Set up environment variables**
```bash
cp .env.example .env
```

Open `.env` and fill in your API keys:
```
ANTHROPIC_API_KEY=your_anthropic_key_here
CRUNCHBASE_API_KEY=your_crunchbase_key_here
TAVILY_API_KEY=your_tavily_key_here
```

---

## Running the Server

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

Interactive API docs (Swagger UI): `http://localhost:8000/docs`

---

## API Endpoints

### `GET /health`
Check that the server is running.

```bash
curl http://localhost:8000/health
```

Response:
```json
{ "status": "ok" }
```

---

### `POST /analyze`
Run a full due diligence analysis on a company. Returns a structured report and generates a PDF.

**Request body:**
```json
{
  "company_name": "OpenAI",
  "company_domain": "openai.com",
  "crunchbase_slug": "openai",
  "generate_pdf": true
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `company_name` | string | Yes | Name of the company |
| `company_domain` | string | No | Company website domain e.g. `openai.com` |
| `crunchbase_slug` | string | No | Crunchbase URL slug e.g. `openai` |
| `generate_pdf` | boolean | No | Whether to generate a PDF report (default: true) |

**Example response:**
```json
{
  "company_name": "OpenAI",
  "report_id": "a1b2c3d4",
  "summary": "OpenAI is a leading AI research company...",
  "verdict": "BUY",
  "confidence": 0.87,
  "pdf_path": "reports/a1b2c3d4.pdf",
  "sections": {
    "team_analysis": { "score": 9, "summary": "...", "key_people": [...] },
    "market_opportunity": { "score": 10, "tam": "$1T+", "growth_rate": "38% CAGR" },
    "financial_health": { "score": 8, "total_funding": "$11.3B", "last_round": "Series C" },
    "technology_ip": { "score": 9, "patent_count": 45, "moat_assessment": "..." },
    "legal_risk": { "score": 6, "risk_level": "MEDIUM", "lawsuits": [...] },
    "news_sentiment": { "score": 7, "overall_sentiment": "MIXED", "recent_headlines": [...] },
    "red_flags": ["Board instability in 2023"],
    "green_flags": ["$11B+ in funding", "Market leader in LLMs"],
    "investment_recommendation": {
      "verdict": "Strong candidate for Series B participation",
      "suggested_due_diligence_next_steps": ["Review audited financials", "..."],
      "key_questions_for_founders": ["What is the path to profitability?", "..."]
    }
  },
  "sources": [
    { "type": "news", "title": "OpenAI raises...", "url": "https://...", "date": "2024-01-01" }
  ]
}
```

---

### `GET /report/{report_id}`
Retrieve a previously generated report in JSON format.

```bash
curl http://localhost:8000/report/a1b2c3d4
```

---

### `GET /report/{report_id}/pdf`
Download the generated PDF report.

```bash
curl http://localhost:8000/report/a1b2c3d4/pdf --output report.pdf
```

---

## How It Works

The agent runs 5 data collectors in parallel, then passes everything to Claude for synthesis:

```
POST /analyze
     |
     | (all run in parallel)
     |
     +-- Crunchbase      Funding rounds, investors, founders
     +-- Tavily News     Press coverage, controversies, sentiment
     +-- Tavily Patents  Google Patents, Justia patent search
     +-- Tavily Legal    Court records, SEC filings, lawsuits
     +-- Tavily Team     Executive backgrounds, hiring signals
     |
     v
[Claude claude-opus-4-5]
  Scores 6 dimensions (1-10)
  Identifies red flags and green flags
  Writes executive summary
  Issues a verdict (STRONG BUY to STRONG PASS)
     |
     v
JSON cached at  reports/{id}.json
PDF saved at    reports/{id}.pdf
```

---

## Scoring Dimensions

Each dimension is scored 1 to 10 by Claude:

| Dimension | What Claude Evaluates |
|---|---|
| Team Analysis | Founder quality, domain expertise, team completeness |
| Market Opportunity | TAM size, growth rate, competitive positioning |
| Financial Health | Total funding, runway estimate, investor quality, revenue signals |
| Technology & IP | Patent portfolio, technical moat, product differentiation |
| Legal Risk | Active lawsuits, regulatory exposure, SEC/compliance flags |
| News Sentiment | Press coverage tone, public perception, controversy history |

---

## Verdict Scale

| Verdict | Meaning |
|---|---|
| STRONG BUY | Exceptional opportunity, high conviction |
| BUY | Solid investment candidate |
| NEUTRAL | Insufficient signal, needs more diligence |
| PASS | Significant concerns outweigh positives |
| STRONG PASS | Critical red flags — do not invest |

---

## PDF Report Contents

The generated PDF includes:

1. Cover page with company name, verdict badge, confidence score, and report metadata
2. Executive summary with quick stats (green flags, red flags, verdict)
3. Scorecard — all 6 dimensions with visual score bars
4. Team Analysis — key people table, strengths and concerns
5. Market Opportunity — TAM, growth rate, competitive landscape
6. Financial Health — funding rounds, key investors, runway estimate
7. Technology and IP — patent table, moat assessment
8. Legal Risk — lawsuit table, regulatory flags, risk level badge
9. News and Sentiment — recent headlines table, sentiment analysis
10. Flags and Recommendation — next steps, key questions for founders
11. Sources appendix — all URLs used, grouped by type

---

## Environment Variables

| Variable | Required | Where to get it |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | https://console.anthropic.com |
| `CRUNCHBASE_API_KEY` | No (optional) | https://data.crunchbase.com/docs |
| `TAVILY_API_KEY` | No (optional) | https://tavily.com |

The engine works with only `ANTHROPIC_API_KEY`. Crunchbase and Tavily enhance report quality significantly. Both clients return graceful fallback data when keys are not set, so the report will still be generated.

---

## Dependencies

```
anthropic>=0.30.0       Claude AI SDK
fastapi>=0.111.0        REST API framework
uvicorn[standard]       ASGI server
httpx>=0.27.0           HTTP client for API calls
pydantic>=2.7.0         Request/response validation
python-dotenv>=1.0.0    .env file loading
reportlab>=4.2.0        PDF generation
tavily-python>=0.3.0    Tavily AI search SDK
```

---

## Notes

- The `reports/` folder is created automatically on first run
- Claude model used: `claude-opus-4-5` — this can be changed in `agent.py`
- All 5 data collectors handle errors individually — if one fails, the rest still contribute to the report
- For production deployments, consider adding: authentication middleware, rate limiting, cloud file storage (e.g. AWS S3 for PDFs), and an async job queue (Celery + Redis) for long-running report generation