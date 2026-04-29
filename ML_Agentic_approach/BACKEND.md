# Backend Architecture — DevSecOps Report Evaluator

## Overview

A Flask-based REST API that evaluates academic reports using a multi-layer AI pipeline:

1. **RoBERTa** (fine-tuned sequence classifier) — fast ML baseline
2. **Agentic SRLM** (Self-Rewarding Language Models) — 6 specialist LLM agents + master arbiter
3. **XAI** (Explainable AI) — attention rollout + LLM-generated reasoning per section
4. **FOL Verifier** (First-Order Logic) — formal consistency check against rubric axioms
5. **SQLite** persistence + analytics

All LLM inference is powered by **Ollama** running `gpt-oss-20b` locally.

---

## Directory Structure

```
backend/
├── app.py                   # Flask app factory + dev server entry point
├── config.py                # All configuration (env-var overrideable)
├── requirements.txt         # Python dependencies
│
├── models/
│   ├── roberta_model.py     # RoBERTa wrapper (inference + attention rollout)
│   └── ollama_client.py     # Ollama REST API client
│
├── agents/
│   ├── base_agent.py        # Abstract SRLM agent base class
│   ├── specialized_agents.py # 6 specialist agents (Abstract, Methodology, etc.)
│   ├── master_arbiter.py    # Master Arbiter (LLM-as-Judge synthesis)
│   └── orchestrator.py      # Full pipeline orchestrator
│
├── xai/
│   ├── explainer.py         # XAI explanations (per-section reasoning + evidence)
│   └── fol_verifier.py      # FOL axiom verification
│
├── storage/
│   └── db.py                # SQLite persistence layer
│
├── utils/
│   ├── report_parser.py     # Regex-based structured report parser
│   └── text_processor.py    # File reading (txt/pdf/docx) + normalisation
│
├── routes/
│   ├── evaluate.py          # POST /api/evaluate/*
│   ├── reports.py           # GET/DELETE /api/reports/*
│   ├── analytics.py         # GET /api/analytics/*
│   └── health.py            # GET /api/health/*
│
└── uploads/                 # Uploaded files (auto-created)
```

---

## Running the Server

```bash
# From the project root (devsecops/)
cd backend
pip install -r requirements.txt

# Start (Ollama must be running separately)
python app.py
# or
flask --app backend.app run --port 5000
```

Server starts at `http://localhost:5000`. Model loading happens in the background (~30–60s). During loading, evaluate routes return 503.

**Required: Ollama running with gpt-oss-20b**
```bash
ollama serve          # start Ollama
ollama run llama3:latest  # pull/run the model
```

---

## Configuration (config.py / environment variables)

| Variable | Default | Description |
|---|---|---|
| `WORKSPACE_PATH` | `../` (project root) | Where to find `checkpoint-*` directories |
| `CHECKPOINT_PATH` | auto-discover | Override checkpoint path |
| `TOKENIZER_NAME` | `roberta-base` | Tokenizer fallback |
| `MAX_LENGTH` | `512` | Tokenizer max sequence length |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `gpt-oss-20b` | Model name |
| `OLLAMA_TIMEOUT` | `180` | Request timeout (seconds) |
| `DB_PATH` | `backend/storage/reports.db` | SQLite database path |
| `SRLM_ROUNDS` | `2` | Number of SRLM review rounds |
| `DEBUG` | `true` | Flask debug mode |

---

## API Reference

### Base URL: `http://localhost:5000`

---

### Evaluation

#### `POST /api/evaluate/text`
Evaluate a report submitted as JSON text.

**Request Body:**
```json
{
  "text": "Academic Report Evaluation Summary\nDomain: Cybersecurity\n...",
  "filename": "my_report.txt",
  "run_srlm": true,
  "run_highlights": true,
  "run_fol": true,
  "run_xai": true
}
```

