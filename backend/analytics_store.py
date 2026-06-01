"""
Analytics Store — In-memory analytics tracking for pipeline runs.

Logs every pipeline execution and provides aggregation methods for
the analytics dashboard (valid %, error breakdown, function usage, etc.).
"""

from datetime import datetime, timezone
from collections import Counter
from typing import Optional


# ─── In-Memory Store ───────────────────────────────────────────────────────────

_pipeline_logs: list[dict] = []


# ─── Logging ───────────────────────────────────────────────────────────────────

def log_pipeline_run(
    function_name: str,
    input_text: Optional[str],
    validation_result: dict,
    execution_success: Optional[bool] = None,
    execution_error: Optional[str] = None,
    dataset_issues: Optional[list[dict]] = None,
    quality_score: Optional[float] = None,
) -> dict:
    """
    Log a pipeline run to the analytics store.
    Returns the logged entry.
    """
    entry = {
        "id": len(_pipeline_logs) + 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "function_name": function_name,
        "input_text": input_text,
        "validation_status": validation_result.get("status", "unknown"),
        "validation_checks": validation_result.get("checks", {}),
        "validation_errors": validation_result.get("errors", []),
        "execution_success": execution_success,
        "execution_error": execution_error,
        "dataset_issue_count": len(dataset_issues) if dataset_issues else 0,
        "quality_score": quality_score,
    }
    _pipeline_logs.append(entry)
    return entry


# ─── Aggregation Methods ──────────────────────────────────────────────────────

def get_analytics() -> dict:
    """
    Compute aggregated analytics from all logged pipeline runs.
    """
    if not _pipeline_logs:
        return {
            "total_runs": 0,
            "valid_pct": 0,
            "invalid_pct": 0,
            "warning_pct": 0,
            "error_breakdown": {},
            "function_usage": {},
            "sql_failure_rate": 0,
            "avg_quality_score": 0,
            "recent_runs": [],
            "validation_over_time": [],
        }

    total = len(_pipeline_logs)

    # Validation status breakdown
    status_counts = Counter(log["validation_status"] for log in _pipeline_logs)
    valid_count = status_counts.get("valid", 0)
    invalid_count = status_counts.get("invalid", 0)
    warning_count = status_counts.get("warning", 0)

    # Error type breakdown
    error_types = Counter()
    for log in _pipeline_logs:
        for error in log["validation_errors"]:
            # Categorize errors
            error_lower = error.lower()
            if "json" in error_lower:
                error_types["JSON Error"] += 1
            elif "schema" in error_lower or "missing required" in error_lower or "unknown function" in error_lower:
                error_types["Schema Error"] += 1
            elif "type mismatch" in error_lower:
                error_types["Type Error"] += 1
            elif "sql" in error_lower or "injection" in error_lower:
                error_types["SQL Error"] += 1
            else:
                error_types["Other Error"] += 1

    # Function usage
    function_usage = Counter(log["function_name"] for log in _pipeline_logs)

    # SQL failure rate
    sql_runs = [log for log in _pipeline_logs if log["execution_success"] is not None]
    sql_failures = sum(1 for log in sql_runs if not log["execution_success"])
    sql_failure_rate = round((sql_failures / len(sql_runs) * 100), 1) if sql_runs else 0

    # Average quality score
    quality_scores = [log["quality_score"] for log in _pipeline_logs if log["quality_score"] is not None]
    avg_quality = round(sum(quality_scores) / len(quality_scores), 1) if quality_scores else 0

    # Recent runs (last 20)
    recent = list(reversed(_pipeline_logs[-20:]))

    # Validation over time (last 50 entries, simplified)
    validation_timeline = []
    for log in _pipeline_logs[-50:]:
        validation_timeline.append({
            "id": log["id"],
            "status": log["validation_status"],
            "function": log["function_name"],
            "timestamp": log["timestamp"],
        })

    return {
        "total_runs": total,
        "valid_pct": round(valid_count / total * 100, 1),
        "invalid_pct": round(invalid_count / total * 100, 1),
        "warning_pct": round(warning_count / total * 100, 1),
        "error_breakdown": dict(error_types),
        "function_usage": dict(function_usage),
        "sql_failure_rate": sql_failure_rate,
        "avg_quality_score": avg_quality,
        "recent_runs": recent,
        "validation_over_time": validation_timeline,
    }


def get_run_count() -> int:
    """Return total number of logged runs."""
    return len(_pipeline_logs)


def clear_analytics():
    """Clear all analytics data. Useful for testing."""
    _pipeline_logs.clear()
