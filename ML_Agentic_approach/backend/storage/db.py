"""
SQLite-backed persistence layer.
All reports, agent evaluations, and analytics cache live here.
"""
import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def _dict_factory(cursor, row):
    return {col[0]: val for col, val in zip(cursor.description, row)}


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _conn(self):
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = _dict_factory
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_schema(self):
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS reports (
                    id              TEXT PRIMARY KEY,
                    filename        TEXT,
                    submitted_at    TEXT NOT NULL,
                    report_text     TEXT NOT NULL,
                    parsed_data     TEXT,           -- JSON

                    -- RoBERTa
                    predicted_label_id  INTEGER,
                    predicted_label     TEXT,
                    confidence          REAL,
                    probabilities       TEXT,        -- JSON

                    -- SRLM / agentic
                    srlm_results        TEXT,        -- JSON
                    unified_verdict     TEXT,
                    thought_process     TEXT,        -- JSON list of steps

                    -- XAI
                    highlights          TEXT,        -- JSON
                    explanations        TEXT,        -- JSON

                    -- FOL
                    fol_statements      TEXT,        -- JSON
                    fol_verification    TEXT,        -- JSON

                    -- Metadata for analytics
                    domain              TEXT,
                    total_score         REAL,
                    max_score           REAL,
                    status              TEXT DEFAULT 'pending'
                );

                CREATE TABLE IF NOT EXISTS agent_evaluations (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id       TEXT NOT NULL,
                    agent_name      TEXT NOT NULL,
                    round_num       INTEGER NOT NULL,
                    evaluation      TEXT,            -- JSON
                    self_reward_score REAL,
                    timestamp       TEXT NOT NULL,
                    FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS analytics_cache (
                    cache_key   TEXT PRIMARY KEY,
                    value       TEXT,                -- JSON
                    updated_at  TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_reports_domain ON reports(domain);
                CREATE INDEX IF NOT EXISTS idx_reports_label  ON reports(predicted_label);
                CREATE INDEX IF NOT EXISTS idx_reports_submitted ON reports(submitted_at);
                CREATE INDEX IF NOT EXISTS idx_agent_eval_report ON agent_evaluations(report_id);
                """
            )

    # ── Reports ──────────────────────────────────────────────────────────────

    def create_report(self, filename: str, report_text: str) -> str:
        report_id = str(uuid.uuid4())[:8]
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO reports (id, filename, submitted_at, report_text, status)
                VALUES (?, ?, ?, ?, 'pending')
                """,
                (report_id, filename, datetime.utcnow().isoformat(), report_text),
            )
        return report_id

    def update_report(self, report_id: str, fields: Dict[str, Any]):
        """Partial update — only set provided fields."""
        json_fields = {
            "parsed_data", "probabilities", "srlm_results", "thought_process",
            "highlights", "explanations", "fol_statements", "fol_verification",
            "unified_verdict",
        }
        set_clauses, values = [], []
        for k, v in fields.items():
            set_clauses.append(f"{k} = ?")
            values.append(json.dumps(v) if k in json_fields and not isinstance(v, str) else v)
        values.append(report_id)
        sql = f"UPDATE reports SET {', '.join(set_clauses)} WHERE id = ?"
        with self._conn() as conn:
            conn.execute(sql, values)

    def get_report(self, report_id: str) -> Optional[Dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM reports WHERE id = ?", (report_id,)
            ).fetchone()
        if row:
            return self._deserialize_report(row)
        return None

    def list_reports(
        self,
        domain: Optional[str] = None,
        label: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict]:
        conditions, params = [], []
        if domain:
            conditions.append("domain = ?")
            params.append(domain)
        if label:
            conditions.append("predicted_label = ?")
            params.append(label)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params += [limit, offset]
        with self._conn() as conn:
            rows = conn.execute(
                f"""
                SELECT id, filename, submitted_at, predicted_label, confidence,
                       domain, total_score, max_score, status, unified_verdict
                FROM reports {where}
                ORDER BY submitted_at DESC
                LIMIT ? OFFSET ?
                """,
                params,
            ).fetchall()
        return rows

    def delete_report(self, report_id: str) -> bool:
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM reports WHERE id = ?", (report_id,))
        return cur.rowcount > 0

    def count_reports(self) -> int:
        with self._conn() as conn:
            return conn.execute("SELECT COUNT(*) as n FROM reports").fetchone()["n"]

    def _deserialize_report(self, row: Dict) -> Dict:
        json_fields = {
            "parsed_data", "probabilities", "srlm_results", "thought_process",
            "highlights", "explanations", "fol_statements", "fol_verification",
            "unified_verdict",
        }
        for f in json_fields:
            if row.get(f) and isinstance(row[f], str):
                try:
                    row[f] = json.loads(row[f])
                except Exception:
                    pass
        return row

    # ── Agent evaluations ────────────────────────────────────────────────────

    def save_agent_evaluation(
        self,
        report_id: str,
        agent_name: str,
        round_num: int,
        evaluation: Dict,
        self_reward_score: float,
    ):
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO agent_evaluations
                    (report_id, agent_name, round_num, evaluation, self_reward_score, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    report_id,
                    agent_name,
                    round_num,
                    json.dumps(evaluation),
                    self_reward_score,
                    datetime.utcnow().isoformat(),
                ),
            )

    def get_agent_evaluations(self, report_id: str) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM agent_evaluations WHERE report_id = ? ORDER BY round_num, agent_name",
                (report_id,),
            ).fetchall()
        for r in rows:
            if r.get("evaluation") and isinstance(r["evaluation"], str):
                try:
                    r["evaluation"] = json.loads(r["evaluation"])
                except Exception:
                    pass
        return rows

    # ── Analytics ────────────────────────────────────────────────────────────

    def get_analytics_overview(self) -> Dict:
        with self._conn() as conn:
            total = conn.execute("SELECT COUNT(*) as n FROM reports").fetchone()["n"]
            by_label = conn.execute(
                """
                SELECT predicted_label, COUNT(*) as count, AVG(confidence) as avg_confidence
                FROM reports WHERE predicted_label IS NOT NULL
                GROUP BY predicted_label
                """
            ).fetchall()
            by_domain = conn.execute(
                """
                SELECT domain, COUNT(*) as count, AVG(total_score) as avg_score
                FROM reports WHERE domain IS NOT NULL
                GROUP BY domain ORDER BY count DESC
                """
            ).fetchall()
            avg_confidence = conn.execute(
                "SELECT AVG(confidence) as v FROM reports WHERE confidence IS NOT NULL"
            ).fetchone()["v"]
            recent = conn.execute(
                """
                SELECT submitted_at, predicted_label, confidence, domain, total_score
                FROM reports ORDER BY submitted_at DESC LIMIT 10
                """
            ).fetchall()
        return {
            "total_reports": total,
            "avg_confidence": avg_confidence,
            "by_label": by_label,
            "by_domain": by_domain,
            "recent_reports": recent,
        }

    def get_score_distribution(self) -> List[Dict]:
        with self._conn() as conn:
            return conn.execute(
                """
                SELECT total_score, max_score, predicted_label, domain
                FROM reports WHERE total_score IS NOT NULL
                ORDER BY submitted_at DESC
                """
            ).fetchall()

    def get_confidence_trends(self) -> List[Dict]:
        with self._conn() as conn:
            return conn.execute(
                """
                SELECT DATE(submitted_at) as date,
                       AVG(confidence) as avg_confidence,
                       COUNT(*) as count
                FROM reports WHERE confidence IS NOT NULL
                GROUP BY DATE(submitted_at)
                ORDER BY date ASC
                """
            ).fetchall()

    def set_cache(self, key: str, value: Any):
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO analytics_cache (cache_key, value, updated_at) VALUES (?, ?, ?)",
                (key, json.dumps(value), datetime.utcnow().isoformat()),
            )

    def get_cache(self, key: str) -> Optional[Any]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT value FROM analytics_cache WHERE cache_key = ?", (key,)
            ).fetchone()
        if row:
            try:
                return json.loads(row["value"])
            except Exception:
                return None
        return None