**Response 200:**
```json
{
  "report_id": "a1b2c3d4",
  "filename": "my_report.txt",
  "elapsed_ms": 12340,
  "status": "complete",

  "parsed_data": {
    "domain": "Cybersecurity",
    "total_score": 18.0,
    "max_score": 20.0,
    "word_count": 450,
    "sections": [
      {"name": "abstract", "score": 2.0, "max_score": 2.0, "feedback": "..."},
      {"name": "methodology", "score": 1.0, "max_score": 2.0, "feedback": "..."}
    ],
    "document_quality": {
      "section_structure": 1.0, "font_consistency": 1.0, "line_spacing": 1.0,
      "figures_tables": 1.0, "blank_pages": 1.0, "citations": 1.0,
      "page_numbers": 0.0, "total": 6.0, "max_total": 7.0
    },
    "has_abstract": true, "has_methodology": true,
    "has_results": true, "has_conclusion": true,
    "reference_count": 5
  },

  "roberta_result": {
    "predicted_label_id": 0,
    "predicted_label": "Needs Improvement",
    "confidence": 0.9996,
    "probabilities": {
      "Needs Improvement": 0.9996,
      "Good": 0.0002,
      "Excellent": 0.0002
    }
  },

  "unified_verdict": {
    "final_verdict": "Needs Improvement",
    "overall_score": 72.5,
    "confidence": 0.87,
    "executive_summary": "...",
    "dimension_verdicts": {
      "abstract": "Good",
      "methodology": "Needs Improvement",
      "results": "Good",
      "citations": "Excellent",
      "document_structure": "Good",
      "content_depth": "Needs Improvement"
    },
    "key_strengths": ["Strong literature review", "Good abstract"],
    "key_weaknesses": ["Methodology lacks detail", "Missing page numbers"],
    "priority_recommendations": ["Expand methodology section", "Add page numbers"],
    "agent_agreement_level": "Strong",
    "ml_model_alignment": "Aligned",
    "reasoning_chain": "..."
  },

  "agent_evaluations": [
    {
      "agent": "AbstractAgent",
      "round": 1,
      "verdict": "Good",
      "score": 7.5,
      "max_score": 10,
      "reasoning": "...",
      "evidence": ["quote from report"],
      "strengths": [...],
      "weaknesses": [...],
      "recommendations": [...],
      "self_reward": {"score": 8.0, "justification": "...", "weaknesses": [...]}
    }
  ],

  "self_reward_scores": {
    "AbstractAgent": 8.0,
    "MethodologyAgent": 7.5
  },

  "cross_reviews": [
    {
      "reviewer": "AbstractAgent",
      "reviewee": "MethodologyAgent",
      "agree_with_peer": true,
      "revised_verdict": "Needs Improvement",
      "confidence_change": 0.05,
      "reasoning": "..."
    }
  ],

  "highlight_data": {
    "highlighted_spans": [
      {"token": "methodology", "start": 245, "end": 256, "score": 0.95}
    ],
    "threshold": 0.72,
    "total_tokens": 312
  },

  "xai_result": {
    "model_explanation": {
      "predicted_label": "Needs Improvement",
      "confidence": 0.9996,
      "plain_english_reasoning": "...",
      "key_signals": [{"signal": "...", "impact": "negative", "explanation": "..."}],
      "attention_summary": "..."
    },
    "section_explanations": {
      "methodology": {
        "section": "methodology",
        "score": 1.0,
        "max_score": 2.0,
        "verdict": "Needs Improvement",
        "reasoning": "...",
        "met_criteria": [...],
        "unmet_criteria": [...],
        "key_text_evidence": [{"text": "...", "interpretation": "..."}],
        "specific_improvements": [...]
      }
    },
    "highlighted_evidence": [...],
    "decision_factors": [
      {"factor": "...", "direction": "negative", "weight": 0.85, "evidence": "...", "impact_on_verdict": "..."}
    ],
    "counterfactuals": [
      {"scenario": "...", "current_state": "...", "required_change": "...", "difficulty": "Medium", "would_achieve": "Good"}
    ],
    "improvement_roadmap": [
      {"priority": 1, "section": "methodology", "current_score": "1/2", "potential_gain": 1.0, "actions": [...], "effort": "Medium"}
    ]
  },

  "fol_result": {
    "verdict": "Needs Improvement",
    "consistent": true,
    "consistency_score": 0.875,
    "fol_statements": [
      "NeedsImprovementReport(r)",
      "TotalScore(r) = 18/20 (90.00%)",
      "HasSection(r, abstract)",
      "¬HasSection(r, methodology)"
    ],
    "satisfied_rules": ["A3: Needs Improvement score threshold"],
    "violated_rules": [],
    "verification_details": [
      {
        "rule_id": "A3",
        "formal": "∀r: NeedsImprovement(r) → ¬ScoreGTE(r, 0.70)",
        "natural_language": "Needs Improvement implies score < 70%",
        "satisfied": true,
        "actual_value": "90.00%",
        "expected": "< 70%",
        "explanation": "...",
        "verdict_impact": "contradicts"
      }
    ],
    "explanation": "..."
  },

  "thought_process": [
    {"step": 1, "title": "Text Extraction & Preprocessing", "description": "...", "evidence": [], "type": "preprocessing"},
    {"step": 2, "title": "RoBERTa Sequence Classification", "description": "...", "type": "ml_inference"},
    {"step": 3, "title": "Attention-Based Text Highlighting", "description": "...", "type": "xai"},
    {"step": 4, "title": "Agent: AbstractAgent — Round 1 Evaluation", "description": "...", "type": "agent_evaluation"},
    {"step": 9, "title": "SRLM Cross-Review Phase", "description": "...", "type": "srlm_cross_review"},
    {"step": 10, "title": "Master Arbiter — Unified Verdict", "description": "...", "type": "master_arbitration"},
    {"step": 11, "title": "FOL Consistency Verification", "description": "...", "type": "fol_verification"}
  ],

  "pipeline_timeline": [
    {"name": "start", "elapsed_ms": 0},
    {"name": "roberta_inference", "elapsed_ms": 450, "data": {...}},
    {"name": "complete", "elapsed_ms": 12340}
  ]
}
```

