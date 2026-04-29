"""
Structured parser for academic evaluation reports.
Extracts: domain, section scores, feedback, document quality metrics, total score.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class SectionScore:
    name: str
    score: Optional[float] = None
    max_score: Optional[float] = None
    feedback: str = ""


@dataclass
class DocumentQuality:
    section_structure: Optional[float] = None
    font_consistency: Optional[float] = None
    line_spacing: Optional[float] = None
    figures_tables: Optional[float] = None
    blank_pages: Optional[float] = None
    citations: Optional[float] = None
    page_numbers: Optional[float] = None
    total: Optional[float] = None
    max_total: float = 7.0


@dataclass
class ParsedReport:
    domain: Optional[str] = None
    total_score: Optional[float] = None
    max_score: Optional[float] = None
    sections: List[SectionScore] = field(default_factory=list)
    literature_review_count: Optional[int] = None
    document_quality: DocumentQuality = field(default_factory=DocumentQuality)
    raw_text: str = ""
    word_count: int = 0
    has_abstract: bool = False
    has_methodology: bool = False
    has_results: bool = False
    has_conclusion: bool = False
    reference_count: Optional[int] = None


# ── Regex patterns ────────────────────────────────────────────────────────────

_DOMAIN_PATTERNS = [
    r"Domain[:\s]+([A-Za-z\s/]+?)(?:\n|$)",
    r"Field[:\s]+([A-Za-z\s/]+?)(?:\n|$)",
    r"Topic[:\s]+([A-Za-z\s/]+?)(?:\n|$)",
]

_TOTAL_SCORE_PATTERNS = [
    r"Total[:\s]+(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)",
    r"Score[:\s]+(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)",
    r"Final[:\s]+(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)",
    r"Overall[:\s]+(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)",
]

_SECTION_PATTERNS = {
    "abstract": r"Abstract[:\s]+(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)",
    "introduction": r"Introduction[:\s]+(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)",
    "methodology": r"Method(?:ology)?[:\s]+(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)",
    "results": r"Results?[:\s]+(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)",
    "conclusion": r"Conclusions?[:\s]+(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)",
    "literature_review": r"Literature\s+Review[:\s]+(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)",
    "discussion": r"Discussion[:\s]+(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)",
}

_DOC_QUALITY_PATTERNS = {
    "section_structure": r"Section\s+structure[:\s]+(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)",
    "font_consistency": r"Font\s+consistency[:\s]+(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)",
    "line_spacing": r"Line\s+spacing[:\s]+(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)",
    "figures_tables": r"Figures?(?:/tables?)?[:\s]+(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)",
    "blank_pages": r"Blank\s+pages?[:\s]+(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)",
    "citations": r"Citations?[:\s]+(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)",
    "page_numbers": r"Page\s+numbers?[:\s]+(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)",
}

_REFERENCE_COUNT_PATTERN = r"(\d+)\s+(?:references?|sources?)\s+(?:verified|found|checked)"
_LIT_REVIEW_COUNT_PATTERN = r"Literature\s+review.*?(\d+)\s+(?:references?|sources?)"


def _find_first(patterns: List[str], text: str) -> Optional[re.Match]:
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m
    return None


def _extract_feedback_for_section(section_name: str, text: str) -> str:
    """Heuristic: grab a few lines after the section heading as feedback."""
    pattern = rf"(?:{section_name})[:\s]+\d[^\n]*\n((?:[^\n]+\n?){{0,5}})"
    m = re.search(pattern, text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return ""


def parse_report(text: str) -> ParsedReport:
    """Parse a raw report text into a structured ParsedReport."""
    report = ParsedReport(raw_text=text, word_count=len(text.split()))

    # ── Domain ────────────────────────────────────────────────────────────
    m = _find_first(_DOMAIN_PATTERNS, text)
    if m:
        report.domain = m.group(1).strip().title()

    # ── Total score ───────────────────────────────────────────────────────
    m = _find_first(_TOTAL_SCORE_PATTERNS, text)
    if m:
        report.total_score = float(m.group(1))
        report.max_score = float(m.group(2))

    # ── Section scores ────────────────────────────────────────────────────
    for sec_name, pattern in _SECTION_PATTERNS.items():
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            feedback = _extract_feedback_for_section(sec_name, text)
            report.sections.append(
                SectionScore(
                    name=sec_name,
                    score=float(m.group(1)),
                    max_score=float(m.group(2)),
                    feedback=feedback,
                )
            )

    # ── Document quality ──────────────────────────────────────────────────
    dq = report.document_quality
    for attr, pattern in _DOC_QUALITY_PATTERNS.items():
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            setattr(dq, attr, float(m.group(1)))
    # Sum document quality sub-scores
    dq_vals = [
        v for v in [
            dq.section_structure, dq.font_consistency, dq.line_spacing,
            dq.figures_tables, dq.blank_pages, dq.citations, dq.page_numbers,
        ]
        if v is not None
    ]
    if dq_vals:
        dq.total = sum(dq_vals)

    # ── Literature review reference count ─────────────────────────────────
    m = re.search(_REFERENCE_COUNT_PATTERN, text, re.IGNORECASE)
    if m:
        report.reference_count = int(m.group(1))
    m = re.search(_LIT_REVIEW_COUNT_PATTERN, text, re.IGNORECASE)
    if m:
        report.literature_review_count = int(m.group(1))

    # ── Structural presence flags ─────────────────────────────────────────
    report.has_abstract = bool(re.search(r"\babstract\b", text, re.IGNORECASE))
    report.has_methodology = bool(re.search(r"\b(?:method(?:ology)?)\b", text, re.IGNORECASE))
    report.has_results = bool(re.search(r"\bresults?\b", text, re.IGNORECASE))
    report.has_conclusion = bool(re.search(r"\bconclusions?\b", text, re.IGNORECASE))

    return report


def parsed_report_to_dict(pr: ParsedReport) -> Dict:
    return {
        "domain": pr.domain,
        "total_score": pr.total_score,
        "max_score": pr.max_score,
        "word_count": pr.word_count,
        "sections": [
            {
                "name": s.name,
                "score": s.score,
                "max_score": s.max_score,
                "feedback": s.feedback,
            }
            for s in pr.sections
        ],
        "document_quality": {
            "section_structure": pr.document_quality.section_structure,
            "font_consistency": pr.document_quality.font_consistency,
            "line_spacing": pr.document_quality.line_spacing,
            "figures_tables": pr.document_quality.figures_tables,
            "blank_pages": pr.document_quality.blank_pages,
            "citations": pr.document_quality.citations,
            "page_numbers": pr.document_quality.page_numbers,
            "total": pr.document_quality.total,
            "max_total": pr.document_quality.max_total,
        },
        "literature_review_count": pr.literature_review_count,
        "reference_count": pr.reference_count,
        "has_abstract": pr.has_abstract,
        "has_methodology": pr.has_methodology,
        "has_results": pr.has_results,
        "has_conclusion": pr.has_conclusion,
    }
