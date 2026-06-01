"""
Function Registry — Defines allowed functions with their parameter schemas.

This module acts as the "contract" for what function calls the system accepts.
Each registered function has a name, description, and typed parameter definitions.
"""

from typing import Any, Optional


# ─── Parameter & Function Schema Definitions ──────────────────────────────────

FUNCTION_REGISTRY = [
    {
        "name": "query_database",
        "description": "Execute a read-only SQL SELECT query against the database.",
        "parameters": {
            "query": {
                "type": "string",
                "required": True,
                "description": "A valid SQL SELECT statement."
            }
        }
    },
    {
        "name": "get_user_stats",
        "description": "Retrieve aggregated statistics for a specific user by ID.",
        "parameters": {
            "user_id": {
                "type": "integer",
                "required": True,
                "description": "The unique identifier of the user."
            }
        }
    },
    {
        "name": "search_products",
        "description": "Search products by keyword with an optional maximum price filter.",
        "parameters": {
            "keyword": {
                "type": "string",
                "required": True,
                "description": "Search keyword to match against product names and categories."
            },
            "max_price": {
                "type": "number",
                "required": False,
                "description": "Maximum price filter (inclusive). Omit for no limit."
            }
        }
    },
    {
        "name": "get_order_history",
        "description": "Retrieve order history for a specific user.",
        "parameters": {
            "user_id": {
                "type": "integer",
                "required": True,
                "description": "The unique identifier of the user."
            },
            "limit": {
                "type": "integer",
                "required": False,
                "description": "Maximum number of orders to return. Defaults to 10."
            }
        }
    }
]


# ─── Type Mapping for Validation ───────────────────────────────────────────────

TYPE_MAP = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "array": list,
    "object": dict,
}


# ─── Registry Lookup Helpers ───────────────────────────────────────────────────

def get_function_names() -> list[str]:
    """Return a list of all registered function names."""
    return [f["name"] for f in FUNCTION_REGISTRY]


def get_function_schema(name: str) -> Optional[dict]:
    """
    Look up a function schema by name.
    Returns None if the function is not registered.
    """
    for func in FUNCTION_REGISTRY:
        if func["name"] == name:
            return func
    return None


def get_required_params(name: str) -> list[str]:
    """Return a list of required parameter names for a function."""
    schema = get_function_schema(name)
    if not schema:
        return []
    return [
        param_name
        for param_name, param_def in schema["parameters"].items()
        if param_def.get("required", False)
    ]


def get_optional_params(name: str) -> list[str]:
    """Return a list of optional parameter names for a function."""
    schema = get_function_schema(name)
    if not schema:
        return []
    return [
        param_name
        for param_name, param_def in schema["parameters"].items()
        if not param_def.get("required", False)
    ]


def validate_param_type(name: str, param_name: str, value: Any) -> bool:
    """
    Check if a parameter value matches the expected type.
    Returns True if the type is correct or if the parameter/function is not found.
    """
    schema = get_function_schema(name)
    if not schema or param_name not in schema["parameters"]:
        return True  # Can't validate unknown params — handled elsewhere

    expected_type_str = schema["parameters"][param_name]["type"]
    expected_type = TYPE_MAP.get(expected_type_str)

    if expected_type is None:
        return True  # Unknown type definition — skip

    return isinstance(value, expected_type)


def get_registry_summary() -> list[dict]:
    """
    Return a simplified view of the registry for API responses / UI display.
    """
    summary = []
    for func in FUNCTION_REGISTRY:
        params = []
        for param_name, param_def in func["parameters"].items():
            params.append({
                "name": param_name,
                "type": param_def["type"],
                "required": param_def.get("required", False),
                "description": param_def.get("description", "")
            })
        summary.append({
            "name": func["name"],
            "description": func["description"],
            "parameters": params
        })
    return summary
