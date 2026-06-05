"""
AppForge AI — Evaluation Metrics Tracker
Runs evaluation suite and generates the metrics report.
"""
from __future__ import annotations
import json
import time
from pathlib import Path
from backend.evaluation.test_cases import ALL_TEST_CASES
import backend.db as db


RESULTS_PATH = Path(__file__).parent.parent.parent / "evaluation" / "results.json"


def score_schema_completeness(response: dict) -> float:
    """Scores how complete the output schema is (0.0 - 1.0)."""
    schema = response.get("schema", {})
    if not schema:
        return 0.0
    checks = [
        bool(schema.get("db_schema")),
        bool(schema.get("api_schema")),
        bool(schema.get("ui_schema")),
        bool(schema.get("auth_schema")),
        bool(schema.get("business_logic")),
        len(schema.get("db_schema", [])) >= 2,
        len(schema.get("api_schema", [])) >= 3,
        len(schema.get("ui_schema", [])) >= 2,
        bool(response.get("validation_report", {}).get("passed")),
        bool(response.get("execution_report", {}).get("executable")),
    ]
    return sum(checks) / len(checks)


def categorize_failure(error: str | None, response: dict) -> str:
    """Returns a failure category string."""
    if not error and response.get("status") == "success":
        return "none"
    if error and "json" in error.lower():
        return "invalid_json"
    if error and "key" in error.lower():
        return "missing_key"
    if error and "timeout" in error.lower():
        return "timeout"
    if response.get("status") == "repaired":
        return "repaired_with_warnings"
    if error:
        return "llm_error"
    return "unknown"


def run_evaluation(pipeline_fn, mode: str = "fast", max_cases: int = None) -> dict:
    """
    Runs evaluation on all (or subset of) test cases.
    pipeline_fn: synchronous wrapper around the pipeline for eval purposes.
    Returns summary metrics dict.
    """
    db.init_db()
    results = []
    cases = ALL_TEST_CASES[:max_cases] if max_cases else ALL_TEST_CASES

    for case in cases:
        t0 = time.time()
        status, retries, failure_type = "unknown", 0, "unknown"
        response = {}

        try:
            response = pipeline_fn(case["prompt"], mode=mode)
            status = response.get("status", "success")
            retries = response.get("metrics", {}).get("repair_attempts", 0) if response.get("metrics") else 0
            failure_type = categorize_failure(None, response)
        except Exception as e:
            status = "failed"
            failure_type = categorize_failure(str(e), {})

        latency = int((time.time() - t0) * 1000)

        result = {
            "test_id":    case["id"],
            "test_type":  case.get("category", "unknown"),
            "prompt":     case["prompt"][:100],
            "status":     status,
            "retries":    retries,
            "latency_ms": latency,
            "failure_type": failure_type,
            "completeness": score_schema_completeness(response),
        }
        results.append(result)
        db.save_eval_result(
            test_id=case["id"], test_type=case.get("category", "unknown"),
            prompt=case["prompt"][:200], status=status, retries=retries,
            latency_ms=latency, failure_type=failure_type
        )
        print(f"[EVAL] {case['id']} ({case.get('category')}) → {status} ({latency}ms)")

    # Aggregate
    total = len(results)
    success = sum(1 for r in results if r["status"] in ("success", "repaired"))
    by_category: dict[str, dict] = {}
    failure_types: dict[str, int] = {}

    for r in results:
        cat = r["test_type"]
        by_category.setdefault(cat, {"total": 0, "success": 0, "avg_latency": 0, "avg_retries": 0})
        by_category[cat]["total"] += 1
        if r["status"] in ("success", "repaired"):
            by_category[cat]["success"] += 1
        by_category[cat]["avg_latency"] += r["latency_ms"]
        by_category[cat]["avg_retries"] += r["retries"]
        failure_types[r["failure_type"]] = failure_types.get(r["failure_type"], 0) + 1

    for cat in by_category:
        n = by_category[cat]["total"]
        by_category[cat]["avg_latency"] = round(by_category[cat]["avg_latency"] / n)
        by_category[cat]["avg_retries"] = round(by_category[cat]["avg_retries"] / n, 2)
        by_category[cat]["success_rate"] = round(by_category[cat]["success"] / n, 2)

    summary = {
        "total_cases": total,
        "success_count": success,
        "success_rate": round(success / total, 3) if total else 0,
        "avg_latency_ms": round(sum(r["latency_ms"] for r in results) / total) if total else 0,
        "avg_retries": round(sum(r["retries"] for r in results) / total, 2) if total else 0,
        "avg_completeness": round(sum(r["completeness"] for r in results) / total, 3) if total else 0,
        "failure_types": failure_types,
        "by_category": by_category,
        "results": results,
    }

    RESULTS_PATH.parent.mkdir(exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(summary, indent=2))
    print(f"\n[EVAL] Results saved to {RESULTS_PATH}")
    print(f"[EVAL] Success rate: {summary['success_rate']*100:.1f}%  Avg latency: {summary['avg_latency_ms']}ms")
    return summary
