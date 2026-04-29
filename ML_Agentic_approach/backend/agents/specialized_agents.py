"""
Specialist agents — one per evaluation dimension.

Each agent is an expert judge for a specific aspect of the academic report.
Together they form the SRLM multi-agent judging panel.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .base_agent import BaseAgent


DIAGRAM_SYSTEM_PROMPT = """
You are DiagramAgent, a strict academic report diagram evaluator.
Evaluate only visual diagrams, figures, charts, workflows, architecture drawings,
and their nearby captions/context. Do not infer quality from writing alone.

Preset evaluation parameters:
- relevance_to_report: 25%
- technical_correctness: 25%
- visual_clarity: 20%
- labels_and_legends: 15%
- usefulness_to_reader: 15%

Return only valid JSON with exactly these keys:
{
  "score": float from 0 to 10,
  "pass/fail": "pass" or "fail",
  "issues": list of strings,
  "explanation": "concise evidence-based explanation",
  "suggestions": list of strings,
  "highlight_annotations": [
    {
      "text_span": "exact nearby caption or text span",
      "page_number": integer,
      "issue_type": "diagram_issue"|"warning"|"good_sentence",
      "severity": "low"|"medium"|"high",
      "explanation": "why marked",
      "suggestion": "actionable suggestion",
      "score_impact": number from -10 to +10
    }
  ]
}
Pass requires score >= 6.0 and no severe correctness issue.
"""


def _verdict_from_score(score: Any) -> str:
    try:
        value = float(score)
    except (TypeError, ValueError):
        return "Needs Improvement"
    if value >= 8:
        return "Excellent"
    if value >= 6:
        return "Good"
    return "Needs Improvement"


def _normalise_compact_result(raw: Optional[Dict], agent_name: str) -> Dict:
    raw = raw or {}
    score = raw.get("score", 0)
    pass_fail = raw.get("pass_fail") or raw.get("pass/fail")
    if pass_fail not in {"pass", "fail"}:
        try:
            pass_fail = "pass" if float(score) >= 6.0 else "fail"
        except (TypeError, ValueError):
            pass_fail = "fail"
    issues = raw.get("issues")
    suggestions = raw.get("suggestions")
    explanation = raw.get("explanation") or raw.get("reasoning") or ""
    annotations = raw.get("highlight_annotations")
    if isinstance(annotations, list):
        annotations = [
            {**item, "agent": item.get("agent") or agent_name}
            for item in annotations
            if isinstance(item, dict) and item.get("text_span")
        ]
    return {
        "agent": agent_name,
        "round": 1,
        "score": score,
        "max_score": 10,
        "pass_fail": pass_fail,
        "pass/fail": pass_fail,
        "verdict": _verdict_from_score(score),
        "issues": issues if isinstance(issues, list) else [],
        "explanation": explanation,
        "reasoning": explanation,
        "suggestions": suggestions if isinstance(suggestions, list) else [],
        "evidence": raw.get("evidence", []) if isinstance(raw.get("evidence"), list) else [],
        "strengths": raw.get("strengths", []) if isinstance(raw.get("strengths"), list) else [],
        "weaknesses": issues if isinstance(issues, list) else [],
        "recommendations": suggestions if isinstance(suggestions, list) else [],
        "highlight_annotations": annotations if isinstance(annotations, list) else [],
    }


class AbstractAgent(BaseAgent):
    name = "AbstractAgent"
    role = "Abstract & Executive Summary Evaluator"
    focus_areas = [
        "clarity of research question",
        "conciseness",
        "key contributions stated",
        "methodology overview present",
        "results summary present",
    ]

    def _build_evaluation_prompt(self, report_text: str, parsed_data: Dict, context: Dict) -> str:
        abstract_score = next(
            (s for s in parsed_data.get("sections", []) if s["name"] == "abstract"), {}
        )
        return f"""
Evaluate the ABSTRACT section of this academic report.

PARSED METADATA: {json.dumps(abstract_score, indent=2)}

REPORT TEXT (first 1500 chars):
{report_text[:1500]}

Assess:
1. Does the abstract clearly state the research problem?
2. Is the methodology briefly described?
3. Are the key results/contributions mentioned?
4. Is it concise and self-contained?
5. What is the writing quality?

