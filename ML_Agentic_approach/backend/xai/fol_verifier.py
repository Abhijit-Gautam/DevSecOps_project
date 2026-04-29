"""
First-Order Logic (FOL) Verifier.

Encodes the academic rubric as formal FOL axioms and verifies whether
the assigned verdict is logically consistent with the parsed report data.

FOL Schema:
  Predicates:
    - ExcellentReport(r)   — report r received 'Excellent' verdict
    - GoodReport(r)        — report r received 'Good' verdict
    - NeedsImprovement(r)  — report r received 'Needs Improvement' verdict
    - HasSection(r, s)     — report r contains section s
    - ScoreGTE(r, ratio)   — report r's total_score/max_score >= ratio
    - SectionScoreGTE(r, s, ratio) — section s of r scored >= ratio of max
    - HasReferences(r, n)  — report r has >= n verified references
    - DocQualityGTE(r, ratio) — document quality >= ratio

  Axioms (rules that must hold):
    A1: ExcellentReport(r) → ScoreGTE(r, 0.90)
    A2: GoodReport(r)      → ScoreGTE(r, 0.70)
    A3: ExcellentReport(r) → HasSection(r, abstract)
                           ∧ HasSection(r, methodology)
                           ∧ HasSection(r, results)
                           ∧ HasSection(r, conclusion)
    A4: ExcellentReport(r) → DocQualityGTE(r, 0.85)
    A5: ¬HasSection(r, methodology) → ¬ExcellentReport(r)
    A6: ¬HasSection(r, abstract) → ¬ExcellentReport(r)
    A7: ScoreGTE(r, 0.90) ∧ AllSectionsPresent(r) → ExcellentReport(r)  [sufficient]
    A8: ScoreGTE(r, 0.50) ∧ ¬ScoreGTE(r, 0.70) → NeedsImprovement(r)   [sufficient]

Reference: Russell & Norvig, "Artificial Intelligence: A Modern Approach", Ch. 8
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class FOLRule:
    """Represents a single FOL axiom with its Python verification function."""
    id: str
    name: str
    natural_language: str
    formal: str
    applicable_to: List[str]  # which verdicts this rule applies to


@dataclass
class VerificationResult:
    rule_id: str
    rule_name: str
    satisfied: bool
    actual_value: Any
    expected: str
    explanation: str
    verdict_impact: str  # "supports" | "contradicts" | "neutral"


# ── FOL Axiom definitions ─────────────────────────────────────────────────────

_AXIOMS: List[FOLRule] = [
    FOLRule(
        id="A1",
        name="Excellent score threshold",
        natural_language="An Excellent report must have total score ≥ 90% of max",
        formal="∀r: ExcellentReport(r) → ScoreGTE(r, 0.90)",
        applicable_to=["Excellent"],
    ),
    FOLRule(
        id="A2",
        name="Good score threshold",
        natural_language="A Good report must have total score ≥ 70% of max",
        formal="∀r: GoodReport(r) → ScoreGTE(r, 0.70)",
        applicable_to=["Good"],
    ),
    FOLRule(
        id="A3",
        name="Needs Improvement score threshold",
        natural_language="Needs Improvement implies score < 70%",
        formal="∀r: NeedsImprovement(r) → ¬ScoreGTE(r, 0.70)",
        applicable_to=["Needs Improvement"],
    ),
    FOLRule(
        id="A4",
        name="Excellent requires all sections",
        natural_language="Excellent report must contain abstract, methodology, results, and conclusion",
        formal="∀r: ExcellentReport(r) → HasSection(r, abstract) ∧ HasSection(r, methodology) ∧ HasSection(r, results) ∧ HasSection(r, conclusion)",
        applicable_to=["Excellent"],
    ),
    FOLRule(
        id="A5",
        name="No methodology disqualifies Excellent",
        natural_language="A report without methodology cannot be Excellent",
        formal="∀r: ¬HasSection(r, methodology) → ¬ExcellentReport(r)",
        applicable_to=["Excellent"],
    ),
    FOLRule(
        id="A6",
        name="No abstract disqualifies Excellent",
        natural_language="A report without abstract cannot be Excellent",
        formal="∀r: ¬HasSection(r, abstract) → ¬ExcellentReport(r)",
        applicable_to=["Excellent"],
    ),
    FOLRule(
        id="A7",
        name="Document quality for Excellent",
        natural_language="Excellent reports must have document quality ≥ 85%",
        formal="∀r: ExcellentReport(r) → DocQualityGTE(r, 0.85)",
        applicable_to=["Excellent"],
    ),
    FOLRule(
        id="A8",
        name="Literature review for Good/Excellent",
        natural_language="Good or Excellent reports must have at least 3 verified references",
        formal="∀r: (GoodReport(r) ∨ ExcellentReport(r)) → HasReferences(r, 3)",
        applicable_to=["Good", "Excellent"],
    ),
    FOLRule(
        id="A9",
        name="Section score consistency",
        natural_language="Excellent report must have all section scores ≥ 60% of max",
        formal="∀r,s: ExcellentReport(r) → SectionScoreGTE(r, s, 0.60)",
        applicable_to=["Excellent"],
    ),
    FOLRule(
        id="A10",
        name="Good requires abstract",
        natural_language="A Good report must have an abstract",
        formal="∀r: GoodReport(r) → HasSection(r, abstract)",
        applicable_to=["Good"],
    ),
]


class FOLVerifier:
    """
    Verifies the assigned verdict against FOL axioms.

    Usage:
        verifier = FOLVerifier()
        result = verifier.verify(verdict="Excellent", parsed_data={...})
    """

    def verify(self, verdict: str, parsed_data: Dict) -> Dict:
        """
        Run all applicable FOL rules against the parsed report data.

        Returns:
            {
                "verdict": str,
                "consistent": bool,
                "satisfied_rules": List[str],
                "violated_rules": List[str],
                "verification_details": List[dict],
                "fol_statements": List[str],
                "consistency_score": float (0-1),
                "explanation": str,
            }
        """
        if not parsed_data:
            return self._empty_result(verdict)

        # ── Predicate evaluations ────────────────────────────────────────
        predicates = self._evaluate_predicates(parsed_data)
        results: List[VerificationResult] = []

        for axiom in _AXIOMS:
            if verdict not in axiom.applicable_to and "all" not in axiom.applicable_to:
                continue
            try:
                result = self._check_axiom(axiom, verdict, predicates, parsed_data)
                results.append(result)
            except Exception as e:
                logger.warning(f"Axiom {axiom.id} check failed: {e}")

        satisfied = [r for r in results if r.satisfied]
        violated = [r for r in results if not r.satisfied]
        consistency_score = len(satisfied) / len(results) if results else 1.0

        # ── Generate FOL statements for display ──────────────────────────
        fol_statements = self._generate_fol_statements(verdict, predicates, parsed_data)

        # ── Overall consistency ───────────────────────────────────────────
        is_consistent = len(violated) == 0

        return {
            "verdict": verdict,
            "consistent": is_consistent,
            "consistency_score": round(consistency_score, 3),
            "satisfied_rules": [f"{r.rule_id}: {r.rule_name}" for r in satisfied],
            "violated_rules": [f"{r.rule_id}: {r.rule_name}" for r in violated],
            "verification_details": [
                {
                    "rule_id": r.rule_id,
                    "rule": r.rule_name,
                    "formal": next((a.formal for a in _AXIOMS if a.id == r.rule_id), ""),
                    "natural_language": next((a.natural_language for a in _AXIOMS if a.id == r.rule_id), ""),
                    "satisfied": r.satisfied,
                    "actual_value": r.actual_value,
                    "expected": r.expected,
                    "explanation": r.explanation,
                    "verdict_impact": r.verdict_impact,
                }
                for r in results
            ],
            "fol_statements": fol_statements,
            "predicates": predicates,
            "explanation": self._build_explanation(verdict, violated, satisfied, consistency_score),
        }

    # ── Predicate evaluation ─────────────────────────────────────────────────

    def _evaluate_predicates(self, parsed_data: Dict) -> Dict[str, Any]:
        """Evaluate all predicates from parsed report data."""
        total = parsed_data.get("total_score")
        max_s = parsed_data.get("max_score")
        score_ratio = (total / max_s) if (total is not None and max_s and max_s > 0) else None

        dq = parsed_data.get("document_quality", {})
        dq_total = dq.get("total")
        dq_max = dq.get("max_total", 7.0)
        dq_ratio = (dq_total / dq_max) if (dq_total is not None and dq_max > 0) else None

        ref_count = parsed_data.get("reference_count") or parsed_data.get("literature_review_count") or 0

        sections = {s["name"]: s for s in parsed_data.get("sections", [])}

        # Per-section score ratios
        section_ratios = {}
        for sec_name, sec in sections.items():
            if sec.get("score") is not None and sec.get("max_score"):
                section_ratios[sec_name] = sec["score"] / sec["max_score"]

        return {
            "score_ratio": score_ratio,
            "total_score": total,
            "max_score": max_s,
            "has_abstract": parsed_data.get("has_abstract", False),
            "has_methodology": parsed_data.get("has_methodology", False),
            "has_results": parsed_data.get("has_results", False),
            "has_conclusion": parsed_data.get("has_conclusion", False),
            "doc_quality_ratio": dq_ratio,
            "doc_quality_total": dq_total,
            "reference_count": ref_count,
            "section_ratios": section_ratios,
            "sections_present": list(sections.keys()),
        }

    # ── Axiom checkers ────────────────────────────────────────────────────────

    def _check_axiom(
        self,
        axiom: FOLRule,
        verdict: str,
        predicates: Dict,
        parsed_data: Dict,
    ) -> VerificationResult:
        score_ratio = predicates.get("score_ratio")

        # ── A1: Excellent → ScoreGTE(0.90) ───────────────────────────────
        if axiom.id == "A1":
            satisfied = score_ratio is None or score_ratio >= 0.90
            return VerificationResult(
                rule_id="A1", rule_name=axiom.name,
                satisfied=satisfied,
                actual_value=f"{score_ratio:.2%}" if score_ratio is not None else "N/A",
                expected="≥ 90%",
                explanation=f"Score ratio {score_ratio:.2%} {'meets' if satisfied else 'does NOT meet'} the 90% threshold for Excellent." if score_ratio else "Score data unavailable.",
                verdict_impact="supports" if satisfied else "contradicts",
            )

        # ── A2: Good → ScoreGTE(0.70) ─────────────────────────────────────
        if axiom.id == "A2":
            satisfied = score_ratio is None or score_ratio >= 0.70
            return VerificationResult(
                rule_id="A2", rule_name=axiom.name,
                satisfied=satisfied,
                actual_value=f"{score_ratio:.2%}" if score_ratio is not None else "N/A",
                expected="≥ 70%",
                explanation=f"Score ratio {score_ratio:.2%} {'meets' if satisfied else 'does NOT meet'} the 70% threshold for Good." if score_ratio else "Score data unavailable.",
                verdict_impact="supports" if satisfied else "contradicts",
            )

        # ── A3: NeedsImprovement → ¬ScoreGTE(0.70) ────────────────────────
        if axiom.id == "A3":
            # For NI verdict, we expect score < 70% (or score unknown)
            satisfied = score_ratio is None or score_ratio < 0.70
            return VerificationResult(
                rule_id="A3", rule_name=axiom.name,
                satisfied=satisfied,
                actual_value=f"{score_ratio:.2%}" if score_ratio is not None else "N/A",
                expected="< 70%",
                explanation=f"Score {score_ratio:.2%} {'is' if satisfied else 'is NOT'} below 70% as expected for Needs Improvement." if score_ratio else "Score unavailable.",
                verdict_impact="supports" if satisfied else "contradicts",
            )

        # ── A4: Excellent → all sections present ──────────────────────────
        if axiom.id == "A4":
            required = ["abstract", "methodology", "results", "conclusion"]
            missing = [s for s in required if not predicates.get(f"has_{s}", False)]
            satisfied = len(missing) == 0
            return VerificationResult(
                rule_id="A4", rule_name=axiom.name,
                satisfied=satisfied,
                actual_value={"present": [s for s in required if s not in missing], "missing": missing},
                expected="All 4 core sections present",
                explanation=f"Missing sections: {missing}" if missing else "All required sections are present.",
                verdict_impact="supports" if satisfied else "contradicts",
            )

        # ── A5: ¬HasMethodology → ¬Excellent ─────────────────────────────
        if axiom.id == "A5":
            has_method = predicates.get("has_methodology", False)
            # Rule is: if no methodology AND verdict is Excellent → violation
            satisfied = has_method  # Must have methodology for Excellent to be valid
            return VerificationResult(
                rule_id="A5", rule_name=axiom.name,
                satisfied=satisfied,
                actual_value=has_method,
                expected="True (methodology section present)",
                explanation="Methodology section found." if has_method else "No methodology section detected — contradicts Excellent verdict.",
                verdict_impact="supports" if satisfied else "contradicts",
            )

        # ── A6: ¬HasAbstract → ¬Excellent ────────────────────────────────
        if axiom.id == "A6":
            has_abs = predicates.get("has_abstract", False)
            satisfied = has_abs
            return VerificationResult(
                rule_id="A6", rule_name=axiom.name,
                satisfied=satisfied,
                actual_value=has_abs,
                expected="True (abstract present)",
                explanation="Abstract found." if has_abs else "No abstract detected — contradicts Excellent verdict.",
                verdict_impact="supports" if satisfied else "contradicts",
            )

        # ── A7: DocQualityGTE(0.85) for Excellent ─────────────────────────
        if axiom.id == "A7":
            dq_ratio = predicates.get("doc_quality_ratio")
            satisfied = dq_ratio is None or dq_ratio >= 0.85
            return VerificationResult(
                rule_id="A7", rule_name=axiom.name,
                satisfied=satisfied,
                actual_value=f"{dq_ratio:.2%}" if dq_ratio is not None else "N/A",
                expected="≥ 85%",
                explanation=f"Document quality {dq_ratio:.2%} {'meets' if satisfied else 'does NOT meet'} 85% threshold." if dq_ratio else "Document quality data unavailable.",
                verdict_impact="supports" if satisfied else "contradicts",
            )

        # ── A8: References ≥ 3 for Good/Excellent ─────────────────────────
        if axiom.id == "A8":
            refs = predicates.get("reference_count", 0)
            satisfied = refs >= 3
            return VerificationResult(
                rule_id="A8", rule_name=axiom.name,
                satisfied=satisfied,
                actual_value=refs,
                expected="≥ 3 verified references",
                explanation=f"{refs} references detected — {'sufficient' if satisfied else 'insufficient'} for {verdict}.",
                verdict_impact="supports" if satisfied else "contradicts",
            )

        # ── A9: Section score ratios ≥ 0.60 for Excellent ─────────────────
        if axiom.id == "A9":
            sec_ratios = predicates.get("section_ratios", {})
            low_sections = {k: v for k, v in sec_ratios.items() if v < 0.60}
            satisfied = len(low_sections) == 0
            return VerificationResult(
                rule_id="A9", rule_name=axiom.name,
                satisfied=satisfied,
                actual_value={"section_ratios": sec_ratios, "below_threshold": low_sections},
                expected="All sections ≥ 60% of max score",
                explanation=f"Sections below 60%: {list(low_sections.keys())}" if low_sections else "All sections meet 60% threshold.",
                verdict_impact="supports" if satisfied else "contradicts",
            )

        # ── A10: Good → HasAbstract ────────────────────────────────────────
        if axiom.id == "A10":
            has_abs = predicates.get("has_abstract", False)
            satisfied = has_abs
            return VerificationResult(
                rule_id="A10", rule_name=axiom.name,
                satisfied=satisfied,
                actual_value=has_abs,
                expected="Abstract present",
                explanation="Abstract present." if has_abs else "No abstract — may contradict Good verdict.",
                verdict_impact="supports" if satisfied else "contradicts",
            )

        # Unknown rule — pass by default
        return VerificationResult(
            rule_id=axiom.id, rule_name=axiom.name,
            satisfied=True, actual_value=None,
            expected="N/A", explanation="Rule not implemented.",
            verdict_impact="neutral",
        )

    # ── FOL statement generation ──────────────────────────────────────────────

    def _generate_fol_statements(
        self, verdict: str, predicates: Dict, parsed_data: Dict
    ) -> List[str]:
        """Generate formal FOL statements that describe this specific report."""
        statements = []
        report_id = "r"  # Skolem constant for this report

        # Existence claim
        pred_name = verdict.replace(" ", "").replace("Improvement", "Improvement")
        # Normalize
        if verdict == "Excellent":
            statements.append(f"ExcellentReport({report_id})")
        elif verdict == "Good":
            statements.append(f"GoodReport({report_id})")
        else:
            statements.append(f"NeedsImprovementReport({report_id})")

        # Score
        sr = predicates.get("score_ratio")
        ts = predicates.get("total_score")
        ms = predicates.get("max_score")
        if sr is not None:
            statements.append(f"TotalScore({report_id}) = {ts}/{ms} ({sr:.2%})")
            statements.append(f"ScoreGTE({report_id}, {sr:.2f})")

        # Section presence
        for sec in ["abstract", "methodology", "results", "conclusion"]:
            has = predicates.get(f"has_{sec}", False)
            if has:
                statements.append(f"HasSection({report_id}, {sec})")
            else:
                statements.append(f"¬HasSection({report_id}, {sec})")

        # Document quality
        dq_ratio = predicates.get("doc_quality_ratio")
        if dq_ratio is not None:
            statements.append(f"DocQuality({report_id}) = {predicates.get('doc_quality_total')}/7 ({dq_ratio:.2%})")

        # References
        refs = predicates.get("reference_count", 0)
        statements.append(f"HasReferences({report_id}, {refs})")

        # Section score ratios
        for sec_name, ratio in predicates.get("section_ratios", {}).items():
            statements.append(f"SectionScoreGTE({report_id}, {sec_name}, {ratio:.2f})")

        return statements

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _build_explanation(
        self,
        verdict: str,
        violated: List[VerificationResult],
        satisfied: List[VerificationResult],
        consistency_score: float = 1.0,
    ) -> str:
        if not violated:
            return (
                f"The verdict '{verdict}' is CONSISTENT with all {len(satisfied)} FOL axioms. "
                f"The report satisfies all formal requirements for this grade."
            )
        violation_names = [r.rule_name for r in violated]
        return (
            f"The verdict '{verdict}' VIOLATES {len(violated)} FOL axiom(s): {violation_names}. "
            f"This may indicate an inconsistency between the rubric score and the assigned label, "
            f"or missing structural elements required for this grade."
        )

    def _empty_result(self, verdict: str) -> Dict:
        return {
            "verdict": verdict,
            "consistent": True,
            "consistency_score": 1.0,
            "satisfied_rules": [],
            "violated_rules": [],
            "verification_details": [],
            "fol_statements": [f"ExcellentReport(r)"],
            "predicates": {},
            "explanation": "Insufficient parsed data for FOL verification.",
        }