---

#### `POST /api/evaluate/upload`
Evaluate a report uploaded as a file.

**Request:** `multipart/form-data`
- `file` (required): `.txt`, `.md`, `.log`, `.pdf`, `.docx`
- `run_srlm` (optional): `"true"` / `"false"` (default `"true"`)
- `run_highlights` (optional): `"true"` / `"false"`
- `run_fol` (optional): `"true"` / `"false"`
- `run_xai` (optional): `"true"` / `"false"`

**Response 200:** Same as `/api/evaluate/text`

---

### Reports

#### `GET /api/reports`
List all reports (paginated).

**Query params:** `domain`, `label`, `limit` (default 50), `offset` (default 0)

**Response 200:**
```json
{
  "reports": [
    {
      "id": "a1b2c3d4",
      "filename": "report.txt",
      "submitted_at": "2026-04-08T12:00:00",
      "predicted_label": "Needs Improvement",
      "confidence": 0.9996,
      "domain": "Cybersecurity",
      "total_score": 18.0,
      "max_score": 20.0,
      "status": "complete",
      "unified_verdict": {...}
    }
  ],
  "total": 42,
  "limit": 50,
  "offset": 0
}
```

#### `GET /api/reports/<id>`
Get full report. Add `?include_text=true` to include raw report text.

#### `DELETE /api/reports/<id>`
Delete a report and all its agent evaluations.

#### `GET /api/reports/<id>/highlights`
```json
{
  "report_id": "a1b2c3d4",
  "predicted_label": "Needs Improvement",
  "highlighted_spans": [{"token": "methodology", "start": 245, "end": 256, "score": 0.95}],
  "threshold": 0.72,
  "total_tokens": 312,
  "mapped_evidence": [{"token": "...", "importance_score": 0.95, "context": "...", "assigned_section": "methodology"}]
}
```

#### `GET /api/reports/<id>/thought-process`
```json
{"report_id": "...", "steps": [...], "total_steps": 11}
```

#### `GET /api/reports/<id>/fol`
Full FOL verification result (see fol_result above).

#### `GET /api/reports/<id>/agents`
```json
{
  "report_id": "...",
  "agent_evaluations": [...],
  "self_reward_scores": {...},
  "cross_reviews": [...],
  "unified_verdict": {...}
}
```

#### `GET /api/reports/<id>/xai`
Full XAI explanation (see xai_result above).