Return JSON:
{{
  "verdict": "Excellent|Good|Needs Improvement",
  "score": float (0-10),
  "max_score": 10,
  "reasoning": "detailed explanation",
  "evidence": ["quote1 from report", "quote2"],
  "strengths": ["point1", "point2"],
  "weaknesses": ["point1"],
  "recommendations": ["action1", "action2"]
}}
"""


class MethodologyAgent(BaseAgent):
    name = "MethodologyAgent"
    role = "Research Methodology Evaluator"
    focus_areas = [
        "research design validity",
        "experimental setup",
        "reproducibility",
        "dataset description",
        "evaluation metrics",
    ]

    def _build_evaluation_prompt(self, report_text: str, parsed_data: Dict, context: Dict) -> str:
        meth_score = next(
            (s for s in parsed_data.get("sections", []) if s["name"] == "methodology"), {}
        )
        return f"""
Evaluate the METHODOLOGY section of this academic report.

PARSED METADATA: {json.dumps(meth_score, indent=2)}

REPORT TEXT:
{report_text[:3000]}

Assess:
1. Is the research design clearly described and appropriate?
2. Are datasets/materials properly described?
3. Is the methodology reproducible?
4. Are baselines and comparisons appropriate?
5. Are evaluation metrics justified?

Return JSON:
{{
  "verdict": "Excellent|Good|Needs Improvement",
  "score": float (0-10),
  "max_score": 10,
  "reasoning": "detailed explanation",
  "evidence": ["specific text evidence"],
  "reproducibility_score": float (0-10),
  "strengths": [],
  "weaknesses": [],
  "recommendations": []
}}
"""


class ResultsAgent(BaseAgent):
    name = "ResultsAgent"
    role = "Results & Analysis Evaluator"
    focus_areas = [
        "statistical significance",
        "result presentation",
        "comparison with state-of-art",
        "visual aids quality",
        "interpretation accuracy",
    ]

    def _build_evaluation_prompt(self, report_text: str, parsed_data: Dict, context: Dict) -> str:
        results_score = next(
            (s for s in parsed_data.get("sections", []) if s["name"] == "results"), {}
        )
        return f"""
Evaluate the RESULTS & ANALYSIS section of this academic report.

PARSED METADATA: {json.dumps(results_score, indent=2)}

REPORT TEXT:
{report_text[:3000]}

Assess:
1. Are results clearly presented with appropriate metrics?
2. Is statistical significance addressed?
3. Are results compared to baselines or prior work?
4. Are figures/tables informative and well-labeled?
5. Is the analysis insightful rather than just descriptive?

Return JSON:
{{
  "verdict": "Excellent|Good|Needs Improvement",
  "score": float (0-10),
  "max_score": 10,
  "reasoning": "detailed explanation",
  "evidence": ["specific text evidence"],
  "statistical_rigor": float (0-10),
  "strengths": [],
  "weaknesses": [],
  "recommendations": []
}}
"""


class CitationAgent(BaseAgent):
    name = "CitationAgent"
    role = "Citations & Literature Review Evaluator"
    focus_areas = [
        "citation completeness",
        "relevance of cited works",
        "proper citation format",
        "coverage of seminal papers",
        "recency of references",
    ]

    def _build_evaluation_prompt(self, report_text: str, parsed_data: Dict, context: Dict) -> str:
        ref_count = parsed_data.get("reference_count", "unknown")
        lit_count = parsed_data.get("literature_review_count", "unknown")
        return f"""
Evaluate the CITATIONS & LITERATURE REVIEW of this academic report.

Reference count detected: {ref_count}
Literature review reference count: {lit_count}
Document quality citations score: {parsed_data.get("document_quality", {}).get("citations")}

REPORT TEXT (last 2000 chars for references):
{report_text[-2000:]}

FULL REPORT (for context):
{report_text[:2000]}

Assess:
1. Is the literature review comprehensive and relevant?
2. Are seminal/foundational works cited?
3. Is the citation format consistent?
4. Are references recent enough for the field?
5. Do citations support claims effectively?

