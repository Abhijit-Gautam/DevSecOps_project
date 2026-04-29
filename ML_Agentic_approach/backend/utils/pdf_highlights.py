"""
Helpers for turning agent annotations into PDF overlay metadata.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


def build_pdf_annotations(
    agent_evaluations: List[Dict[str, Any]],
    report_text: str,
    pdf_pages: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    pages = pdf_pages or [report_text]
    annotations: List[Dict[str, Any]] = []
    for ev in agent_evaluations:
        agent_name = ev.get("agent", "Unknown")
        for raw in ev.get("highlight_annotations", []) or []:
            item = _normalise_annotation(raw, agent_name, pages)
            if item:
                annotations.append(item)
    return annotations


def extract_pdf_page_texts(data: bytes, filename: str) -> List[str]:
    if not filename.lower().endswith(".pdf"):
        return []
    try:
        from pypdf import PdfReader
        import io

        reader = PdfReader(io.BytesIO(data))
        return [page.extract_text() or "" for page in reader.pages]
    except Exception:
        return []


def _normalise_annotation(
    raw: Dict[str, Any],
    agent_name: str,
    pages: List[str],
) -> Optional[Dict[str, Any]]:
    text_span = str(raw.get("text_span") or raw.get("exact_text_span") or "").strip()
    if not text_span:
        return None

    page_number = _resolve_page_number(text_span, raw.get("page_number"), pages)
    issue_type = str(raw.get("issue_type") or "warning")
    severity = str(raw.get("severity") or "medium").lower()
    score_impact = _safe_float(raw.get("score_impact"), 0.0)
    color = _color_for(issue_type, severity, score_impact)
    rect = _approximate_rect(text_span, pages[page_number - 1] if pages else "")

    return {
        "text_span": text_span,
        "page_number": page_number,
        "issue_type": issue_type,
        "severity": severity,
        "explanation": str(raw.get("explanation") or ""),
        "suggestion": str(raw.get("suggestion") or ""),
        "score_impact": score_impact,
        "agent": raw.get("agent") or agent_name,
        "color": color,
        "rect": rect,
    }


def _resolve_page_number(text_span: str, supplied_page: Any, pages: List[str]) -> int:
    try:
        page = int(supplied_page)
        if 1 <= page <= max(1, len(pages)):
            return page
    except (TypeError, ValueError):
        pass

    needle = _compact(text_span)
    if needle:
        for idx, page_text in enumerate(pages, start=1):
            if needle in _compact(page_text):
                return idx
    return 1


def _approximate_rect(text_span: str, page_text: str) -> Dict[str, float]:
    lines = [line.strip() for line in page_text.splitlines() if line.strip()]
    if not lines:
        return {"x": 8, "y": 8, "width": 84, "height": 5}

    needle = _compact(text_span)
    line_idx = 0
    for idx, line in enumerate(lines):
        if needle and needle[: min(40, len(needle))] in _compact(line):
            line_idx = idx
            break

    y = 5 + (line_idx / max(1, len(lines))) * 88
    return {"x": 7, "y": min(92, y), "width": 86, "height": 4.5}


def _color_for(issue_type: str, severity: str, score_impact: float) -> str:
    issue = issue_type.lower()
    if "good" in issue or score_impact > 0:
        return "green"
    if severity == "high" or "bad" in issue or score_impact < -3:
        return "red"
    return "yellow"


def _compact(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
