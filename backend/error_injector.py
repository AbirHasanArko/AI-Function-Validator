"""
Error Injector — The WOW FACTOR module.

Intentionally corrupts valid function calls in controlled ways to demonstrate
the validator's detection capabilities. Supports multiple injection modes.
"""

import json
import random
import copy


# ─── Error Injection Modes ─────────────────────────────────────────────────────

def inject_invalid_json(call: dict) -> tuple[str, str]:
    """
    Break JSON syntax in various ways.
    Returns the corrupted string (not parseable JSON) and a description.
    """
    json_str = json.dumps(call, indent=2)

    strategies = [
        # Remove a closing brace
        (
            json_str.rstrip("}") + " ",
            "Removed closing brace — JSON is now malformed."
        ),
        # Add trailing comma
        (
            json_str.replace("}", ",}"),
            "Added trailing comma — invalid JSON syntax."
        ),
        # Remove quotes from a key
        (
            json_str.replace('"name"', 'name', 1),
            "Removed quotes from key 'name' — keys must be quoted in JSON."
        ),
        # Use single quotes
        (
            json_str.replace('"', "'"),
            "Replaced double quotes with single quotes — JSON requires double quotes."
        ),
    ]

    corrupted, description = random.choice(strategies)
    return corrupted, description


def inject_wrong_schema(call: dict) -> tuple[dict, str]:
    """
    Break the schema structure: remove required fields, add unknown ones, etc.
    """
    corrupted = copy.deepcopy(call)

    strategies = []

    # Remove the 'name' field
    strategies.append((
        lambda c: c.pop("name", None) or c,
        "Removed required 'name' field."
    ))

    # Remove the 'arguments' field
    strategies.append((
        lambda c: c.pop("arguments", None) or c,
        "Removed required 'arguments' field."
    ))

    # Add unknown parameters
    def add_unknown(c):
        c["arguments"]["unknown_param_xyz"] = "mystery_value"
        return c
    strategies.append((
        add_unknown,
        "Added unknown parameter 'unknown_param_xyz' not in the schema."
    ))

    # Remove a required parameter
    def remove_param(c):
        args = c.get("arguments", {})
        if args:
            first_key = list(args.keys())[0]
            del args[first_key]
        return c
    strategies.append((
        remove_param,
        "Removed a required parameter from arguments."
    ))

    mutator, description = random.choice(strategies)
    result = mutator(corrupted)

    # Ensure we return a dict (the lambda for 'name' removal returns None from pop)
    if not isinstance(result, dict):
        result = corrupted

    return result, description


def inject_sql_syntax_error(call: dict) -> tuple[dict, str]:
    """
    Introduce SQL syntax errors into the query.
    """
    corrupted = copy.deepcopy(call)
    query = corrupted.get("arguments", {}).get("query", "")

    if not query:
        corrupted["arguments"]["query"] = "SELCT * FORM users WERE age => 20"
        return corrupted, "Replaced query with one containing multiple typos and invalid operators."

    strategies = [
        # Invalid operator =>
        (
            query.replace(">=", "=>").replace(">", "=>") if ">" in query
            else query + " WHERE age => 20",
            "Replaced '>' or '>=' with invalid operator '=>'."
        ),
        # Typo in SELECT
        (
            query.replace("SELECT", "SELCT", 1),
            "Introduced typo: 'SELCT' instead of 'SELECT'."
        ),
        # Missing FROM
        (
            query.replace("FROM", "FORM", 1),
            "Introduced typo: 'FORM' instead of 'FROM'."
        ),
        # Unmatched quote
        (
            query.replace("'", "", 1) if "'" in query
            else query + " WHERE name = 'test",
            "Removed a single quote — creating unmatched quotes."
        ),
    ]

    new_query, description = random.choice(strategies)
    corrupted["arguments"]["query"] = new_query
    return corrupted, description