Return JSON:
{{
  "verdict": "Excellent|Good|Needs Improvement",
  "score": float (0-10),
  "max_score": 10,
  "reasoning": "detailed explanation",
  "evidence": ["specific text evidence"],
  "estimated_reference_count": int,
  "citation_format_consistent": bool,
  "recency_assessment": "str",
  "strengths": [],
  "weaknesses": [],
  "recommendations": []
}}
"""


class DocumentStructureAgent(BaseAgent):
    name = "DocumentStructureAgent"
    role = "Document Quality & Structure Evaluator"
    focus_areas = [
        "section organization",
        "formatting consistency",
        "figure and table quality",
        "page layout",
        "overall presentation",
    ]

    def _build_evaluation_prompt(self, report_text: str, parsed_data: Dict, context: Dict) -> str:
        dq = parsed_data.get("document_quality", {})
        structural_flags = {
            "has_abstract": parsed_data.get("has_abstract"),
            "has_methodology": parsed_data.get("has_methodology"),
            "has_results": parsed_data.get("has_results"),
            "has_conclusion": parsed_data.get("has_conclusion"),
        }
        return f"""
Evaluate the DOCUMENT QUALITY & STRUCTURE of this academic report.

Detected structure flags: {json.dumps(structural_flags, indent=2)}
Document quality sub-scores: {json.dumps(dq, indent=2)}

REPORT TEXT:
{report_text[:2500]}

Assess:
1. Is the document logically structured (abstract → intro → methodology → results → conclusion)?
2. Is formatting consistent throughout?
3. Are all required sections present and well-developed?
4. Is the document professionally presented?
5. Are figures, tables, and appendices properly integrated?

Return JSON:
{{
  "verdict": "Excellent|Good|Needs Improvement",
  "score": float (0-10),
  "max_score": 10,
  "reasoning": "detailed explanation",
  "evidence": ["specific observations"],
  "missing_sections": ["list of missing sections"],
  "formatting_issues": ["list of formatting problems"],
  "strengths": [],
  "weaknesses": [],
  "recommendations": []
}}
"""


class ContentDepthAgent(BaseAgent):
    name = "ContentDepthAgent"
    role = "Content Depth & Academic Rigor Evaluator"
    focus_areas = [
        "intellectual contribution",
        "depth of analysis",
        "critical thinking",
        "novelty",
        "academic writing quality",
    ]

    def _build_evaluation_prompt(self, report_text: str, parsed_data: Dict, context: Dict) -> str:
        domain = parsed_data.get("domain", "unknown")
        total_score = parsed_data.get("total_score")
        max_score = parsed_data.get("max_score")
        return f"""
Evaluate the CONTENT DEPTH & ACADEMIC RIGOR of this {domain} domain report.

Overall rubric score: {total_score}/{max_score}
Word count: {parsed_data.get("word_count", "unknown")}

FULL REPORT TEXT:
{report_text[:4000]}

Assess:
1. Does the report demonstrate deep understanding of the domain?
2. Is there original intellectual contribution or just summarisation?
3. Is the critical analysis sound and well-argued?
4. Is the writing style appropriately academic?
5. Does the conclusion synthesise findings meaningfully?

Return JSON:
{{
  "verdict": "Excellent|Good|Needs Improvement",
  "score": float (0-10),
  "max_score": 10,
  "reasoning": "detailed explanation",
  "evidence": ["specific text passages"],
  "novelty_score": float (0-10),
  "critical_thinking_score": float (0-10),
  "writing_quality_score": float (0-10),
  "strengths": [],
  "weaknesses": [],
  "recommendations": []
}}
"""


class DiagramAgent(BaseAgent):
    name = "DiagramAgent"
    role = "Diagram, Figure & Visual Evidence Evaluator"
    focus_areas = [
        "diagram relevance",
        "technical correctness",
        "visual clarity",
        "labels and legends",
        "reader usefulness",
    ]

    def __init__(self, ollama_client, groq_vlm_client=None):
        super().__init__(ollama_client)
        self.groq_vlm = groq_vlm_client

    def evaluate(
        self,
        report_text: str,
        parsed_data: Optional[Dict] = None,
        context: Optional[Dict] = None,
    ) -> Dict:
        context = context or {}
        parsed_data = parsed_data or {}
        images = context.get("diagram_images") or parsed_data.get("diagram_images") or []
        if not images:
            return _normalise_compact_result(
                {
                    "score": 0,
                    "pass/fail": "fail",
                    "issues": ["No diagram images were available for VLM evaluation."],
                    "explanation": "DiagramAgent requires extracted diagram or figure images to judge visual relevance, correctness, clarity, labels, and usefulness.",
                    "suggestions": ["Upload a PDF or DOCX containing extractable figures, diagrams, or charts."],
                },
                self.name,
            )

        prompt = self._build_evaluation_prompt(report_text, parsed_data, context)
        if self.groq_vlm and hasattr(self.groq_vlm, "generate_json_with_images"):
            raw = self.groq_vlm.generate_json_with_images(
                prompt=prompt,
                image_urls=images,
                system=DIAGRAM_SYSTEM_PROMPT,
                temperature=0.1,
                max_tokens=900,
            )
        else:
            raw = self._fallback_evaluation(report_text, parsed_data)
        return _normalise_compact_result(raw, self.name)

    def _system_prompt(self) -> str:
        return DIAGRAM_SYSTEM_PROMPT

    def _build_evaluation_prompt(self, report_text: str, parsed_data: Dict, context: Dict) -> str:
        return f"""
