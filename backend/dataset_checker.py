"""
Dataset Checker — Analyzes query result datasets for quality issues.

Performs automated QA on data returned from SQL queries:
  - Missing/null value detection
  - Type consistency checks
  - Outlier detection (IQR-based)
  - Empty result flagging
  - Duplicate row detection
"""

from typing import Any


# ─── Issue Severity Levels ─────────────────────────────────────────────────────

SEVERITY_INFO = "info"
SEVERITY_WARNING = "warning"
SEVERITY_ERROR = "error"


def _make_issue(severity: str, category: str, message: str, details: Any = None) -> dict:
    """Create a standardized issue report."""
    issue = {
        "severity": severity,
        "category": category,
        "message": message,
    }
    if details is not None:
        issue["details"] = details
    return issue


# ─── Individual Checks ─────────────────────────────────────────────────────────

def check_empty_results(data: dict) -> list[dict]:
    """Flag if the query returned zero rows."""
    issues = []
    if data.get("row_count", 0) == 0:
        issues.append(_make_issue(
            SEVERITY_WARNING,
            "empty_results",
            "Query returned 0 rows. The filter criteria may be too restrictive.",
        ))
    return issues


def check_null_values(data: dict) -> list[dict]:
    """Detect columns with NULL/None values and calculate null percentages."""
    issues = []
    rows = data.get("rows", [])
    columns = data.get("columns", [])

    if not rows or not columns:
        return issues

    total = len(rows)
    for col in columns:
        null_count = sum(1 for row in rows if row.get(col) is None)
        if null_count > 0:
            pct = round((null_count / total) * 100, 1)
            severity = SEVERITY_ERROR if pct > 50 else SEVERITY_WARNING
            issues.append(_make_issue(
                severity,
                "null_values",
                f"Column '{col}' has {null_count}/{total} NULL values ({pct}%).",
                {"column": col, "null_count": null_count, "null_pct": pct}
            ))

    return issues


def check_type_consistency(data: dict) -> list[dict]:
    """Detect columns with mixed data types."""
    issues = []
    rows = data.get("rows", [])
    columns = data.get("columns", [])

    if not rows or not columns:
        return issues

    for col in columns:
        types_seen = set()
        for row in rows:
            val = row.get(col)
            if val is not None:
                types_seen.add(type(val).__name__)

        if len(types_seen) > 1:
            issues.append(_make_issue(
                SEVERITY_WARNING,
                "type_mismatch",
                f"Column '{col}' has mixed types: {', '.join(sorted(types_seen))}.",
                {"column": col, "types": sorted(types_seen)}
            ))

    return issues


def check_outliers(data: dict) -> list[dict]:
    """
    Detect outliers in numeric columns using the IQR method.
    An outlier is defined as a value below Q1 - 1.5*IQR or above Q3 + 1.5*IQR.
    """
    issues = []
    rows = data.get("rows", [])
    columns = data.get("columns", [])

    if len(rows) < 4:  # Need minimum data for meaningful IQR
        return issues

    for col in columns:
        # Collect numeric values
        values = []
        for row in rows:
            val = row.get(col)
            if isinstance(val, (int, float)):
                values.append(val)

        if len(values) < 4:
            continue

        # Calculate IQR
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        q1 = sorted_vals[n // 4]
        q3 = sorted_vals[(3 * n) // 4]
        iqr = q3 - q1

        if iqr == 0:
            continue  # All values in the middle 50% are the same

        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        outliers = [v for v in values if v < lower_bound or v > upper_bound]

        if outliers:
            issues.append(_make_issue(
                SEVERITY_INFO,
                "outliers",
                f"Column '{col}' has {len(outliers)} potential outlier(s) "
                f"(IQR bounds: [{lower_bound:.2f}, {upper_bound:.2f}]).",
                {
                    "column": col,
                    "outlier_count": len(outliers),
                    "outlier_values": outliers[:10],  # Limit to first 10
                    "lower_bound": round(lower_bound, 2),
                    "upper_bound": round(upper_bound, 2),
                }
            ))

    return issues


def check_duplicates(data: dict) -> list[dict]:
    """Detect duplicate rows in the dataset."""
    issues = []
    rows = data.get("rows", [])

    if len(rows) < 2:
        return issues

    # Convert rows to hashable tuples for comparison
    seen = set()
    duplicate_count = 0
    for row in rows:
        # Create a hashable representation
        row_tuple = tuple(sorted(row.items()))
        if row_tuple in seen:
            duplicate_count += 1
        else:
            seen.add(row_tuple)

    if duplicate_count > 0:
        issues.append(_make_issue(
            SEVERITY_WARNING,
            "duplicates",
            f"Dataset contains {duplicate_count} duplicate row(s).",
            {"duplicate_count": duplicate_count}
        ))

    return issues


# ─── Full Dataset Analysis ─────────────────────────────────────────────────────

def analyze_dataset(data: dict) -> dict:
    """
    Run all QA checks on a dataset and return a comprehensive report.

    Args:
        data: Dict with 'columns', 'rows', 'row_count' keys (from sql_engine).

    Returns:
        A report dict with summary stats and issues list.
    """
    all_issues = []

    # Run all checks
    all_issues.extend(check_empty_results(data))
    all_issues.extend(check_null_values(data))
    all_issues.extend(check_type_consistency(data))
    all_issues.extend(check_outliers(data))
    all_issues.extend(check_duplicates(data))

    # Summarize
    error_count = sum(1 for i in all_issues if i["severity"] == SEVERITY_ERROR)
    warning_count = sum(1 for i in all_issues if i["severity"] == SEVERITY_WARNING)
    info_count = sum(1 for i in all_issues if i["severity"] == SEVERITY_INFO)

    # Overall quality score
    total_checks = 5  # Number of check categories
    failed_checks = len(set(i["category"] for i in all_issues if i["severity"] in (SEVERITY_ERROR, SEVERITY_WARNING)))
    quality_score = round(((total_checks - failed_checks) / total_checks) * 100, 1)

    return {
        "summary": {
            "total_rows": data.get("row_count", 0),
            "total_columns": len(data.get("columns", [])),
            "total_issues": len(all_issues),
            "errors": error_count,
            "warnings": warning_count,
            "info": info_count,
            "quality_score": quality_score,
        },
        "issues": all_issues,
    }