def inject_sql_injection(call: dict) -> tuple[dict, str]:
    """
    Inject SQL injection patterns into the query.
    """
    corrupted = copy.deepcopy(call)

    strategies = [
        (
            "SELECT * FROM users WHERE name = '' OR '1'='1'; DROP TABLE users; --",
            "Classic SQL injection: OR '1'='1' with DROP TABLE."
        ),
        (
            "SELECT * FROM users WHERE id = 1 UNION SELECT * FROM sqlite_master; --",
            "UNION-based injection to extract schema information."
        ),
        (
            "SELECT * FROM users; DELETE FROM users; --",
            "Chained DELETE statement to wipe the users table."
        ),
        (
            "SELECT * FROM users WHERE name = '' OR 1=1; --",
            "Boolean-based injection: OR 1=1 to bypass WHERE clause."
        ),
    ]

    new_query, description = random.choice(strategies)
    corrupted["arguments"] = {"query": new_query}
    return corrupted, description


def inject_wrong_types(call: dict) -> tuple[dict, str]:
    """
    Change argument values to incorrect types.
    """
    corrupted = copy.deepcopy(call)
    args = corrupted.get("arguments", {})

    descriptions = []
    for key, value in list(args.items()):
        if isinstance(value, str):
            args[key] = 12345  # String → int
            descriptions.append(f"Changed '{key}' from string to integer.")
        elif isinstance(value, int):
            args[key] = "not_a_number"  # Int → string
            descriptions.append(f"Changed '{key}' from integer to string.")
        elif isinstance(value, float):
            args[key] = True  # Float → bool
            descriptions.append(f"Changed '{key}' from float to boolean.")
        if descriptions:
            break  # Just change one for clarity

    description = descriptions[0] if descriptions else "No type changes could be made."
    return corrupted, description


def inject_unknown_function(call: dict) -> tuple[dict, str]:
    """
    Change the function name to a non-existent one.
    """
    corrupted = copy.deepcopy(call)
    fake_names = [
        "hack_database",
        "delete_all_users",
        "send_email",
        "restart_server",
        "query_databse",  # Intentional typo
    ]
    original = corrupted.get("name", "unknown")
    corrupted["name"] = random.choice(fake_names)
    return corrupted, f"Changed function name from '{original}' to '{corrupted['name']}'."


# ─── Main Injection Interface ─────────────────────────────────────────────────

INJECTION_MODES = {
    "invalid_json": {
        "name": "Invalid JSON",
        "description": "Breaks JSON syntax (missing braces, bad quotes, trailing commas).",
        "handler": inject_invalid_json,
        "returns_string": True,  # Returns string, not dict
    },
    "wrong_schema": {
        "name": "Wrong Schema",
        "description": "Removes required fields or adds unknown parameters.",
        "handler": inject_wrong_schema,
        "returns_string": False,
    },
    "sql_syntax_error": {
        "name": "SQL Syntax Error",
        "description": "Introduces typos and invalid operators in SQL.",
        "handler": inject_sql_syntax_error,
        "returns_string": False,
    },
    "sql_injection": {
        "name": "SQL Injection",
        "description": "Injects classic SQL injection payloads.",
        "handler": inject_sql_injection,
        "returns_string": False,
    },
    "wrong_types": {
        "name": "Wrong Types",
        "description": "Changes argument values to incorrect types.",
        "handler": inject_wrong_types,
        "returns_string": False,
    },
    "unknown_function": {
        "name": "Unknown Function",
        "description": "Changes function name to unregistered one.",
        "handler": inject_unknown_function,
        "returns_string": False,
    },
}


def inject_error(call: dict, mode: str) -> dict:
    """
    Inject an error into a function call.

    Args:
        call: A valid function call dict.
        mode: One of the INJECTION_MODES keys.

    Returns:
        Dict with 'corrupted_call', 'injection_description', 'mode'.
    """
    if mode not in INJECTION_MODES:
        return {
            "error": f"Unknown injection mode '{mode}'. Available: {list(INJECTION_MODES.keys())}"
        }

    mode_info = INJECTION_MODES[mode]
    handler = mode_info["handler"]
    corrupted, description = handler(call)

    return {
        "original_call": call,
        "corrupted_call": corrupted,
        "injection_mode": mode,
        "injection_name": mode_info["name"],
        "injection_description": description,
        "returns_string": mode_info["returns_string"],
    }


def get_injection_modes() -> list[dict]:
    """Return available injection modes for the UI."""
    return [
        {"id": mode_id, "name": info["name"], "description": info["description"]}
        for mode_id, info in INJECTION_MODES.items()
    ]
