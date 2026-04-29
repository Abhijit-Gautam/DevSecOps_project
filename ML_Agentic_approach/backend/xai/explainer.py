"""
XAI Explainer — Explainable AI module.

Generates human-readable reasoning for each evaluation dimension, explaining:
  - WHY the model assigned a specific verdict
  - WHICH text segments drove the decision
  - WHAT specific improvements are needed

Inspired by:
  - LIME: Ribeiro et al. (2016) "Why Should I Trust You?"
  - SHAP: Lundberg & Lee (2017) "A Unified Approach to Interpreting Model Predictions"
  - Attention Rollout: Abnar & Zuidema (2020)
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


EXPLAINER_SYSTEM = """
You are an expert academic evaluator providing transparent, evidence-based explanations
of report quality assessments. Your explanations must:
1. Reference SPECIFIC text from the report as evidence
2. Link each piece of evidence to an evaluation criterion
3. Be actionable — tell the student exactly what to improve
4. Be calibrated — explain why the evidence supports the verdict

Always return valid JSON as instructed.
"""


class XAIExplainer:
    """
    Produces per-dimension explanations that link report text to verdicts.

    Methods:
        explain() — generate full XAI output for a report
        explain_section() — explain a single section in isolation
    """

    def __init__(self, roberta_model, ollama_client):
        self.roberta = roberta_model
        self.ollama = ollama_client

    # ── Main entry point ─────────────────────────────────────────────────────

    def explain(
        self,
        report_text: str,
        roberta_result: Dict,
        unified_verdict: Dict,
        highlight_data: Optional[Dict],
        parsed_data: Optional[Dict],
    ) -> Dict[str, Any]:
        """
        Generate comprehensive XAI output.

        Returns:
            {
                "model_explanation": {...},
                "section_explanations": {section: {...}},
                "highlighted_evidence": [...],
                "decision_factors": [...],
                "counterfactuals": [...],
                "improvement_roadmap": [...]
            }
        """
        parsed_data = parsed_data or {}
        sections = parsed_data.get("sections", [])

        # ── 1. Model explanation (why did RoBERTa assign this label?) ──────
        model_exp = self._explain_model_prediction(
            report_text, roberta_result, highlight_data
        )

        # ── 2. Per-section explanations ────────────────────────────────────
        section_explanations = {}
        for sec in sections:
            sec_name = sec.get("name", "unknown")
            try:
                section_explanations[sec_name] = self._explain_section(
                    sec_name, sec, report_text, parsed_data
                )
            except Exception as e:
                logger.warning(f"Section explanation failed for {sec_name}: {e}")
                section_explanations[sec_name] = {"error": str(e)}

        # ── 3. Decision factors (what mattered most) ───────────────────────
        decision_factors = self._extract_decision_factors(
            report_text, roberta_result, unified_verdict, parsed_data
        )

        # ── 4. Counterfactual: what would change the verdict? ──────────────
        counterfactuals = self._generate_counterfactuals(
            report_text, unified_verdict, parsed_data
        )

        # ── 5. Evidence linking: map highlight spans to sections ───────────
        highlighted_evidence = self._map_highlights_to_sections(
            highlight_data, report_text, sections
        )

        # ── 6. Improvement roadmap ─────────────────────────────────────────
        improvement_roadmap = self._build_improvement_roadmap(
            unified_verdict, section_explanations, parsed_data
        )

        return {
            "model_explanation": model_exp,
            "section_explanations": section_explanations,
            "highlighted_evidence": highlighted_evidence,
            "decision_factors": decision_factors,
            "counterfactuals": counterfactuals,
            "improvement_roadmap": improvement_roadmap,
        }

    # ── Private helpers ──────────────────────────────────────────────────────

    def _explain_model_prediction(
        self,
        report_text: str,
        roberta_result: Dict,
        highlight_data: Optional[Dict],
    ) -> Dict:
        """Explain why the RoBERTa model gave its prediction."""
        label = roberta_result.get("predicted_label", "Unknown")
        confidence = roberta_result.get("confidence", 0)
        probs = roberta_result.get("probabilities", {})

        # Build top highlighted tokens from attention rollout
        top_tokens = []
        if highlight_data and highlight_data.get("highlighted_spans"):
            top_tokens = sorted(
                highlight_data["highlighted_spans"],
                key=lambda x: x["score"],
                reverse=True,
            )[:10]

        prompt = f"""
The RoBERTa sequence classifier (fine-tuned on {3} academic quality classes,
F1=0.981) predicted this report as: "{label}" with {confidence:.2%} confidence.

Class probabilities:
{json.dumps(probs, indent=2)}

