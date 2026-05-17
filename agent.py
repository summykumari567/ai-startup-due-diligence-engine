"""
agent.py — Claude-Powered Due Diligence Orchestrator

Pipeline:
  1. Fetch Crunchbase data (funding, team, investors)
  2. Tavily web search (news, sentiment, controversies)
  3. Patent search (Google Patents via Tavily)
  4. Court/legal records search (via Tavily)
  5. Claude synthesizes all data into structured report sections
  6. PDF report generation
"""
import asyncio
import json
import os
import uuid
from datetime import datetime
from typing import Optional

import anthropic

from crunchbase_client import CrunchbaseClient
from tavily_client import TavilyClient
from pdf_generator import PDFReportGenerator


# ── Prompts ────────────────────────────────────────────────────────────────────

SYNTHESIS_PROMPT = """You are a senior VC analyst producing a comprehensive due diligence report.

Analyze ALL the raw data provided and produce a structured JSON report with the following sections.
Return ONLY valid JSON (no markdown, no preamble).

Schema:
{{
  "executive_summary": "<3-4 paragraph high-level verdict for a VC partner>",
  "verdict": "<STRONG BUY | BUY | NEUTRAL | PASS | STRONG PASS>",
  "confidence": <0.0-1.0>,
  "sections": {{
    "company_overview": {{
      "description": "...",
      "founded": "...",
      "headquarters": "...",
      "stage": "...",
      "business_model": "..."
    }},
    "team_analysis": {{
      "score": <1-10>,
      "summary": "...",
      "key_people": [{{"name":"...","role":"...","background":"..."}}],
      "strengths": ["..."],
      "concerns": ["..."]
    }},
    "market_opportunity": {{
      "score": <1-10>,
      "tam": "...",
      "growth_rate": "...",
      "competitive_landscape": "...",
      "positioning": "...",
      "summary": "..."
    }},
    "financial_health": {{
      "score": <1-10>,
      "total_funding": "...",
      "last_round": "...",
      "last_round_date": "...",
      "key_investors": ["..."],
      "runway_estimate": "...",
      "revenue_signals": "...",
      "summary": "..."
    }},
    "technology_ip": {{
      "score": <1-10>,
      "patent_count": <int>,
      "patents": [{{"title":"...","number":"...","filed":"..."}}],
      "tech_stack_signals": ["..."],
      "moat_assessment": "...",
      "summary": "..."
    }},
    "legal_risk": {{
      "score": <1-10>,
      "lawsuits": [{{"case":"...","type":"...","status":"...","year":"..."}}],
      "regulatory_flags": ["..."],
      "risk_level": "<LOW|MEDIUM|HIGH|CRITICAL>",
      "summary": "..."
    }},
    "news_sentiment": {{
      "score": <1-10>,
      "overall_sentiment": "<POSITIVE|NEUTRAL|NEGATIVE|MIXED>",
      "recent_headlines": [{{"title":"...","date":"...","source":"...","sentiment":"..."}}],
      "key_themes": ["..."],
      "summary": "..."
    }},
    "red_flags": ["<critical concern>"],
    "green_flags": ["<positive signal>"],
    "investment_recommendation": {{
      "verdict": "...",
      "suggested_due_diligence_next_steps": ["..."],
      "key_questions_for_founders": ["..."]
    }}
  }}
}}

Company: {company_name}
Domain: {domain}
Date: {date}

--- RAW DATA ---

CRUNCHBASE DATA:
{crunchbase_data}

NEWS & WEB INTELLIGENCE (Tavily):
{news_data}

PATENT DATA:
{patent_data}

LEGAL / COURT RECORDS:
{legal_data}

LINKEDIN / TEAM SIGNALS:
{team_data}
"""