#### `GET /api/reports/<id>/full-text`
```json
{"report_id": "...", "text": "...", "word_count": 450, "char_count": 2100}
```

---

### Analytics

#### `GET /api/analytics/overview`
```json
{
  "total_reports": 42,
  "avg_confidence": 0.9876,
  "by_label": [{"predicted_label": "Needs Improvement", "count": 35, "avg_confidence": 0.999}],
  "by_domain": [{"domain": "Cybersecurity", "count": 20, "avg_score": 17.5}],
  "recent_reports": [...]
}
```

#### `GET /api/analytics/score-distribution?bins=10`
Histogram of score percentages.

#### `GET /api/analytics/confidence-trends`
Daily average confidence over time.

#### `GET /api/analytics/label-distribution`
```json
{
  "distribution": [{"label": "Needs Improvement", "count": 35, "percentage": 83.3}],
  "total": 42
}
```

#### `GET /api/analytics/domain-breakdown`
Per-domain stats.

#### `GET /api/analytics/model-performance`
Checkpoint training metrics (eval_accuracy, eval_f1 from trainer_state.json).

#### `GET /api/analytics/agent-scores`
Per-agent SRLM self-reward score averages.

---

### Health

#### `GET /api/health`
```json
{
  "status": "healthy",
  "components": {
    "model": {"status": "ok", "checkpoint": "...", "device": "cpu"},
    "ollama": {"status": "ok", "model": "gpt-oss-20b", "reachable": true},
    "db": {"status": "ok", "total_reports": 42}
  }
}
```

#### `GET /api/health/model` — RoBERTa model status
#### `GET /api/health/ollama` — Ollama connectivity
#### `GET /api/health/db` — Database connectivity

---

## Pipeline Architecture

```
Input (text / file)
        │
        ▼
┌─────────────────────┐
│   Report Parser     │  → Extracts: domain, total_score, section_scores,
│  (report_parser.py) │    doc_quality, reference_count, structural_flags
└─────────────────────┘
        │
        ▼
┌─────────────────────┐
│   RoBERTa Model     │  → Label (Needs Improvement / Good / Excellent)
│  (roberta_model.py) │    + Confidence + Probabilities
│                     │  → Attention Rollout → Token Importance Scores
└─────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                 SRLM Multi-Agent Panel                          │
│                                                                 │
│  Round 1 (Independent):                                         │
│    AbstractAgent     → evaluates abstract quality               │
│    MethodologyAgent  → evaluates research methodology           │
│    ResultsAgent      → evaluates results & analysis             │
│    CitationAgent     → evaluates literature & citations         │
│    DocumentStructure → evaluates formatting & structure         │
│    ContentDepth      → evaluates academic rigor & novelty       │
│                                                                 │
│  Self-Reward (SRLM):                                            │
│    Each agent scores its own evaluation quality (1-10)          │
│                                                                 │
│  Round 2 (Cross-Review):                                        │
│    Each agent reviews its peer's evaluation                     │
│    Agents may revise their verdicts                             │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────┐
│   Master Arbiter    │  → Weighted synthesis of all agent verdicts
│  (master_arbiter.py)│    (weighted by self-reward quality scores)
│                     │  → Final unified verdict + reasoning chain
└─────────────────────┘
        │
        ├───────────────────────────────────┐
        ▼                                   ▼
┌─────────────────────┐         ┌─────────────────────┐
│   FOL Verifier      │         │   XAI Explainer     │
│  (fol_verifier.py)  │         │  (explainer.py)     │
│                     │         │                     │
│ 10 FOL axioms:      │         │ - Model explanation │
│ A1: Excellent→≥90%  │         │ - Per-section       │
│ A2: Good→≥70%       │         │   reasoning         │
│ A3: NI→<70%         │         │ - Decision factors  │
│ A4: Excellent→      │         │ - Counterfactuals   │
│     all sections    │         │ - Improvement       │
│ A5-A6: Structural   │         │   roadmap           │
│ A7: DocQuality≥85%  │         │                     │
│ A8: Refs≥3          │         │                     │
│ A9: SectionScore≥60%│         │                     │
│ A10: Good→abstract  │         │                     │
└─────────────────────┘         └─────────────────────┘
        │                                   │
        └───────────────────┬───────────────┘
                            ▼
                  ┌─────────────────────┐
                  │   SQLite Database   │
                  │  (reports.db)       │
                  │                     │
                  │  tables:            │
                  │  - reports          │
                  │  - agent_evaluations│
                  │  - analytics_cache  │
                  └─────────────────────┘
```

