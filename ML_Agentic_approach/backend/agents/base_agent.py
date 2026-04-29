"""
Base agent class for the SRLM (Self-Rewarding Language Models) pipeline.

Each specialist agent:
1. Independently evaluates a specific report aspect (Round 1)
2. Scores its own reasoning quality (self-reward, SRLM)
3. Reviews peer evaluations and may revise its assessment (Round 2)

Reference:
  Yuan et al. (2024) "Self-Rewarding Language Models"
  https://arxiv.org/abs/2401.10020
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

HIGHLIGHT_SCHEMA_INSTRUCTION = """
Also return "highlight_annotations": a list of up to 5 objects for PDF attention highlighting.
Include bad/weak sentences and good/strong sentences when present.
Each object must include:
  "text_span": exact sentence or phrase from the report,
  "page_number": integer page number if known, otherwise 1,
  "issue_type": "bad_sentence"|"good_sentence"|"formatting_issue"|"diagram_issue"|"warning",
  "severity": "low"|"medium"|"high",
  "explanation": why it was marked,
  "suggestion": concrete improvement or reinforcement,
  "score_impact": numeric impact from -10 to +10.
Use exact report wording for text_span so the UI can align highlights.
"""


SELF_REWARD_SYSTEM_PROMPT = """
You are an expert evaluator assessing the quality of an academic evaluation.
Your job is to judge how thorough, accurate, and well-reasoned the evaluation is.
Score on a scale of 1-10 where:
  1-3: Superficial, lacks evidence, vague conclusions
  4-6: Adequate, some evidence but could be stronger
  7-8: Good, well-reasoned with solid evidence
  9-10: Excellent, comprehensive, specific evidence, nuanced analysis
"""


class BaseAgent:
    """
    Abstract base for all specialist evaluation agents.

    Subclasses must define:
      - name: str
      - role: str
      - focus_areas: List[str]
      - _build_evaluation_prompt(report_text, parsed_data, context) -> str
    """

    name: str = "BaseAgent"
    role: str = "General Evaluator"
    focus_areas: List[str] = []

    def __init__(self, ollama_client):
        self.ollama = ollama_client

    # ── Public API ────────────────────────────────────────────────────────────

    def evaluate(
        self,
        report_text: str,
        parsed_data: Optional[Dict] = None,
        context: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Round 1: independent evaluation of this agent's specialty."""
        prompt = self._build_evaluation_prompt(report_text, parsed_data or {}, context or {})
        system = self._system_prompt()

        raw = self.ollama.generate_json(prompt=prompt, system=system, temperature=0.3)

        if not raw:
            raw = self._fallback_evaluation(report_text, parsed_data)

        # Guarantee list fields are always actual lists — LLM may return null/string
        for field in ("strengths", "weaknesses", "evidence", "recommendations", "issues", "suggestions"):
            val = raw.get(field)
            raw[field] = val if isinstance(val, list) else []
        raw["highlight_annotations"] = self._normalise_highlight_annotations(
            raw.get("highlight_annotations")
        )

        raw["agent"] = self.name
        raw["round"] = 1
        return raw

    def self_reward(self, evaluation: Dict) -> Dict[str, Any]:
        """
        SRLM self-reward step: the agent scores its own evaluation quality.
        Returns {"score": float, "justification": str, "weaknesses": List[str]}
        """
        eval_text = json.dumps(evaluation, indent=2)
        prompt = f"""
You previously produced this evaluation:

{eval_text}

Now assess the quality of YOUR OWN evaluation:
1. How comprehensive is your analysis? Did you cover all relevant evidence?
2. How specific and well-supported are your claims?
3. Are your conclusions logically sound?
4. Did you miss any important aspects?

Return JSON with keys:
  "score": float (1-10),
  "justification": str,
  "weaknesses": list of str,
  "strengths": list of str
"""
        result = self.ollama.generate_json(
            prompt=prompt,
            system=SELF_REWARD_SYSTEM_PROMPT,
            temperature=0.2,
        )
        if not result:
            result = {"score": 6.0, "justification": "Unable to self-assess.", "weaknesses": [], "strengths": []}
        result.setdefault("score", 6.0)
        return result

    def review_peer(
        self,
        peer_evaluation: Dict,
        my_evaluation: Dict,
        report_text: str,
    ) -> Dict[str, Any]:
        """
        SRLM cross-review: this agent reviews a peer's evaluation
        and optionally revises its own stance.
        """
        prompt = f"""
You are the {self.name} agent reviewing a peer evaluation.

YOUR previous evaluation:
{json.dumps(my_evaluation, indent=2)}

PEER agent ({peer_evaluation.get('agent', 'Unknown')}) evaluation:
{json.dumps(peer_evaluation, indent=2)}

Consider the peer's perspective. Then return JSON with keys:
  "agree_with_peer": bool,
  "points_of_agreement": list of str,
  "points_of_disagreement": list of str,
  "revised_verdict": str (your updated verdict after seeing the peer's view),
  "confidence_change": float (e.g. +0.1 or -0.2, reflecting change in your certainty),
  "reasoning": str
"""
        result = self.ollama.generate_json(prompt=prompt, temperature=0.3)
        if not result:
            result = {
                "agree_with_peer": True,
                "points_of_agreement": [],
                "points_of_disagreement": [],
                "revised_verdict": my_evaluation.get("verdict", ""),
                "confidence_change": 0.0,
                "reasoning": "Unable to cross-review.",
            }
        return result

    # ── Subclass contract ─────────────────────────────────────────────────────

    def _system_prompt(self) -> str:
        return f"""
You are a specialist AI agent: {self.name}.
Your role: {self.role}
You focus on: {', '.join(self.focus_areas)}

Analyse academic research reports objectively. Be specific, cite text evidence.
Always return valid JSON as instructed. Be precise and analytical.
{self._highlight_instruction()}
"""

    def _build_evaluation_prompt(
        self, report_text: str, parsed_data: Dict, context: Dict
    ) -> str:
        raise NotImplementedError

    def _highlight_instruction(self) -> str:
        return HIGHLIGHT_SCHEMA_INSTRUCTION

    def _normalise_highlight_annotations(self, annotations: Any) -> List[Dict[str, Any]]:
        if not isinstance(annotations, list):
            return []
        normalised = []
        for item in annotations[:8]:
            if not isinstance(item, dict):
                continue
            text_span = str(item.get("text_span") or item.get("exact_text_span") or "").strip()
            if not text_span:
                continue
            normalised.append({
                "text_span": text_span,
                "page_number": int(item.get("page_number") or item.get("page") or 1),
                "issue_type": str(item.get("issue_type") or "warning"),
                "severity": str(item.get("severity") or "medium"),
                "explanation": str(item.get("explanation") or ""),
                "suggestion": str(item.get("suggestion") or ""),
                "score_impact": float(item.get("score_impact") or 0),
                "agent": self.name,
            })
        return normalised

    def _fallback_evaluation(self, report_text: str, parsed_data: Optional[Dict]) -> Dict:
        return {
            "verdict": "Unable to evaluate",
            "score": 0,
            "max_score": 10,
            "reasoning": "LLM did not return valid JSON.",
            "evidence": [],
            "strengths": [],
            "weaknesses": [],
            "recommendations": [],
            "highlight_annotations": [],
        }