Evaluate the report diagrams using the provided image input.

Report context:
{report_text[:2000]}

Parsed document quality:
{json.dumps(parsed_data.get("document_quality", {}), indent=2)}

Use the preset evaluation parameters from the system prompt. Return only the required JSON.
"""

    def _fallback_evaluation(self, report_text: str, parsed_data: Optional[Dict]) -> Dict:
        return {
            "score": 0,
            "pass_fail": "fail",
            "pass/fail": "fail",
            "issues": ["Groq VLM client was unavailable or did not return valid JSON."],
            "explanation": "Visual diagram assessment could not be completed.",
            "suggestions": ["Configure GROQ_API_KEY and retry with image-bearing report input."],
        }


class FormatterAgent(BaseAgent):
    name = "FormatterAgent"
    role = "Formatting & Layout Evaluator"
    focus_areas = [
        "font consistency",
        "bold headings",
        "spacing",
        "margins",
        "alignment",
        "formatting consistency",
    ]

    def _system_prompt(self) -> str:
        return """
You are FormatterAgent, a strict academic report formatting evaluator.
Evaluate formatting only: font consistency, bold/clear headings, spacing, margins,
alignment, indentation, and consistency across the document.

Return only valid JSON with exactly these keys:
{
  "score": float from 0 to 10,
  "pass/fail": "pass" or "fail",
  "issues": list of strings,
  "explanation": "concise evidence-based explanation",
  "suggestions": list of strings,
  "highlight_annotations": [
    {
      "text_span": "exact text span from the report",
      "page_number": integer,
      "issue_type": "formatting_issue"|"warning"|"good_sentence",
      "severity": "low"|"medium"|"high",
      "explanation": "why marked",
      "suggestion": "actionable suggestion",
      "score_impact": number from -10 to +10
    }
  ]
}
Pass requires score >= 6.0.
"""

    def evaluate(
        self,
        report_text: str,
        parsed_data: Optional[Dict] = None,
        context: Optional[Dict] = None,
    ) -> Dict:
        raw = self.ollama.generate_json(
            prompt=self._build_evaluation_prompt(report_text, parsed_data or {}, context or {}),
            system=self._system_prompt(),
            temperature=0.2,
        )
        if not raw:
            raw = self._fallback_evaluation(report_text, parsed_data)
        return _normalise_compact_result(raw, self.name)

    def _build_evaluation_prompt(self, report_text: str, parsed_data: Dict, context: Dict) -> str:
        dq = parsed_data.get("document_quality", {})
        return f"""
Evaluate the report formatting.

Document quality metadata:
{json.dumps(dq, indent=2)}

REPORT TEXT:
{report_text[:3000]}

Check font, bold headings, spacing, margins, alignment, and consistency.
Return only the required JSON.
"""

    def _fallback_evaluation(self, report_text: str, parsed_data: Optional[Dict]) -> Dict:
        return {
            "score": 0,
            "pass_fail": "fail",
            "pass/fail": "fail",
            "issues": ["Formatting evaluation model did not return valid JSON."],
            "explanation": "Unable to evaluate formatting reliably.",
            "suggestions": ["Retry once the text LLM service is available."],
        }


# ── Factory ───────────────────────────────────────────────────────────────────

def build_all_agents(ollama_client, groq_vlm_client=None) -> List[BaseAgent]:
    """Instantiate the full panel of specialist agents."""
    return [
        AbstractAgent(ollama_client),
        MethodologyAgent(ollama_client),
        ResultsAgent(ollama_client),
        CitationAgent(ollama_client),
        DocumentStructureAgent(ollama_client),
        ContentDepthAgent(ollama_client),
        DiagramAgent(ollama_client, groq_vlm_client),
        FormatterAgent(ollama_client),
    ]
