import unittest

from backend.agents.orchestrator import AgentOrchestrator
from backend.agents.specialized_agents import build_all_agents


class FakeOllama:
    def __init__(self):
        self.calls = []

    def generate_json(self, prompt, system="", temperature=0.3):
        self.calls.append({"prompt": prompt, "system": system, "temperature": temperature})
        if "YOUR OWN evaluation" in prompt:
            return {"score": 7.5, "justification": "complete", "weaknesses": [], "strengths": []}
        if "reviewing a peer evaluation" in prompt:
            return {
                "agree_with_peer": True,
                "points_of_agreement": ["consistent rubric interpretation"],
                "points_of_disagreement": [],
                "revised_verdict": "Good",
                "confidence_change": 0.0,
                "reasoning": "Peer view is compatible.",
            }
        if "Master Arbiter" in prompt:
            return {
                "final_verdict": "Good",
                "overall_score": 75,
                "confidence": 0.8,
                "executive_summary": "Solid report.",
                "dimension_verdicts": {},
                "key_strengths": [],
                "key_weaknesses": [],
                "priority_recommendations": [],
                "agent_agreement_level": "Strong",
                "ml_model_alignment": "Aligned",
                "reasoning_chain": "Agents agree.",
            }
        if "FormatterAgent" in system:
            return {
                "score": 8,
                "pass_fail": "pass",
                "issues": [],
                "explanation": "Formatting is consistent.",
                "suggestions": [],
                "highlight_annotations": [{
                    "text_span": "Abstract: 8/10",
                    "page_number": 1,
                    "issue_type": "good_sentence",
                    "severity": "low",
                    "explanation": "Clear section score.",
                    "suggestion": "Keep this formatting.",
                    "score_impact": 2,
                }],
            }
        return {
            "verdict": "Good",
            "score": 7,
            "max_score": 10,
            "reasoning": "Adequate evidence.",
            "evidence": [],
            "strengths": [],
            "weaknesses": [],
            "recommendations": [],
        }


class FakeGroqVLM:
    def __init__(self):
        self.calls = []

    def generate_json_with_images(self, prompt, image_urls, system="", temperature=0.1, max_tokens=900):
        self.calls.append({
            "prompt": prompt,
            "image_urls": image_urls,
            "system": system,
            "temperature": temperature,
            "max_tokens": max_tokens,
        })
        return {
            "score": 8.5,
            "pass_fail": "pass",
            "issues": [],
            "explanation": "Diagrams are relevant, clear, labeled, and useful.",
            "suggestions": [],
            "highlight_annotations": [{
                "text_span": "Figures: 1/1",
                "page_number": 1,
                "issue_type": "diagram_issue",
                "severity": "low",
                "explanation": "Diagram evidence is present.",
                "suggestion": "Keep labels visible.",
                "score_impact": 1,
            }],
        }


class FakeRoBERTa:
    def predict(self, report_text):
        return {
            "predicted_label_id": 1,
            "predicted_label": "Good",
            "confidence": 0.8,
            "probabilities": {"Good": 0.8},
        }


class AgentIntegrationTests(unittest.TestCase):
    def test_factory_includes_diagram_and_formatter_agents(self):
        agents = build_all_agents(FakeOllama(), FakeGroqVLM())
        names = [agent.name for agent in agents]

        self.assertIn("DiagramAgent", names)
        self.assertIn("FormatterAgent", names)

    def test_orchestrator_invokes_new_agents_in_srlm_and_cross_review(self):
        ollama = FakeOllama()
        groq = FakeGroqVLM()
        orchestrator = AgentOrchestrator(FakeRoBERTa(), ollama, groq, srlm_rounds=2)

        result = orchestrator.run(
            "Abstract: 8/10\nMethodology: 7/10\nResults: 7/10\nFigures: 1/1",
            parsed_data={"document_quality": {"font_consistency": 1, "line_spacing": 1}},
            run_srlm=True,
            run_highlights=False,
            run_fol=False,
            run_xai=False,
            diagram_images=["data:image/png;base64,abc"],
        )

        agent_names = [ev["agent"] for ev in result["agent_evaluations"]]
        reviewers = [review["reviewer"] for review in result["cross_reviews"]]
        self.assertIn("DiagramAgent", agent_names)
        self.assertIn("FormatterAgent", agent_names)
        self.assertIn("DiagramAgent", reviewers)
        self.assertIn("FormatterAgent", reviewers)
        self.assertEqual(len(groq.calls), 1)
        self.assertEqual(groq.calls[0]["image_urls"], ["data:image/png;base64,abc"])
        self.assertGreaterEqual(len(result["highlight_data"]["pdf_annotations"]), 2)


if __name__ == "__main__":
    unittest.main()
