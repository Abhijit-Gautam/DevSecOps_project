"""
Agent Orchestrator — runs the full SRLM pipeline end-to-end.

Pipeline:
  1. Parse report structure
  2. RoBERTa inference (ML baseline)
  3. Attention-based text highlighting
  4. Round 1: all specialist agents evaluate independently
  5. Self-reward: each agent scores its own reasoning
  6. Round 2: cross-review (SRLM — agents update on peer feedback)
  7. Master Arbiter produces unified verdict
  8. FOL verification
  9. XAI explanation generation
  10. Thought process log assembly

Inspired by:
  - SRLM: Yuan et al. (2024) "Self-Rewarding Language Models"
  - ReAct: Yao et al. (2022) "ReAct: Synergizing Reasoning and Acting in LLMs"
  - Multi-agent debate: Du et al. (2023) "Improving Factuality via Multi-Agent Debate"
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    def __init__(self, roberta_model, ollama_client, groq_vlm_client=None, srlm_rounds: int = 2):
        from .specialized_agents import build_all_agents
        from .master_arbiter import MasterArbiter
        from ..xai.explainer import XAIExplainer
        from ..xai.fol_verifier import FOLVerifier

        self.roberta = roberta_model
        self.ollama = ollama_client
        self.groq_vlm = groq_vlm_client
        self.srlm_rounds = srlm_rounds

        self.agents = build_all_agents(ollama_client, groq_vlm_client)
        self.arbiter = MasterArbiter(ollama_client)
        self.explainer = XAIExplainer(roberta_model, ollama_client)
        self.fol_verifier = FOLVerifier()

    def run(
        self,
        report_text: str,
        parsed_data: Dict,
        run_srlm: bool = True,
        run_highlights: bool = True,
        run_fol: bool = True,
        run_xai: bool = True,
        diagram_images: Optional[List[str]] = None,
        pdf_pages: Optional[List[str]] = None,
        step_callback=None,  # callable(event: str, data: dict) — for SSE streaming
    ) -> Dict[str, Any]:
        """
        Execute the full analysis pipeline.

        Returns a comprehensive result dict containing all analysis outputs.
        step_callback(event, data) is called after each major step if provided.
        """
        t_start = time.time()
        timeline: List[Dict] = []

        def log_step(name: str, data: Any = None):
            elapsed = round((time.time() - t_start) * 1000)
            timeline.append({"name": name, "elapsed_ms": elapsed, "data": data})
            if step_callback:
                try:
                    payload = {"elapsed_ms": elapsed, **(data or {})} if isinstance(data, dict) else {"elapsed_ms": elapsed, "data": data}
                    step_callback(name, payload)
                except Exception:
                    pass

        # ── Step 1: RoBERTa baseline ──────────────────────────────────────
        log_step("start")
        roberta_result = self.roberta.predict(report_text)
        log_step("roberta_inference", {
            "label": roberta_result["predicted_label"],
            "confidence": roberta_result["confidence"],
        })

        # ── Step 2: Attention highlights ──────────────────────────────────
        highlight_data = None
        if run_highlights:
            try:
                highlight_data = self.roberta.get_token_importance(report_text)
                log_step("attention_highlights", {
                    "n_spans": len(highlight_data.get("highlighted_spans", [])),
                })
            except Exception as e:
                logger.warning(f"Highlight extraction failed: {e}")
                highlight_data = {"error": str(e), "highlighted_spans": []}

        # ── Step 3: Round 1 — independent agent evaluations ──────────────
        agent_evaluations: List[Dict] = []
        if run_srlm:
            agent_context = {"diagram_images": diagram_images or []}
            for agent in self.agents:
                try:
                    ev = agent.evaluate(report_text, parsed_data, agent_context)
                    agent_evaluations.append(ev)
                    log_step(f"agent_r1_{agent.name}", {"verdict": ev.get("verdict")})
                except Exception as e:
                    logger.error(f"{agent.name} evaluation failed: {e}")
                    agent_evaluations.append({
                        "agent": agent.name, "round": 1,
                        "verdict": "Error", "error": str(e),
                    })

        # ── Step 4: Self-reward scoring ───────────────────────────────────
        self_reward_scores: Dict[str, float] = {}
        if run_srlm and agent_evaluations:
            for i, (agent, ev) in enumerate(zip(self.agents, agent_evaluations)):
                try:
                    sr = agent.self_reward(ev)
                    score = float(sr.get("score", 5.0))
                    self_reward_scores[agent.name] = score
                    # Attach self-reward to the evaluation
                    agent_evaluations[i]["self_reward"] = sr
                    log_step(f"self_reward_{agent.name}", {"score": score})
                except Exception as e:
                    logger.warning(f"Self-reward failed for {agent.name}: {e}")
                    self_reward_scores[agent.name] = 5.0

        # ── Step 5: Round 2 — cross-review (SRLM) ────────────────────────
        cross_reviews: List[Dict] = []
        if run_srlm and len(agent_evaluations) > 1 and self.srlm_rounds >= 2:
            for i, (agent, ev) in enumerate(zip(self.agents, agent_evaluations)):
                # Each agent reviews the agent next in the list (circular)
                peer_idx = (i + 1) % len(agent_evaluations)
                peer_ev = agent_evaluations[peer_idx]
                try:
                    cr = agent.review_peer(peer_ev, ev, report_text)
                    cr["reviewer"] = agent.name
                    cr["reviewee"] = peer_ev.get("agent")
                    cross_reviews.append(cr)
                    log_step(f"cross_review_{agent.name}", {
                        "agree": cr.get("agree_with_peer")
                    })
                except Exception as e:
                    logger.warning(f"Cross-review failed for {agent.name}: {e}")

        pdf_annotations: List[Dict] = []
        if agent_evaluations:
            from ..utils.pdf_highlights import build_pdf_annotations
            pdf_annotations = build_pdf_annotations(agent_evaluations, report_text, pdf_pages)
            if highlight_data is None:
                highlight_data = {"highlighted_spans": [], "threshold": 0.5}
            highlight_data["pdf_annotations"] = pdf_annotations
            log_step("pdf_highlight_annotations", {"n_annotations": len(pdf_annotations)})

        # ── Step 6: Master Arbiter ────────────────────────────────────────
        unified_verdict: Dict = {}
        if run_srlm:
            try:
                unified_verdict = self.arbiter.arbitrate(
                    agent_evaluations=agent_evaluations,
                    self_reward_scores=self_reward_scores,
                    cross_reviews=cross_reviews,
                    parsed_data=parsed_data,
                    roberta_result=roberta_result,
                )
                log_step("master_arbiter", {
                    "verdict": unified_verdict.get("final_verdict"),
                    "confidence": unified_verdict.get("confidence"),
                })
            except Exception as e:
                logger.error(f"Master arbitration failed: {e}")
                unified_verdict = {
                    "final_verdict": roberta_result["predicted_label"],
                    "confidence": roberta_result["confidence"],
                    "error": str(e),
                }
        else:
            # SRLM disabled — use RoBERTa result only
            unified_verdict = {
                "final_verdict": roberta_result["predicted_label"],
                "confidence": roberta_result["confidence"],
                "executive_summary": "SRLM disabled — RoBERTa prediction only.",
            }

        # ── Step 7: FOL verification ──────────────────────────────────────
        fol_result: Dict = {}
        if run_fol:
            try:
                fol_result = self.fol_verifier.verify(
                    verdict=unified_verdict.get("final_verdict", ""),
                    parsed_data=parsed_data,
                )
                log_step("fol_verification", {
                    "consistent": fol_result.get("consistent"),
                    "violated_rules": len(fol_result.get("violated_rules", [])),
                })
            except Exception as e:
                logger.error(f"FOL verification failed: {e}")
                fol_result = {"error": str(e)}

        # ── Step 8: XAI explanation ───────────────────────────────────────
        xai_result: Dict = {}
        if run_xai:
            try:
                xai_result = self.explainer.explain(
                    report_text=report_text,
                    roberta_result=roberta_result,
                    unified_verdict=unified_verdict,
                    highlight_data=highlight_data,
                    parsed_data=parsed_data,
                )
                log_step("xai_explanation", {"generated": True})
            except Exception as e:
                logger.error(f"XAI explanation failed: {e}")
                xai_result = {"error": str(e)}

        # ── Step 9: Thought process ───────────────────────────────────────
        thought_process = self.arbiter.generate_thought_process(
            report_text=report_text,
            agent_evaluations=agent_evaluations,
            unified_verdict=unified_verdict,
            roberta_result=roberta_result,
            highlight_data=highlight_data,
        )
        # Patch FOL step into thought process
        for step in thought_process:
            if step.get("type") == "fol_verification":
                step["evidence"] = [
                    f"Rule: {r}" for r in fol_result.get("satisfied_rules", [])[:3]
                ]
                step["description"] = (
                    f"FOL verification: "
                    f"{len(fol_result.get('satisfied_rules', []))} rules satisfied, "
                    f"{len(fol_result.get('violated_rules', []))} violated. "
                    f"Verdict is {'consistent' if fol_result.get('consistent') else 'inconsistent'} "
                    f"with formal rubric axioms."
                )

        log_step("complete")

        return {
            "roberta_result": roberta_result,
            "highlight_data": highlight_data,
            "pdf_annotations": pdf_annotations,
            "agent_evaluations": agent_evaluations,
            "self_reward_scores": self_reward_scores,
            "cross_reviews": cross_reviews,
            "unified_verdict": unified_verdict,
            "fol_result": fol_result,
            "xai_result": xai_result,
            "thought_process": thought_process,
            "pipeline_timeline": timeline,
            "total_elapsed_ms": round((time.time() - t_start) * 1000),
        }
