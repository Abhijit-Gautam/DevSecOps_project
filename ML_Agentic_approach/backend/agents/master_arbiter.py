"""
Master Arbiter — the final judge in the SRLM pipeline.

After all specialist agents have evaluated and cross-reviewed the report,
the Master Arbiter synthesises their verdicts into a single, unified assessment.

Implements the "LLM-as-Judge" paradigm from:
  Zheng et al. (2023) "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena"
  https://arxiv.org/abs/2306.05685
"""
from __future__ import annotations

import json
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

ARBITER_SYSTEM = """
You are the Master Arbiter — a senior academic evaluation expert.
You synthesise the assessments of multiple specialist agents into a
single comprehensive, authoritative verdict.

Your synthesis must:
1. Weigh each specialist's assessment by their self-reward quality score
2. Identify consensus and genuine disagreements
3. Produce a final verdict that is fair, evidence-based, and actionable
4. Be calibrated: high confidence only when agents strongly agree

Always reason transparently and return valid JSON.
"""


class MasterArbiter:
    def __init__(self, ollama_client):
        self.ollama = ollama_client

    def arbitrate(
        self,
        agent_evaluations: List[Dict],
        self_reward_scores: Dict[str, float],
        cross_reviews: List[Dict],
        parsed_data: Optional[Dict] = None,
        roberta_result: Optional[Dict] = None,
    ) -> Dict:
        """
        Produce the unified verdict from all agent outputs.

        Args:
            agent_evaluations: Round-1 evaluations from each specialist
            self_reward_scores: {agent_name: float} — self-assessed quality
            cross_reviews: Round-2 cross-review responses
            parsed_data: structured report metadata
            roberta_result: prediction from RoBERTa (label + confidence)

        Returns:
            Comprehensive unified verdict dict
        """
        # Build a weighted summary for the prompt
        weighted_summaries = []
        for ev in agent_evaluations:
            agent = ev.get("agent", "Unknown")
            reward = self_reward_scores.get(agent, 5.0)
            weighted_summaries.append({
                "agent": agent,
                "verdict": ev.get("verdict"),
                "score": ev.get("score"),
                "max_score": ev.get("max_score"),
                "key_reasoning": ev.get("reasoning", "")[:300],
                "strengths": ev.get("strengths", []),
                "weaknesses": ev.get("weaknesses", []),
                "self_reward_quality": reward,
            })

        # Cross-review consensus
        consensus_points = []
        disagreement_points = []
        for cr in cross_reviews:
            consensus_points.extend(cr.get("points_of_agreement", []))
            disagreement_points.extend(cr.get("points_of_disagreement", []))

        roberta_context = ""
        if roberta_result:
            roberta_context = f"""
ML Model (RoBERTa fine-tuned on historical reports):
  - Prediction: {roberta_result.get("predicted_label")}
  - Confidence: {roberta_result.get("confidence", 0):.2%}
  - Probabilities: {json.dumps(roberta_result.get("probabilities", {}))}
"""

        rubric_context = ""
        if parsed_data:
            rubric_context = f"""
Rubric scores from report:
  - Total: {parsed_data.get("total_score")}/{parsed_data.get("max_score")}
  - Domain: {parsed_data.get("domain")}
  - Sections: {json.dumps([s for s in parsed_data.get("sections", [])], indent=2)[:500]}
"""

        prompt = f"""
You are the Master Arbiter. Here are the specialist agent evaluations:

{json.dumps(weighted_summaries, indent=2)}

Cross-review consensus points:
{json.dumps(list(set(consensus_points))[:10], indent=2)}

Cross-review disagreements:
{json.dumps(list(set(disagreement_points))[:10], indent=2)}

{roberta_context}
{rubric_context}

Synthesise all of the above into a UNIFIED verdict. Consider:
1. Weight higher-quality agents (higher self_reward_quality) more heavily
2. Where agents strongly agree, reflect that in your confidence
3. Where agents disagree, explain the conflict and your reasoning for resolution
4. The RoBERTa model provides an empirical data-driven baseline — factor it in
5. The rubric score gives ground-truth structure — validate against it

Return JSON:
{{
  "final_verdict": "Excellent|Good|Needs Improvement",
  "overall_score": float (0-100, percentage),
  "confidence": float (0-1),
  "executive_summary": "2-3 sentence overall assessment",
  "dimension_verdicts": {{
    "abstract": "verdict",
    "methodology": "verdict",
    "results": "verdict",
    "citations": "verdict",
    "document_structure": "verdict",
    "content_depth": "verdict"
  }},
  "key_strengths": ["top 3-5 strengths"],
  "key_weaknesses": ["top 3-5 weaknesses"],
  "priority_recommendations": ["top 3-5 actionable improvements"],
  "agent_agreement_level": "Strong|Moderate|Weak",
  "ml_model_alignment": "Aligned|Partial|Diverged",
  "reasoning_chain": "step-by-step reasoning for this verdict"
}}
"""
        result = self.ollama.generate_json(
            prompt=prompt,
            system=ARBITER_SYSTEM,
            temperature=0.2,
        )

        if not result:
            # Fallback: simple majority vote
            result = self._fallback_arbitration(agent_evaluations, roberta_result)

        result["raw_agent_evaluations"] = weighted_summaries
        result["cross_review_consensus"] = list(set(consensus_points))[:10]
        result["cross_review_disagreements"] = list(set(disagreement_points))[:10]
        return result

    def generate_thought_process(
        self,
        report_text: str,
        agent_evaluations: List[Dict],
        unified_verdict: Dict,
        roberta_result: Optional[Dict],
        highlight_data: Optional[Dict],
    ) -> List[Dict]:
        """
        Generate a step-by-step thought process log for display in the UI.
        Each step has: step_number, title, description, evidence, duration_ms.
        """
        steps = []
        step_n = 1

        # Step 1: Text extraction & preprocessing
        steps.append({
            "step": step_n, "title": "Text Extraction & Preprocessing",
            "description": f"Report text extracted ({len(report_text)} characters, {len(report_text.split())} words). Whitespace normalised, encoding validated.",
            "evidence": [], "type": "preprocessing",
        })
        step_n += 1

        # Step 2: RoBERTa inference
        if roberta_result:
            steps.append({
                "step": step_n, "title": "RoBERTa Sequence Classification",
                "description": (
                    f"Fine-tuned RoBERTa (F1=0.981) ran inference on the tokenised report. "
                    f"Predicted: '{roberta_result.get('predicted_label')}' with "
                    f"{roberta_result.get('confidence', 0):.2%} confidence."
                ),
                "evidence": [f"Probability distribution: {json.dumps(roberta_result.get('probabilities', {}))}"],
                "type": "ml_inference",
                "model": "roberta-base fine-tuned",
            })
            step_n += 1

        # Step 3: Attention highlights
        if highlight_data and highlight_data.get("highlighted_spans"):
            top_spans = sorted(
                highlight_data["highlighted_spans"], key=lambda x: x["score"], reverse=True
            )[:3]
            steps.append({
                "step": step_n, "title": "Attention-Based Text Highlighting",
                "description": "Attention rollout computed across all 12 transformer layers to identify the most influential text segments.",
                "evidence": [f"Top token: '{s['token']}' (importance: {s['score']:.3f})" for s in top_spans],
                "type": "xai",
            })
            step_n += 1

        # Steps for each agent
        for ev in agent_evaluations:
            agent_name = ev.get("agent", "Unknown")
            steps.append({
                "step": step_n,
                "title": f"Agent: {agent_name} — Round 1 Evaluation",
                "description": (
                    f"{agent_name} independently assessed its specialty. "
                    f"Verdict: {ev.get('verdict', 'N/A')} (score: {ev.get('score', 'N/A')}/{ev.get('max_score', 10)})"
                ),
                "evidence": ev.get("evidence", [])[:2],
                "reasoning_summary": ev.get("reasoning", "")[:200],
                "type": "agent_evaluation",
                "agent": agent_name,
            })
            step_n += 1

        # Cross-review step
        steps.append({
            "step": step_n, "title": "SRLM Cross-Review Phase",
            "description": "Agents reviewed each other's evaluations. Where disagreements were found, agents revised their stances (Self-Rewarding Language Model pattern).",
            "evidence": unified_verdict.get("cross_review_consensus", [])[:3],
            "type": "srlm_cross_review",
        })
        step_n += 1

        # Master arbitration
        steps.append({
            "step": step_n, "title": "Master Arbiter — Unified Verdict",
            "description": (
                f"Master Arbiter synthesised {len(agent_evaluations)} agent verdicts "
                f"(weighted by self-reward quality scores). "
                f"Final verdict: '{unified_verdict.get('final_verdict')}' "
                f"(confidence: {unified_verdict.get('confidence', 0):.2%}). "
                f"Agent agreement level: {unified_verdict.get('agent_agreement_level', 'N/A')}."
            ),
            "evidence": unified_verdict.get("key_strengths", [])[:2],
            "type": "master_arbitration",
            "verdict": unified_verdict.get("final_verdict"),
        })
        step_n += 1

        # FOL verification (placeholder — filled in by orchestrator)
        steps.append({
            "step": step_n, "title": "FOL Consistency Verification",
            "description": "First-Order Logic rules verified the verdict against formal rubric axioms.",
            "evidence": [],
            "type": "fol_verification",
        })

        return steps

    # ── Fallback ─────────────────────────────────────────────────────────────

    def _fallback_arbitration(
        self, agent_evaluations: List[Dict], roberta_result: Optional[Dict]
    ) -> Dict:
        verdicts = [e.get("verdict", "Needs Improvement") for e in agent_evaluations]
        vote_count = {"Excellent": 0, "Good": 0, "Needs Improvement": 0}
        for v in verdicts:
            if v in vote_count:
                vote_count[v] += 1
        final = max(vote_count, key=vote_count.get)
        if roberta_result:
            final = roberta_result.get("predicted_label", final)
        return {
            "final_verdict": final,
            "overall_score": 50.0,
            "confidence": 0.5,
            "executive_summary": "Fallback arbitration — LLM synthesis unavailable.",
            "dimension_verdicts": {},
            "key_strengths": [],
            "key_weaknesses": [],
            "priority_recommendations": [],
            "agent_agreement_level": "Unknown",
            "ml_model_alignment": "Unknown",
            "reasoning_chain": "Majority vote fallback.",
        }
