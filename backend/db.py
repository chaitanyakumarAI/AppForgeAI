"""
AppForge AI — SQLite Database Layer
Stores run history, per-stage metrics, and evaluation results.
"""
import json
import sqlite3
import os
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "appforge.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS runs (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id          TEXT NOT NULL UNIQUE,
        prompt          TEXT NOT NULL,
        mode            TEXT NOT NULL,
        status          TEXT NOT NULL,          -- pending | success | failed | repaired
        total_latency_ms INTEGER,
        estimated_cost_usd REAL,
        repair_attempts INTEGER DEFAULT 0,
        created_at      TEXT NOT NULL,
        schema_json     TEXT,                   -- final output JSON
        metrics_json    TEXT                    -- per-stage metrics
    );

    CREATE TABLE IF NOT EXISTS stage_logs (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id      TEXT NOT NULL,
        stage       TEXT NOT NULL,
        status      TEXT NOT NULL,
        latency_ms  INTEGER,
        tokens_in   INTEGER,
        tokens_out  INTEGER,
        error       TEXT,
        created_at  TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS validation_errors (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id      TEXT NOT NULL,
        error_type  TEXT NOT NULL,
        layer       TEXT NOT NULL,
        message     TEXT NOT NULL,
        repaired    INTEGER DEFAULT 0,
        created_at  TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS eval_results (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        test_id         TEXT NOT NULL,
        test_type       TEXT NOT NULL,
        prompt          TEXT NOT NULL,
        status          TEXT NOT NULL,
        retries         INTEGER DEFAULT 0,
        latency_ms      INTEGER,
        failure_type    TEXT,
        created_at      TEXT NOT NULL
    );
    """)
    conn.commit()
    conn.close()


def save_run(run_id: str, prompt: str, mode: str, status: str,
             total_latency_ms: int, estimated_cost_usd: float,
             repair_attempts: int, schema_json: dict, metrics_json: dict):
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO runs
        (run_id, prompt, mode, status, total_latency_ms, estimated_cost_usd,
         repair_attempts, created_at, schema_json, metrics_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        run_id, prompt, mode, status, total_latency_ms, estimated_cost_usd,
        repair_attempts, datetime.now(timezone.utc).isoformat(),
        json.dumps(schema_json), json.dumps(metrics_json)
    ))
    conn.commit()
    conn.close()


def log_stage(run_id: str, stage: str, status: str, latency_ms: int,
              tokens_in: int = 0, tokens_out: int = 0, error: str = None):
    conn = get_conn()
    conn.execute("""
        INSERT INTO stage_logs (run_id, stage, status, latency_ms, tokens_in, tokens_out, error, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (run_id, stage, status, latency_ms, tokens_in, tokens_out, error,
          datetime.now(timezone.utc).isoformat()))
    conn.commit()
    conn.close()


def log_validation_error(run_id: str, error_type: str, layer: str,
                          message: str, repaired: bool = False):
    conn = get_conn()
    conn.execute("""
        INSERT INTO validation_errors (run_id, error_type, layer, message, repaired, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (run_id, error_type, layer, message, int(repaired),
          datetime.now(timezone.utc).isoformat()))
    conn.commit()
    conn.close()


def get_recent_runs(limit: int = 20):
    conn = get_conn()
    rows = conn.execute("""
        SELECT run_id, prompt, mode, status, total_latency_ms,
               estimated_cost_usd, repair_attempts, created_at
        FROM runs ORDER BY created_at DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_aggregate_metrics():
    conn = get_conn()
    row = conn.execute("""
        SELECT
            COUNT(*) as total_runs,
            SUM(CASE WHEN status='success' OR status='repaired' THEN 1 ELSE 0 END) as success_count,
            AVG(total_latency_ms) as avg_latency_ms,
            AVG(estimated_cost_usd) as avg_cost_usd,
            AVG(repair_attempts) as avg_retries,
            SUM(repair_attempts) as total_repairs
        FROM runs
    """).fetchone()
    conn.close()
    return dict(row) if row else {}


def save_eval_result(test_id: str, test_type: str, prompt: str, status: str,
                     retries: int, latency_ms: int, failure_type: str = None):
    conn = get_conn()
    conn.execute("""
        INSERT INTO eval_results
        (test_id, test_type, prompt, status, retries, latency_ms, failure_type, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (test_id, test_type, prompt, status, retries, latency_ms, failure_type,
          datetime.now(timezone.utc).isoformat()))
    conn.commit()
    conn.close()


def get_eval_summary():
    conn = get_conn()
    rows = conn.execute("""
        SELECT test_type, status, COUNT(*) as count, AVG(latency_ms) as avg_latency,
               AVG(retries) as avg_retries, failure_type
        FROM eval_results
        GROUP BY test_type, status, failure_type
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]
