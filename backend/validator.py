"""
Validator Engine — The CORE feature of the system.

Performs multi-layer validation on function call JSON:
  1. JSON well-formedness
  2. Schema validation (function exists, required params, no unknown params)
  3. Data type validation (argument types match schema)
  4. SQL safety checks (injection detection, dangerous statements, syntax)
"""

import json
import re
from typing import Any, Union

import sqlparse

from backend.function_registry import (
    get_function_schema,
    get_function_names,
    get_required_params,
    get_optional_params,
    validate_param_type,
)


# ─── Validation Result Model ──────────────────────────────────────────────────

def _make_result(
    status: str,
    checks: dict,
    errors: list[str] | None = None,
    warnings: list[str] | None = None,
) -> dict:
    """Construct a standardized validation result."""
    return {
        "status": status,  # "valid", "invalid", "warning"
        "checks": checks,
        "errors": errors or [],
        "warnings": warnings or [],
    }


# ─── JSON Validation ──────────────────────────────────────────────────────────

def validate_json(raw_input: Union[str, dict]) -> tuple[bool, Any, str]:
    """
    Check if input is valid JSON.
    Returns: (is_valid, parsed_object_or_None, error_message)
    """
    if isinstance(raw_input, dict):
        return True, raw_input, ""

    try:
        parsed = json.loads(raw_input)
        if not isinstance(parsed, dict):
            return False, None, "JSON must be an object (dict), not a list or primitive."
        return True, parsed, ""
    except json.JSONDecodeError as e:
        return False, None, f"JSON parse error: {str(e)}"


# ─── Schema Validation ────────────────────────────────────────────────────────

def validate_schema(call: dict) -> tuple[bool, list[str], list[str]]:
    """
    Validate the function call against the registry schema.
    Checks: name field exists, function is registered, required params present,
    no unknown params.
    Returns: (is_valid, errors, warnings)
    """
    errors = []
    warnings = []

    # Check top-level structure
    if "name" not in call:
        errors.append("Missing required field: 'name'")
        return False, errors, warnings

    if "arguments" not in call:
        errors.append("Missing required field: 'arguments'")
        return False, errors, warnings

    func_name = call["name"]
    arguments = call["arguments"]

    # Check function exists in registry
    if func_name not in get_function_names():
        errors.append(
            f"Unknown function '{func_name}'. "
            f"Allowed functions: {', '.join(get_function_names())}"
        )
        return False, errors, warnings

    # Check arguments is a dict
    if not isinstance(arguments, dict):
        errors.append("'arguments' must be an object (dict).")
        return False, errors, warnings

    # Check required parameters
    required = get_required_params(func_name)
    for param in required:
        if param not in arguments:
            errors.append(f"Missing required parameter: '{param}'")

    # Check for unknown parameters
    schema = get_function_schema(func_name)
    known_params = set(schema["parameters"].keys())
    for param in arguments:
        if param not in known_params:
            warnings.append(f"Unknown parameter: '{param}' (will be ignored)")

    is_valid = len(errors) == 0
    return is_valid, errors, warnings


# ─── Data Type Validation ─────────────────────────────────────────────────────

def validate_types(call: dict) -> tuple[bool, list[str]]:
    """
    Validate that argument values match expected types.
    Returns: (is_valid, errors)
    """
    errors = []
    func_name = call.get("name", "")
    arguments = call.get("arguments", {})

    schema = get_function_schema(func_name)
    if not schema:
        return True, []  # Can't validate without schema

    for param_name, value in arguments.items():
        if param_name in schema["parameters"]:
            if not validate_param_type(func_name, param_name, value):
                expected = schema["parameters"][param_name]["type"]
                actual = type(value).__name__
                errors.append(
                    f"Type mismatch for '{param_name}': "
                    f"expected {expected}, got {actual} (value: {repr(value)})"
                )

    return len(errors) == 0, errors


# ─── SQL Safety Validation ────────────────────────────────────────────────────

# Patterns that indicate SQL injection attempts
SQL_INJECTION_PATTERNS = [
    r";\s*--",                          # Statement terminator + comment
    r"'\s*OR\s+'?\d+'?\s*=\s*'?\d+",   # OR 1=1 variations
    r"UNION\s+SELECT",                  # UNION-based injection
    r";\s*(DROP|DELETE|INSERT|UPDATE|ALTER|CREATE|TRUNCATE)",  # Chained dangerous statements
    r"EXEC\s*\(",                       # Stored procedure execution
    r"xp_\w+",                          # SQL Server extended procedures
]