class DueDiligenceAgent:
    def __init__(self):
        self.claude = anthropic.Anthropic()
        self.crunchbase = CrunchbaseClient()
        self.tavily = TavilyClient()
        self.pdf_gen = PDFReportGenerator()
        os.makedirs("reports", exist_ok=True)

    async def run(
        self,
        company_name: str,
        domain: Optional[str] = None,
        crunchbase_slug: Optional[str] = None,
        focus_areas: Optional[list[str]] = None,
        generate_pdf: bool = True,
    ) -> dict:
        report_id = str(uuid.uuid4())[:8]

        # ── Step 1: Parallel data collection ──────────────────────────────────
        print(f"[{report_id}] Collecting data for: {company_name}")

        results = await asyncio.gather(
            self._get_crunchbase(company_name, crunchbase_slug),
            self._get_news(company_name, domain),
            self._get_patents(company_name),
            self._get_legal(company_name),
            self._get_team_signals(company_name, domain),
            return_exceptions=True,
        )

        crunchbase_data, news_data, patent_data, legal_data, team_data = [
            r if not isinstance(r, Exception) else f"Error: {r}"
            for r in results
        ]

        # ── Step 2: Claude synthesis ───────────────────────────────────────────
        print(f"[{report_id}] Synthesizing with Claude...")
        prompt = SYNTHESIS_PROMPT.format(
            company_name=company_name,
            domain=domain or "unknown",
            date=datetime.utcnow().strftime("%Y-%m-%d"),
            crunchbase_data=json.dumps(crunchbase_data, indent=2) if isinstance(crunchbase_data, dict) else str(crunchbase_data),
            news_data=json.dumps(news_data, indent=2) if isinstance(news_data, (dict, list)) else str(news_data),
            patent_data=json.dumps(patent_data, indent=2) if isinstance(patent_data, (dict, list)) else str(patent_data),
            legal_data=json.dumps(legal_data, indent=2) if isinstance(legal_data, (dict, list)) else str(legal_data),
            team_data=json.dumps(team_data, indent=2) if isinstance(team_data, (dict, list)) else str(team_data),
        )

        loop = asyncio.get_event_loop()
        message = await loop.run_in_executor(
            None,
            lambda: self.claude.messages.create(
                model="claude-opus-4-5",
                max_tokens=8192,
                messages=[{"role": "user", "content": prompt}],
            ),
        )

        raw = message.content[0].text.strip()
        report_data = json.loads(raw)

        # ── Step 3: Collect sources ────────────────────────────────────────────
        sources = self._collect_sources(news_data, patent_data, legal_data)

        # ── Step 4: PDF generation ─────────────────────────────────────────────
        pdf_path = None
        if generate_pdf:
            pdf_path = f"reports/{report_id}.pdf"
            self.pdf_gen.generate(
                report_id=report_id,
                company_name=company_name,
                report_data=report_data,
                sources=sources,
                output_path=pdf_path,
            )
            print(f"[{report_id}] PDF saved: {pdf_path}")

        # ── Step 5: Cache JSON ─────────────────────────────────────────────────
        output = {
            "company_name": company_name,
            "report_id": report_id,
            "summary": report_data.get("executive_summary", ""),
            "sections": report_data.get("sections", {}),
            "verdict": report_data.get("verdict", "NEUTRAL"),
            "confidence": report_data.get("confidence", 0.5),
            "pdf_path": pdf_path,
            "sources": sources,
        }
        with open(f"reports/{report_id}.json", "w") as f:
            json.dump(output, f, indent=2)

        return output

    # ── Data collectors ────────────────────────────────────────────────────────

    async def _get_crunchbase(self, company: str, slug: Optional[str]) -> dict:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self.crunchbase.get_company(company, slug)
        )

    async def _get_news(self, company: str, domain: Optional[str]) -> list:
        queries = [
            f"{company} startup news 2024 2025",
            f"{company} funding investment",
            f"{company} controversy scandal",
            f"{company} product launch growth",
        ]
        if domain:
            queries.append(f"site:{domain}")

        loop = asyncio.get_event_loop()
        results = []
        for q in queries:
            r = await loop.run_in_executor(None, lambda q=q: self.tavily.search(q, max_results=5))
            results.extend(r)
        return results

    async def _get_patents(self, company: str) -> list:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.tavily.search(
                f"{company} patent application site:patents.google.com OR site:patents.justia.com",
                max_results=8,
            ),
        )

    async def _get_legal(self, company: str) -> list:
        loop = asyncio.get_event_loop()
        results = []
        for q in [
            f"{company} lawsuit court case",
            f"{company} SEC filing regulatory investigation",
            f"{company} legal dispute settlement",
        ]:
            r = await loop.run_in_executor(None, lambda q=q: self.tavily.search(q, max_results=5))
            results.extend(r)
        return results

    async def _get_team_signals(self, company: str, domain: Optional[str]) -> list:
        loop = asyncio.get_event_loop()
        queries = [
            f"{company} CEO founder background",
            f"{company} leadership team executives",
            f"{company} layoffs hiring employees",
        ]
        results = []
        for q in queries:
            r = await loop.run_in_executor(None, lambda q=q: self.tavily.search(q, max_results=4))
            results.extend(r)
        return results

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _collect_sources(news, patents, legal) -> list[dict]:
        sources = []
        for item in (news or []):
            if isinstance(item, dict) and item.get("url"):
                sources.append({
                    "type": "news",
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "date": item.get("published_date", ""),
                })
        for item in (patents or []):
            if isinstance(item, dict) and item.get("url"):
                sources.append({
                    "type": "patent",
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "date": "",
                })
        for item in (legal or []):
            if isinstance(item, dict) and item.get("url"):
                sources.append({
                    "type": "legal",
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "date": item.get("published_date", ""),
                })
        return sources[:30]