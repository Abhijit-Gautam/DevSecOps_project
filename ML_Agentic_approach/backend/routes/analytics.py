"""
Analytics routes — dashboard data for the frontend.

GET /api/analytics/overview          — summary stats
GET /api/analytics/score-distribution — histogram of total scores
GET /api/analytics/confidence-trends  — confidence over time
GET /api/analytics/label-distribution — pie chart data
GET /api/analytics/domain-breakdown   — per-domain stats
GET /api/analytics/model-performance  — checkpoint/model metrics
"""
from __future__ import annotations

import json
import logging
from collections import Counter
from typing import Any, Dict, List

from flask import Blueprint, current_app, jsonify, request

logger = logging.getLogger(__name__)
analytics_bp = Blueprint("analytics", __name__)


def _db():
    db = current_app.config.get("_db")
    if db is None:
        from flask import abort
        abort(503, "Database not yet initialised.")
    return db


@analytics_bp.route("/overview", methods=["GET"])
def overview():
    """
    Overall dashboard statistics.

    Response 200:
      {
        "total_reports": int,
        "avg_confidence": float,
        "by_label": [{predicted_label, count, avg_confidence}],
        "by_domain": [{domain, count, avg_score}],
        "recent_reports": [...]
      }
    """
    db = _db()
    data = db.get_analytics_overview()
    return jsonify(data)


@analytics_bp.route("/score-distribution", methods=["GET"])
def score_distribution():
    """
    Score distribution data for histograms.

    Query params:
      bins — number of histogram bins (default 10)

    Response 200:
      {
        "raw": [{total_score, max_score, predicted_label, domain}],
        "histogram": [{bucket_start, bucket_end, count, label_breakdown}],
        "percentages": [{score, max_score, percentage, predicted_label}]
      }
    """
    db = _db()
    raw = db.get_score_distribution()

    # Build percentage list
    percentages = []
    for row in raw:
        ts = row.get("total_score")
        ms = row.get("max_score")
        if ts is not None and ms and ms > 0:
            percentages.append({
                "total_score": ts,
                "max_score": ms,
                "percentage": round(ts / ms * 100, 1),
                "predicted_label": row.get("predicted_label"),
                "domain": row.get("domain"),
            })

    # Build histogram
    bins = int(request.args.get("bins", 10))
    histogram = _build_histogram([p["percentage"] for p in percentages], bins=bins, label_map={
        p["percentage"]: p["predicted_label"] for p in percentages
    })

    return jsonify({
        "raw": raw,
        "percentages": percentages,
        "histogram": histogram,
        "total": len(raw),
    })


@analytics_bp.route("/confidence-trends", methods=["GET"])
def confidence_trends():
    """
    Model confidence over time (per-day averages).

    Response 200:
      {
        "trends": [{date, avg_confidence, count}],
        "overall_avg": float
      }
    """
    db = _db()
    trends = db.get_confidence_trends()
    overall = sum(t["avg_confidence"] for t in trends) / len(trends) if trends else None
    return jsonify({
        "trends": trends,
        "overall_avg": round(overall, 4) if overall else None,
    })


@analytics_bp.route("/label-distribution", methods=["GET"])
def label_distribution():
    """
    Label distribution for pie/donut charts.

    Response 200:
      {
        "distribution": [{"label": str, "count": int, "percentage": float}],
        "total": int
      }
    """
    db = _db()
    overview_data = db.get_analytics_overview()
    by_label = overview_data.get("by_label", [])
    total = sum(row["count"] for row in by_label)

    distribution = [
        {
            "label": row["predicted_label"] or "Unknown",
            "count": row["count"],
            "percentage": round(row["count"] / total * 100, 1) if total else 0,
            "avg_confidence": round(row.get("avg_confidence") or 0, 4),
        }
        for row in by_label
    ]

    return jsonify({"distribution": distribution, "total": total})


@analytics_bp.route("/domain-breakdown", methods=["GET"])
def domain_breakdown():
    """
    Per-domain statistics.

    Response 200:
      {
        "domains": [{"domain", "count", "avg_score", "avg_score_pct"}]
      }
    """
    db = _db()
    overview_data = db.get_analytics_overview()
    by_domain = overview_data.get("by_domain", [])

    # Enrich with score percentage (assuming max_score=20 default)
    enriched = []
    for row in by_domain:
        avg_score = row.get("avg_score")
        enriched.append({
            "domain": row.get("domain") or "Unknown",
            "count": row.get("count", 0),
            "avg_score": avg_score,
            "avg_score_pct": round(avg_score / 20 * 100, 1) if avg_score else None,
        })

    return jsonify({"domains": enriched})


@analytics_bp.route("/model-performance", methods=["GET"])
def model_performance():
    """
    Checkpoint and model performance metrics (from trainer_state.json).

    Response 200:
      {
        "best_checkpoint": str,
        "eval_metrics": {...},
        "training_history": [...]
      }
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    try:
        from checkpoint_utils import discover_checkpoints, resolve_best_checkpoint
        workspace = Path(current_app.config.get("WORKSPACE_PATH", "."))
        checkpoints = discover_checkpoints(workspace)
        best = resolve_best_checkpoint(workspace)

        checkpoint_info = []
        for c in checkpoints:
            # Load trainer_state for log_history
            state_path = c.path / "trainer_state.json"
            log_history = []
            if state_path.exists():
                import json as _json
                with open(state_path) as f:
                    state = _json.load(f)
                log_history = state.get("log_history", [])

            checkpoint_info.append({
                "path": str(c.path),
                "name": c.path.name,
                "best_metric": c.best_metric,
                "global_step": c.global_step,
                "is_selected": c.path == best,
                "log_history": log_history,
            })

        return jsonify({
            "best_checkpoint": str(best),
            "checkpoints": checkpoint_info,
            "model_type": "RoBERTa-base (fine-tuned)",
            "num_labels": 3,
            "labels": {0: "Needs Improvement", 1: "Good", 2: "Excellent"},
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@analytics_bp.route("/agent-scores", methods=["GET"])
def agent_scores():
    """
    Aggregated agent self-reward scores across all reports.

    Response 200:
      {
        "by_agent": [{"agent_name", "avg_score", "count"}]
      }
    """
    db = _db()
    try:
        with db._conn() as conn:
            rows = conn.execute(
                """
                SELECT agent_name,
                       AVG(self_reward_score) as avg_score,
                       COUNT(*) as count,
                       MIN(self_reward_score) as min_score,
                       MAX(self_reward_score) as max_score
                FROM agent_evaluations
                GROUP BY agent_name
                ORDER BY avg_score DESC
                """
            ).fetchall()
        return jsonify({"by_agent": rows})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_histogram(
    values: List[float],
    bins: int = 10,
    label_map: Dict[float, str] = None,
) -> List[Dict]:
    """Build a histogram from a list of float values."""
    if not values:
        return []

    min_val, max_val = 0, 100
    bin_size = (max_val - min_val) / bins
    buckets: List[Dict] = []

    for i in range(bins):
        bucket_start = min_val + i * bin_size
        bucket_end = bucket_start + bin_size
        in_bucket = [v for v in values if bucket_start <= v < bucket_end]
        if i == bins - 1:
            in_bucket = [v for v in values if bucket_start <= v <= bucket_end]

        label_counter: Counter = Counter()
        if label_map:
            for v in in_bucket:
                lbl = label_map.get(v, "Unknown")
                label_counter[lbl] += 1

        buckets.append({
            "bucket_start": round(bucket_start, 1),
            "bucket_end": round(bucket_end, 1),
            "count": len(in_bucket),
            "label_breakdown": dict(label_counter),
        })

    return buckets