# Dangerous SQL keywords that shouldn't appear in user queries
DANGEROUS_KEYWORDS = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE", "TRUNCATE", "EXEC"]


def validate_sql(sql: str) -> tuple[bool, list[str], list[str]]:
    """
    Validate SQL query for safety and syntax.
    Returns: (is_valid, errors, warnings)
    """
    errors = []
    warnings = []

    if not sql or not sql.strip():
        errors.append("SQL query is empty.")
        return False, errors, warnings

    sql_upper = sql.strip().upper()

    # Must be a SELECT statement
    if not sql_upper.startswith("SELECT"):
        errors.append(
            f"Only SELECT queries are allowed. "
            f"Detected: '{sql_upper.split()[0]}' statement."
        )

    # Check for dangerous keywords
    for keyword in DANGEROUS_KEYWORDS:
        # Use word boundary matching to avoid false positives
        pattern = r'\b' + keyword + r'\b'
        if re.search(pattern, sql_upper):
            errors.append(f"Dangerous SQL keyword detected: '{keyword}'")

    # Check for injection patterns
    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, sql_upper):
            errors.append(f"Potential SQL injection detected (pattern: {pattern})")

    # Syntax validation with sqlparse
    try:
        parsed = sqlparse.parse(sql)
        if not parsed or not parsed[0].tokens:
            errors.append("SQL could not be parsed — possible syntax error.")
        else:
            # Check for common syntax errors
            sql_str = str(parsed[0])
            # Detect invalid operators like =>
            if "=>" in sql and "->>" not in sql and "->" not in sql:
                errors.append(
                    "Invalid SQL operator '=>' detected. "
                    "Did you mean '>=' (greater than or equal)?"
                )
    except Exception as e:
        errors.append(f"SQL parse error: {str(e)}")

    # Additional checks
    if sql.count("'") % 2 != 0:
        errors.append("Unmatched single quotes in SQL query.")
    if sql.count('"') % 2 != 0:
        warnings.append("Unmatched double quotes in SQL query.")

    # Check for SELECT * (warning, not error)
    if "SELECT *" in sql_upper or "SELECT  *" in sql_upper:
        warnings.append(
            "Using SELECT * — consider specifying columns explicitly "
            "for better performance and clarity."
        )

    is_valid = len(errors) == 0
    return is_valid, errors, warnings


# ─── Full Validation Pipeline ─────────────────────────────────────────────────

def validate_function_call(raw_input: Union[str, dict]) -> dict:
    """
    Run the complete validation pipeline on a function call.
    Returns a comprehensive validation result.
    """
    checks = {
        "json_valid": False,
        "schema_match": False,
        "types_valid": False,
        "sql_safe": None,  # None = not applicable (non-SQL function)
    }
    all_errors = []
    all_warnings = []

    # Step 1: JSON validation
    json_valid, parsed, json_error = validate_json(raw_input)
    checks["json_valid"] = json_valid

    if not json_valid:
        all_errors.append(json_error)
        return _make_result("invalid", checks, all_errors)

    # Step 2: Schema validation
    schema_valid, schema_errors, schema_warnings = validate_schema(parsed)
    checks["schema_match"] = schema_valid
    all_errors.extend(schema_errors)
    all_warnings.extend(schema_warnings)

    if not schema_valid:
        return _make_result("invalid", checks, all_errors, all_warnings)

    # Step 3: Type validation
    types_valid, type_errors = validate_types(parsed)
    checks["types_valid"] = types_valid
    all_errors.extend(type_errors)

    # Step 4: SQL safety (only for query_database function)
    if parsed["name"] == "query_database":
        sql_query = parsed["arguments"].get("query", "")
        sql_valid, sql_errors, sql_warnings = validate_sql(sql_query)
        checks["sql_safe"] = sql_valid
        all_errors.extend(sql_errors)
        all_warnings.extend(sql_warnings)

    # Determine overall status
    if all_errors:
        status = "invalid"
    elif all_warnings:
        status = "warning"
    else:
        status = "valid"

    return _make_result(status, checks, all_errors, all_warnings)