---

## SRLM Research Background

This implementation is inspired by several key papers:

| Technique | Paper | How Used |
|---|---|---|
| **Self-Rewarding LMs** | Yuan et al. (2024) arXiv:2401.10020 | Each agent scores its own evaluation quality; quality score used for weighting |
| **LLM-as-Judge** | Zheng et al. (2023) arXiv:2306.05685 | Master Arbiter synthesises agent verdicts |
| **Multi-Agent Debate** | Du et al. (2023) arXiv:2305.14325 | Cross-review round where agents challenge each other |
| **ReAct** | Yao et al. (2022) arXiv:2210.03629 | Step-by-step reasoning chain generation |
| **Attention Rollout** | Abnar & Zuidema (2020) arXiv:2005.00928 | Layer-wise attention aggregation for text highlighting |
| **LIME** | Ribeiro et al. (2016) KDD | Inspiration for local feature importance mapping |
| **FOL Verification** | Russell & Norvig, AIMA Ch. 8 | Formal logic consistency checking |

---

## Database Schema

```sql
reports (
    id              TEXT PRIMARY KEY,   -- 8-char UUID prefix
    filename        TEXT,
    submitted_at    TEXT,               -- ISO 8601
    report_text     TEXT,
    parsed_data     TEXT (JSON),        -- structured extraction
    predicted_label_id  INTEGER,
    predicted_label     TEXT,
    confidence          REAL,
    probabilities       TEXT (JSON),
    srlm_results        TEXT (JSON),    -- {agent_evaluations, self_reward_scores, cross_reviews}
    unified_verdict     TEXT (JSON),    -- master arbiter output
    thought_process     TEXT (JSON),    -- list of reasoning steps
    highlights          TEXT (JSON),    -- attention rollout data
    explanations        TEXT (JSON),    -- XAI output
    fol_statements      TEXT (JSON),    -- FOL axiom statements
    fol_verification    TEXT (JSON),    -- FOL check results
    domain              TEXT,
    total_score         REAL,
    max_score           REAL,
    status              TEXT            -- pending | complete | error
)

agent_evaluations (
    id              INTEGER PRIMARY KEY,
    report_id       TEXT → reports(id),
    agent_name      TEXT,
    round_num       INTEGER,
    evaluation      TEXT (JSON),
    self_reward_score REAL,
    timestamp       TEXT
)

analytics_cache (
    cache_key   TEXT PRIMARY KEY,
    value       TEXT (JSON),
    updated_at  TEXT
)
```

---

## Error Responses

All errors return JSON:
```json
{"error": "Human-readable message", "detail": "Optional technical detail"}
```

| Code | Meaning |
|---|---|
| 400 | Bad request (missing required field) |
| 404 | Report not found |
| 413 | File/text too large (> 16 MB) |
| 415 | Unsupported file type |
| 500 | Internal server error |
| 503 | Model still loading (retry after ~60s) |

---

## Frontend Integration Notes

- **Polling**: For very large reports or Ollama being slow, consider polling `/api/health` until `status: "healthy"` before first evaluate call.
- **Streaming**: The `/api/evaluate/*` endpoints are synchronous. A future enhancement could use SSE (Server-Sent Events) to stream thought-process steps as they complete.
- **Highlights**: Use `highlighted_spans` (start/end char offsets into the normalized text) to render coloured highlights in the report viewer. The `score` field (0–1) maps to highlight intensity.
- **FOL UI**: `verification_details[*].satisfied` → green/red badge per axiom. `consistent: true` → overall green banner.
- **Thought Process**: Render `thought_process` as a stepper/timeline component. Each step has a `type` field for icon selection.
- **Improvement Roadmap**: Render `xai_result.improvement_roadmap` as a prioritised action list.