Top attention-weighted tokens (most influential for prediction):
{json.dumps(top_tokens, indent=2)}

Report excerpt (first 1000 chars):
{report_text[:1000]}

Explain in plain English:
1. Why this label was assigned based on the report content
2. What patterns in the text drove the high/low confidence
3. What specific weaknesses the model likely detected
4. How the attention mechanism identified the key text regions

Return JSON:
{{
  "predicted_label": "{label}",
  "confidence": {confidence},
  "plain_english_reasoning": "2-3 sentence explanation",
  "key_signals": [
    {{"signal": "text or pattern", "impact": "positive|negative", "explanation": "why this matters"}}
  ],
  "confidence_explanation": "why confidence is high/low",
  "attention_summary": "what the attention highlights tell us"
}}
"""
        result = self.ollama.generate_json(
            prompt=prompt,
            system=EXPLAINER_SYSTEM,
            temperature=0.2,
        )
        if not result:
            result = {
                "predicted_label": label,
                "confidence": confidence,
                "plain_english_reasoning": f"The model classified this report as '{label}' with {confidence:.2%} confidence.",
                "key_signals": [],
                "confidence_explanation": "Model confidence reflects training data patterns.",
                "attention_summary": "Attention highlights most statistically significant tokens.",
            }
        return result

    def _explain_section(
        self,
        section_name: str,
        section_data: Dict,
        report_text: str,
        parsed_data: Dict,
    ) -> Dict:
        """Generate explanation for a single section's score."""
        score = section_data.get("score")
        max_score = section_data.get("max_score")
        feedback = section_data.get("feedback", "")

        prompt = f"""
Analyse why the {section_name.upper()} section received {score}/{max_score} in this report.

Original feedback given: "{feedback}"

Full report text (search for {section_name} related content):
{report_text[:3000]}

Provide a detailed explanation linking specific text to the score:
1. What text evidence justifies this score?
2. What criteria were met vs not met?
3. What exact changes would improve the score?

Return JSON:
{{
  "section": "{section_name}",
  "score": {score},
  "max_score": {max_score},
  "score_percentage": {round((score / max_score * 100) if max_score else 0, 1)},
  "verdict": "Excellent|Good|Needs Improvement",
  "reasoning": "detailed explanation of the score",
  "met_criteria": ["criterion1 with text evidence", "criterion2"],
  "unmet_criteria": ["criterion not met with explanation"],
  "key_text_evidence": [
    {{"text": "exact quote from report", "interpretation": "what this shows"}}
  ],
  "specific_improvements": ["actionable step 1", "actionable step 2"]
}}
"""
        result = self.ollama.generate_json(
            prompt=prompt,
            system=EXPLAINER_SYSTEM,
            temperature=0.2,
        )
        if not result:
            result = {
                "section": section_name,
                "score": score,
                "max_score": max_score,
                "verdict": "Unknown",
                "reasoning": feedback or "No explanation available.",
                "met_criteria": [],
                "unmet_criteria": [],
                "key_text_evidence": [],
                "specific_improvements": [],
            }
        return result

    def _extract_decision_factors(
        self,
        report_text: str,
        roberta_result: Dict,
        unified_verdict: Dict,
        parsed_data: Dict,
    ) -> List[Dict]:
        """Identify the top factors that most influenced the final verdict."""
        verdict = unified_verdict.get("final_verdict", "Unknown")
        total_score = parsed_data.get("total_score")
        max_score = parsed_data.get("max_score")

        prompt = f"""
The final verdict for this report is: "{verdict}"
Rubric score: {total_score}/{max_score}
RoBERTa prediction: {roberta_result.get("predicted_label")} ({roberta_result.get("confidence", 0):.2%})

Report (first 2000 chars):
{report_text[:2000]}

Identify the TOP 5 factors that most strongly influenced this verdict.
For each factor, explain the direction of influence (positive/negative) and provide evidence.

Return JSON array (exactly 5 items):
[
  {{
    "factor": "factor name",
    "direction": "positive|negative",
    "weight": float (0-1, relative importance),
    "evidence": "specific text or observation",
    "impact_on_verdict": "how this pushed toward the final verdict"
  }}
]
"""
        result = self.ollama.generate_json(prompt=prompt, temperature=0.2)
        if isinstance(result, list):
            return result
        return [
            {
                "factor": f"Total score: {total_score}/{max_score}",
                "direction": "positive" if (total_score or 0) / (max_score or 1) >= 0.7 else "negative",
                "weight": 1.0,
                "evidence": f"Overall rubric score of {total_score}/{max_score}",
                "impact_on_verdict": "Primary determinant of verdict",
            }
        ]

    def _generate_counterfactuals(
        self,
        report_text: str,
        unified_verdict: Dict,
        parsed_data: Dict,
    ) -> List[Dict]:
        """Generate counterfactual explanations: what would flip the verdict?"""
        verdict = unified_verdict.get("final_verdict", "Unknown")

        # Determine target verdicts for counterfactuals
        if verdict == "Needs Improvement":
            target = "Good"
        elif verdict == "Good":
            target = "Excellent"
        else:
            target = "Good"

        prompt = f"""
The current verdict is: "{verdict}"

For this report to receive a "{target}" verdict instead, what would need to change?
Be specific about minimal changes.

Report excerpt:
{report_text[:1500]}

Return JSON array of 3 counterfactual scenarios:
[
  {{
    "scenario": "brief description",
    "current_state": "what is currently true",
    "required_change": "specific minimal change needed",
    "affected_section": "which section/criterion changes",
    "difficulty": "Easy|Medium|Hard",
    "would_achieve": "{target}"
  }}
]
"""
        result = self.ollama.generate_json(prompt=prompt, temperature=0.3)
        if isinstance(result, list):
            return result
        return []

    def _map_highlights_to_sections(
        self,
        highlight_data: Optional[Dict],
        report_text: str,
        sections: List[Dict],
    ) -> List[Dict]:
        """
        Map attention-highlighted text spans to the sections they belong to.
        Creates structured evidence linking text → section → verdict impact.
        """
        if not highlight_data or not highlight_data.get("highlighted_spans"):
            return []

        top_spans = sorted(
            highlight_data["highlighted_spans"],
            key=lambda x: x["score"],
            reverse=True,
        )[:15]

        # Simple heuristic: assign spans to sections based on text proximity
        section_keywords = {
            "abstract": ["abstract", "overview", "summary"],
            "introduction": ["introduction", "background", "motivation"],
            "methodology": ["method", "approach", "algorithm", "experiment"],
            "results": ["result", "performance", "accuracy", "evaluation"],
            "conclusion": ["conclusion", "future work", "discuss"],
            "literature_review": ["cited", "reference", "related work"],
            "document_quality": ["formatting", "structure", "page"],
        }

        evidence = []
        for span in top_spans:
            token = span.get("token", "")
            start = span.get("start", 0)

            # Get surrounding context (±100 chars)
            ctx_start = max(0, start - 100)
            ctx_end = min(len(report_text), start + 100)
            context = report_text[ctx_start:ctx_end].strip()

            # Assign to section
            assigned_section = "general"
            for sec_name, keywords in section_keywords.items():
                if any(kw in context.lower() for kw in keywords):
                    assigned_section = sec_name
                    break

            evidence.append({
                "token": token,
                "importance_score": span.get("score", 0),
                "char_position": {"start": span.get("start"), "end": span.get("end")},
                "context": context,
                "assigned_section": assigned_section,
                "verdict_impact": "high" if span["score"] > 0.8 else "medium" if span["score"] > 0.5 else "low",
            })

        return evidence

    def _build_improvement_roadmap(
        self,
        unified_verdict: Dict,
        section_explanations: Dict,
        parsed_data: Dict,
    ) -> List[Dict]:
        """Build a prioritised, actionable improvement roadmap."""
        roadmap = []
        priority = 1

        # From section scores, identify lowest-scoring sections
        sections = parsed_data.get("sections", [])
        scored_sections = [
            (s["name"], s.get("score", 0), s.get("max_score", 1))
            for s in sections
            if s.get("score") is not None and s.get("max_score")
        ]
        scored_sections.sort(key=lambda x: x[1] / x[2])  # Sort by score ratio

        for sec_name, score, max_score in scored_sections[:3]:
            sec_exp = section_explanations.get(sec_name, {})
            improvements = sec_exp.get("specific_improvements", [])
            roadmap.append({
                "priority": priority,
                "section": sec_name,
                "current_score": f"{score}/{max_score}",
                "potential_gain": round((max_score - score), 1),
                "actions": improvements[:3] if improvements else [
                    f"Review {sec_name} against rubric criteria",
                    f"Add more detail and evidence to {sec_name}",
                ],
                "effort": "High" if score / max_score < 0.5 else "Medium",
            })
            priority += 1

        # Top-level recommendations from Master Arbiter
        top_recs = unified_verdict.get("priority_recommendations", [])
        for rec in top_recs[:3]:
            roadmap.append({
                "priority": priority,
                "section": "overall",
                "current_score": None,
                "potential_gain": None,
                "actions": [rec],
                "effort": "Medium",
            })
            priority += 1

        return roadmap
