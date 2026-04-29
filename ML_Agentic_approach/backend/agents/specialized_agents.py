"""
Specialist agents — one per evaluation dimension.

Each agent is an expert judge for a specific aspect of the academic report.
Together they form the SRLM multi-agent judging panel.
"""
from __future__ import annotations

import json
from typing import Dict, List, Optional

from .base_agent import BaseAgent


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


# ── Factory ───────────────────────────────────────────────────────────────────

def build_all_agents(ollama_client) -> List[BaseAgent]:
    """Instantiate the full panel of specialist agents."""
    return [
        AbstractAgent(ollama_client),
        MethodologyAgent(ollama_client),
        ResultsAgent(ollama_client),
        CitationAgent(ollama_client),
        DocumentStructureAgent(ollama_client),
        ContentDepthAgent(ollama_client),
    ]
