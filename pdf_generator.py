"""
pdf_generator.py — VC-Grade Due Diligence PDF Report Generator

Uses ReportLab Platypus to produce a polished, structured PDF report
with cover page, section scoring, tables, and source appendix.
"""
from __future__ import annotations
import os
from datetime import datetime
from typing import Optional

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether,
)
from reportlab.platypus.flowables import Flowable


# ── Color palette ──────────────────────────────────────────────────────────────
NAVY      = colors.HexColor("#0A1628")
DARK_BLUE = colors.HexColor("#0D2137")
ACCENT    = colors.HexColor("#1E90FF")
GOLD      = colors.HexColor("#F5A623")
GREEN     = colors.HexColor("#27AE60")
RED       = colors.HexColor("#E74C3C")
AMBER     = colors.HexColor("#F39C12")
LIGHT_BG  = colors.HexColor("#F4F7FB")
MID_GREY  = colors.HexColor("#7F8C8D")
BORDER    = colors.HexColor("#D5DDE8")
WHITE     = colors.white
BLACK     = colors.HexColor("#1A1A2E")

VERDICT_COLORS = {
    "STRONG BUY": GREEN,
    "BUY": colors.HexColor("#2ECC71"),
    "NEUTRAL": AMBER,
    "PASS": colors.HexColor("#E67E22"),
    "STRONG PASS": RED,
}

RISK_COLORS = {
    "LOW": GREEN, "MEDIUM": AMBER, "HIGH": colors.HexColor("#E67E22"), "CRITICAL": RED,
}

SENTIMENT_COLORS = {
    "POSITIVE": GREEN, "NEUTRAL": MID_GREY, "NEGATIVE": RED, "MIXED": AMBER,
}


def _score_color(score: float) -> colors.Color:
    if score >= 8:  return GREEN
    if score >= 6:  return AMBER
    return RED


class ScoreBar(Flowable):
    """Custom flowable: horizontal score bar 1–10."""
    def __init__(self, score: float, width: float = 3 * inch):
        super().__init__()
        self.score = min(max(float(score), 0), 10)
        self.bar_width = width
        self.bar_height = 8
        self.width = width
        self.height = 14

    def draw(self):
        filled = self.bar_width * (self.score / 10)
        # Background
        self.canv.setFillColor(BORDER)
        self.canv.roundRect(0, 3, self.bar_width, self.bar_height, 3, fill=1, stroke=0)
        # Fill
        c = _score_color(self.score)
        self.canv.setFillColor(c)
        if filled > 0:
            self.canv.roundRect(0, 3, filled, self.bar_height, 3, fill=1, stroke=0)
        # Label
        self.canv.setFillColor(BLACK)
        self.canv.setFont("Helvetica-Bold", 7)
        self.canv.drawRightString(self.bar_width + 28, 5, f"{self.score:.1f}/10")


class PDFReportGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._build_styles()

    def _build_styles(self):
        """Register custom paragraph styles."""
        base = self.styles

        self.s = {
            "cover_title": ParagraphStyle("CoverTitle",
                fontName="Helvetica-Bold", fontSize=28,
                textColor=WHITE, leading=34, spaceAfter=8),
            "cover_sub": ParagraphStyle("CoverSub",
                fontName="Helvetica", fontSize=13,
                textColor=colors.HexColor("#A8C4E0"), leading=18),
            "cover_meta": ParagraphStyle("CoverMeta",
                fontName="Helvetica", fontSize=10,
                textColor=colors.HexColor("#7FA8C9"), leading=14),
            "h1": ParagraphStyle("H1",
                fontName="Helvetica-Bold", fontSize=16,
                textColor=NAVY, leading=20, spaceBefore=18, spaceAfter=6),
            "h2": ParagraphStyle("H2",
                fontName="Helvetica-Bold", fontSize=12,
                textColor=DARK_BLUE, leading=16, spaceBefore=12, spaceAfter=4),
            "body": ParagraphStyle("Body",
                fontName="Helvetica", fontSize=10,
                textColor=BLACK, leading=15, alignment=TA_JUSTIFY, spaceAfter=6),
            "small": ParagraphStyle("Small",
                fontName="Helvetica", fontSize=8,
                textColor=MID_GREY, leading=11),
            "bullet": ParagraphStyle("Bullet",
                fontName="Helvetica", fontSize=10,
                textColor=BLACK, leading=14, leftIndent=14, spaceAfter=3,
                bulletFontName="Helvetica-Bold", bulletFontSize=10),
            "label": ParagraphStyle("Label",
                fontName="Helvetica-Bold", fontSize=9,
                textColor=MID_GREY, leading=12, spaceAfter=2),
            "verdict_text": ParagraphStyle("VerdictText",
                fontName="Helvetica-Bold", fontSize=22,
                textColor=WHITE, leading=28, alignment=TA_CENTER),
            "source_url": ParagraphStyle("SourceURL",
                fontName="Helvetica", fontSize=7,
                textColor=ACCENT, leading=10),
        }

    # ── Public API ─────────────────────────────────────────────────────────────

    def generate(
        self,
        report_id: str,
        company_name: str,
        report_data: dict,
        sources: list[dict],
        output_path: str,
    ):
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            leftMargin=0.75 * inch,
            rightMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
            title=f"Due Diligence Report — {company_name}",
            author="AI Due Diligence Engine",
        )

        story = []
        sections = report_data.get("sections", {})
        verdict = report_data.get("verdict", "NEUTRAL")
        confidence = report_data.get("confidence", 0.5)
        summary = report_data.get("executive_summary", "")

        # Pages
        story += self._cover_page(company_name, report_id, verdict, confidence)
        story += self._executive_summary(summary, verdict, sections)
        story += self._scorecard(sections)
        story += self._section_team(sections.get("team_analysis", {}))
        story += self._section_market(sections.get("market_opportunity", {}))
        story += self._section_financial(sections.get("financial_health", {}))
        story += self._section_ip(sections.get("technology_ip", {}))
        story += self._section_legal(sections.get("legal_risk", {}))
        story += self._section_news(sections.get("news_sentiment", {}))
        story += self._flags_and_recommendation(sections)
        story += self._sources_appendix(sources)

        doc.build(story, onFirstPage=self._page_header_footer, onLaterPages=self._page_header_footer)

    # ── Cover Page ─────────────────────────────────────────────────────────────

    def _cover_page(self, company: str, report_id: str, verdict: str, confidence: float) -> list:
        story = []
        # Dark banner via colored table
        verdict_color = VERDICT_COLORS.get(verdict, AMBER)

        banner_data = [[Paragraph(f"DUE DILIGENCE REPORT", self.s["cover_sub"])]]
        banner = Table(banner_data, colWidths=[7 * inch])
        banner.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), NAVY),
            ("TOPPADDING", (0, 0), (-1, -1), 28),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 20),
        ]))
        story.append(banner)

        title_data = [[Paragraph(company, self.s["cover_title"])]]
        title_table = Table(title_data, colWidths=[7 * inch])
        title_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), NAVY),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 28),
            ("LEFTPADDING", (0, 0), (-1, -1), 20),
        ]))
        story.append(title_table)

        # Verdict badge
        verdict_data = [[Paragraph(verdict, self.s["verdict_text"])]]
        verdict_table = Table(verdict_data, colWidths=[7 * inch])
        verdict_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), verdict_color),
            ("TOPPADDING", (0, 0), (-1, -1), 18),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 18),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        story.append(verdict_table)
        story.append(Spacer(1, 12))

        # Meta info
        meta_data = [
            ["Report ID", report_id, "Confidence", f"{confidence * 100:.0f}%"],
            ["Generated", datetime.utcnow().strftime("%B %d, %Y"), "Classification", "CONFIDENTIAL"],
            ["Engine", "AI Due Diligence Engine v1.0", "Powered by", "Claude · Crunchbase · Tavily"],
        ]
        meta_table = Table(meta_data, colWidths=[1.2 * inch, 2.3 * inch, 1.2 * inch, 2.3 * inch])
        meta_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TEXTCOLOR", (0, 0), (-1, -1), BLACK),
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT_BG, WHITE]),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(meta_table)
        story.append(PageBreak())
        return story

    # ── Executive Summary ──────────────────────────────────────────────────────

    def _executive_summary(self, summary: str, verdict: str, sections: dict) -> list:
        story = [Paragraph("Executive Summary", self.s["h1"]),
                 HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=8)]

        # Red/green flag quick stats
        flags = sections.get("red_flags", [])
        green = sections.get("green_flags", [])
        stat_data = [
            [Paragraph(f"<b>{len(green)}</b><br/>Green Flags", self.s["body"]),
             Paragraph(f"<b>{len(flags)}</b><br/>Red Flags", self.s["body"]),
             Paragraph(f"<b>{verdict}</b><br/>Verdict", self.s["body"])],
        ]
        stat_table = Table(stat_data, colWidths=[2.33 * inch, 2.33 * inch, 2.33 * inch])
        stat_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#EAF7EE")),
            ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#FDECEA")),
            ("BACKGROUND", (2, 0), (2, 0), LIGHT_BG),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ]))
        story += [stat_table, Spacer(1, 12)]

        # Summary paragraphs
        for para in summary.split("\n\n"):
            if para.strip():
                story.append(Paragraph(para.strip(), self.s["body"]))
        return story

    # ── Scorecard ──────────────────────────────────────────────────────────────

    def _scorecard(self, sections: dict) -> list:
        keys = [
            ("team_analysis", "Team"),
            ("market_opportunity", "Market Opportunity"),
            ("financial_health", "Financial Health"),
            ("technology_ip", "Technology & IP"),
            ("legal_risk", "Legal Risk"),
            ("news_sentiment", "News Sentiment"),
        ]
        story = [PageBreak(), Paragraph("Scorecard", self.s["h1"]),
                 HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=8)]

        rows = [["Category", "Score", "Indicator"]]
        for key, label in keys:
            score = sections.get(key, {}).get("score", 5)
            rows.append([label, f"{score}/10", ScoreBar(score)])

        t = Table(rows, colWidths=[2.8 * inch, 0.7 * inch, 3.5 * inch])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(t)
        return story

    # ── Section helpers ────────────────────────────────────────────────────────

    def _section_team(self, data: dict) -> list:
        story = [PageBreak(), Paragraph("Team Analysis", self.s["h1"]),
                 HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=6)]
        story.append(Paragraph(data.get("summary", ""), self.s["body"]))

        people = data.get("key_people", [])
        if people:
            rows = [["Name", "Role", "Background"]]
            for p in people[:8]:
                rows.append([p.get("name", ""), p.get("role", ""), p.get("background", "")[:120]])
            t = Table(rows, colWidths=[1.5 * inch, 1.5 * inch, 4 * inch])
            t.setStyle(self._base_table_style())
            story += [Spacer(1, 6), t]

        story += self._strengths_concerns(data)
        return story

    def _section_market(self, data: dict) -> list:
        story = [PageBreak(), Paragraph("Market Opportunity", self.s["h1"]),
                 HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=6)]
        for field, label in [("tam", "TAM"), ("growth_rate", "Growth Rate"), ("positioning", "Positioning")]:
            v = data.get(field, "")
            if v:
                story.append(Paragraph(f"<b>{label}:</b> {v}", self.s["body"]))
        story.append(Paragraph(data.get("summary", ""), self.s["body"]))
        return story

    def _section_financial(self, data: dict) -> list:
        story = [PageBreak(), Paragraph("Financial Health", self.s["h1"]),
                 HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=6)]

        kv = [
            ("Total Funding", data.get("total_funding", "N/A")),
            ("Last Round", data.get("last_round", "N/A")),
            ("Last Round Date", data.get("last_round_date", "N/A")),
            ("Runway Estimate", data.get("runway_estimate", "N/A")),
            ("Revenue Signals", data.get("revenue_signals", "N/A")),
        ]
        rows = [[Paragraph(f"<b>{k}</b>", self.s["body"]), Paragraph(v, self.s["body"])] for k, v in kv]
        t = Table(rows, colWidths=[2 * inch, 5 * inch])
        t.setStyle(TableStyle([
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, LIGHT_BG]),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(t)

        investors = data.get("key_investors", [])
        if investors:
            story += [Spacer(1, 8), Paragraph("<b>Key Investors:</b>", self.s["body"])]
            story.append(Paragraph("  •  ".join(investors[:10]), self.s["body"]))

        story.append(Paragraph(data.get("summary", ""), self.s["body"]))
        return story

    def _section_ip(self, data: dict) -> list:
        story = [PageBreak(), Paragraph("Technology & IP", self.s["h1"]),
                 HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=6)]
        story.append(Paragraph(f"<b>Patent Count:</b> {data.get('patent_count', 0)}", self.s["body"]))
        story.append(Paragraph(f"<b>Moat Assessment:</b> {data.get('moat_assessment', '')}", self.s["body"]))

        patents = data.get("patents", [])
        if patents:
            rows = [["Patent Title", "Number", "Filed"]]
            for p in patents[:8]:
                rows.append([p.get("title", "")[:60], p.get("number", ""), p.get("filed", "")])
            t = Table(rows, colWidths=[4 * inch, 1.5 * inch, 1.5 * inch])
            t.setStyle(self._base_table_style())
            story += [Spacer(1, 6), t]

        story.append(Paragraph(data.get("summary", ""), self.s["body"]))
        return story

    def _section_legal(self, data: dict) -> list:
        story = [PageBreak(), Paragraph("Legal Risk", self.s["h1"]),
                 HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=6)]

        risk = data.get("risk_level", "MEDIUM")
        risk_color = RISK_COLORS.get(risk, AMBER)
        badge = [[Paragraph(f"<b>Risk Level: {risk}</b>", ParagraphStyle("rb",
            fontName="Helvetica-Bold", fontSize=11, textColor=WHITE))]]
        bt = Table(badge, colWidths=[2 * inch])
        bt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), risk_color),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ]))
        story += [bt, Spacer(1, 8)]

        lawsuits = data.get("lawsuits", [])
        if lawsuits:
            rows = [["Case", "Type", "Status", "Year"]]
            for s in lawsuits[:8]:
                rows.append([s.get("case", "")[:50], s.get("type", ""), s.get("status", ""), str(s.get("year", ""))])
            t = Table(rows, colWidths=[3 * inch, 1.2 * inch, 1.2 * inch, 0.6 * inch])
            t.setStyle(self._base_table_style())
            story += [t, Spacer(1, 8)]

        story.append(Paragraph(data.get("summary", ""), self.s["body"]))
        return story

    def _section_news(self, data: dict) -> list:
        story = [PageBreak(), Paragraph("News & Sentiment", self.s["h1"]),
                 HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=6)]

        sentiment = data.get("overall_sentiment", "NEUTRAL")
        story.append(Paragraph(f"<b>Overall Sentiment:</b> {sentiment}", self.s["body"]))

        headlines = data.get("recent_headlines", [])
        if headlines:
            rows = [["Headline", "Date", "Source", "Sentiment"]]
            for h in headlines[:10]:
                rows.append([h.get("title", "")[:60], h.get("date", ""),
                              h.get("source", "")[:20], h.get("sentiment", "")])
            t = Table(rows, colWidths=[3.5 * inch, 0.8 * inch, 1.2 * inch, 1.5 * inch])
            t.setStyle(self._base_table_style())
            story += [Spacer(1, 6), t]

        story.append(Paragraph(data.get("summary", ""), self.s["body"]))
        return story

    def _flags_and_recommendation(self, sections: dict) -> list:
        story = [PageBreak(), Paragraph("Flags & Recommendation", self.s["h1"]),
                 HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=8)]

        red = sections.get("red_flags", [])
        green = sections.get("green_flags", [])
        rec = sections.get("investment_recommendation", {})

        col1, col2 = [], []
        col1.append(Paragraph("🟢 Green Flags", self.s["h2"]))
        for g in green:
            col1.append(Paragraph(f"• {g}", self.s["bullet"]))
        col2.append(Paragraph("🔴 Red Flags", self.s["h2"]))
        for r in red:
            col2.append(Paragraph(f"• {r}", self.s["bullet"]))

        flag_table = Table([[col1, col2]], colWidths=[3.5 * inch, 3.5 * inch])
        flag_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(flag_table)
        story.append(Spacer(1, 12))

        if rec:
            story.append(Paragraph("Investment Recommendation", self.s["h2"]))
            story.append(Paragraph(rec.get("verdict", ""), self.s["body"]))
            nxt = rec.get("suggested_due_diligence_next_steps", [])
            qs = rec.get("key_questions_for_founders", [])
            if nxt:
                story.append(Paragraph("<b>Next Steps:</b>", self.s["body"]))
                for n in nxt:
                    story.append(Paragraph(f"• {n}", self.s["bullet"]))
            if qs:
                story.append(Spacer(1, 6))
                story.append(Paragraph("<b>Key Questions for Founders:</b>", self.s["body"]))
                for q in qs:
                    story.append(Paragraph(f"• {q}", self.s["bullet"]))
        return story

    def _sources_appendix(self, sources: list[dict]) -> list:
        story = [PageBreak(), Paragraph("Sources & References", self.s["h1"]),
                 HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=8)]

        grouped: dict[str, list] = {}
        for s in sources:
            grouped.setdefault(s.get("type", "other"), []).append(s)

        for stype, items in grouped.items():
            story.append(Paragraph(stype.upper(), self.s["h2"]))
            for i, item in enumerate(items[:15], 1):
                story.append(Paragraph(
                    f"{i}. {item.get('title','')[:80]}",
                    self.s["small"],
                ))
                story.append(Paragraph(item.get("url", ""), self.s["source_url"]))
            story.append(Spacer(1, 6))
        return story

    # ── Shared table style ─────────────────────────────────────────────────────

    def _strengths_concerns(self, data: dict) -> list:
        story = []
        strengths = data.get("strengths", [])
        concerns = data.get("concerns", [])
        if strengths or concerns:
            story.append(Spacer(1, 8))
            col1 = [Paragraph("Strengths", self.s["h2"])] + [Paragraph(f"• {s}", self.s["bullet"]) for s in strengths]
            col2 = [Paragraph("Concerns", self.s["h2"])] + [Paragraph(f"• {c}", self.s["bullet"]) for c in concerns]
            t = Table([[col1, col2]], colWidths=[3.5 * inch, 3.5 * inch])
            t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
            story.append(t)
        return story

    def _base_table_style(self) -> TableStyle:
        return TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("WORDWRAP", (0, 0), (-1, -1), True),
        ])

    # ── Page decoration ────────────────────────────────────────────────────────

    @staticmethod
    def _page_header_footer(canvas, doc):
        canvas.saveState()
        w, h = letter

        # Header bar
        canvas.setFillColor(NAVY)
        canvas.rect(0, h - 0.45 * inch, w, 0.45 * inch, fill=1, stroke=0)
        canvas.setFillColor(WHITE)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawString(0.75 * inch, h - 0.28 * inch, "CONFIDENTIAL — AI Due Diligence Engine")
        canvas.drawRightString(w - 0.75 * inch, h - 0.28 * inch, datetime.utcnow().strftime("%Y-%m-%d"))

        # Footer
        canvas.setFillColor(MID_GREY)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(0.75 * inch, 0.35 * inch,
            "This report is AI-generated and for informational purposes only. Not investment advice.")
        canvas.drawRightString(w - 0.75 * inch, 0.35 * inch, f"Page {doc.page}")
        canvas.restoreState()