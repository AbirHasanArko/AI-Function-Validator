"""
NL-to-Function Mapper — Simulates LLM function call generation.

Converts natural language queries into structured function call JSON
using rule-based pattern matching. This replaces a real LLM for
self-contained demonstration purposes.
"""

import re
from typing import Optional


# ─── Pattern Definitions ──────────────────────────────────────────────────────

def _extract_city(text: str) -> Optional[str]:
    """Extract city name from natural language."""
    city_pattern = r"(?:in|from|city\s+(?:is|=)?)\s+['\"]?(\w+)['\"]?"
    match = re.search(city_pattern, text, re.IGNORECASE)
    return match.group(1) if match else None


def _extract_age_condition(text: str) -> Optional[str]:
    """Extract age-related conditions."""
    patterns = [
        (r"age\s*(?:above|over|greater than|>)\s*(\d+)", "> {0}"),
        (r"(?:above|over|older than)\s+(?:age\s+)?(\d+)", "> {0}"),
        (r"age\s*(?:below|under|less than|<)\s*(\d+)", "< {0}"),
        (r"(?:below|under|younger than)\s+(?:age\s+)?(\d+)", "< {0}"),
        (r"age\s*(?:at least|>=)\s*(\d+)", ">= {0}"),
        (r"age\s*(?:at most|<=)\s*(\d+)", "<= {0}"),
        (r"age\s*(?:=|is|equals?)\s*(\d+)", "= {0}"),
        (r"(\d+)\s*(?:years?\s+old|yo)", "> {0}"),
    ]
    for pattern, template in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return template.format(match.group(1))
    return None


def _extract_name(text: str) -> Optional[str]:
    """Extract a person's name from natural language."""
    patterns = [
        r"(?:named?|called)\s+['\"]?(\w+(?:\s+\w+)?)['\"]?",
        r"user\s+['\"]?(\w+(?:\s+\w+)?)['\"]?(?:\s|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = match.group(1)
            # Filter out common words that aren't names
            if name.lower() not in ("the", "a", "an", "in", "from", "with", "above", "below", "stats", "history"):
                return name
    return None


def _extract_user_id(text: str) -> Optional[int]:
    """Extract user ID from natural language."""
    patterns = [
        r"user\s*(?:id|#)?\s*[=:]?\s*(\d+)",
        r"(?:id|#)\s*[=:]?\s*(\d+)",
        r"for\s+user\s+(\d+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def _extract_keyword(text: str) -> Optional[str]:
    """Extract search keyword from natural language."""
    patterns = [
        r"(?:search|find|look for|looking for)\s+(?:products?\s+)?(?:with|named?|called|like|for)?\s*['\"]?(\w+(?:\s+\w+)*?)['\"]?\s*(?:with|under|below|above|over|$)",
        r"(?:products?\s+)(?:like|named?|called|about)\s+['\"]?(\w+(?:\s+\w+)*?)['\"]?",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            keyword = match.group(1).strip()
            if keyword.lower() not in ("product", "products", "the", "a", "an"):
                return keyword
    return None


def _extract_price(text: str) -> Optional[float]:
    """Extract price/budget from natural language."""
    patterns = [
        r"(?:under|below|less than|max|budget|cheaper than|up to)\s*(?:\$|tk|bdt|taka)?\s*(\d+(?:\.\d+)?)",
        r"(?:\$|tk|bdt|taka)\s*(\d+(?:\.\d+)?)\s*(?:max|budget|or less)",
        r"(?:price|cost)\s*(?:under|below|<|<=)\s*(?:\$|tk|bdt|taka)?\s*(\d+(?:\.\d+)?)",
        r"max(?:imum)?\s*price\s*(?:of|:)?\s*(?:\$|tk|bdt|taka)?\s*(\d+(?:\.\d+)?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None


def _extract_limit(text: str) -> Optional[int]:
    """Extract result limit from natural language."""
    patterns = [
        r"(?:top|first|last|latest|recent|limit)\s*(\d+)",
        r"(\d+)\s*(?:most recent|latest|results?|orders?|items?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


# ─── Function Call Generators ──────────────────────────────────────────────────

def _generate_user_query(text: str) -> dict:
    """Generate a query_database call for user-related queries."""
    conditions = []
    city = _extract_city(text)
    age_cond = _extract_age_condition(text)
    name = _extract_name(text)

    if city:
        conditions.append(f"city = '{city}'")
    if age_cond:
        conditions.append(f"age {age_cond}")
    if name:
        conditions.append(f"name LIKE '%{name}%'")

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    sql = f"SELECT * FROM users WHERE {where_clause}"

    return {
        "name": "query_database",
        "arguments": {"query": sql}
    }


def _generate_product_query(text: str) -> dict:
    """Generate a search_products call."""
    keyword = _extract_keyword(text)
    max_price = _extract_price(text)

    if not keyword:
        # Fallback: try to extract any noun after "product"
        words = text.lower().split()
        for i, w in enumerate(words):
            if w in ("product", "products") and i + 1 < len(words):
                keyword = words[i + 1]
                break
        if not keyword:
            keyword = "all"

    args = {"keyword": keyword}
    if max_price is not None:
        args["max_price"] = max_price

    return {
        "name": "search_products",
        "arguments": args
    }


def _generate_user_stats(text: str) -> dict:
    """Generate a get_user_stats call."""
    user_id = _extract_user_id(text)
    return {
        "name": "get_user_stats",
        "arguments": {"user_id": user_id or 1}
    }


def _generate_order_history(text: str) -> dict:
    """Generate a get_order_history call."""
    user_id = _extract_user_id(text)
    limit = _extract_limit(text)

    args = {"user_id": user_id or 1}
    if limit is not None:
        args["limit"] = limit

    return {
        "name": "get_order_history",
        "arguments": args
    }


def _generate_generic_query(text: str) -> dict:
    """Fallback: generate a simple SELECT query from whatever we can parse."""
    # Try to detect table name
    table_keywords = {
        "user": "users",
        "product": "products",
        "order": "orders",
    }

    table = "users"  # default
    for keyword, table_name in table_keywords.items():
        if keyword in text.lower():
            table = table_name
            break

    return {
        "name": "query_database",
        "arguments": {"query": f"SELECT * FROM {table} LIMIT 10"}
    }


# ─── Main Interface ───────────────────────────────────────────────────────────

def nl_to_function_call(text: str) -> dict:
    """
    Convert natural language text to a structured function call.

    Uses rule-based pattern matching to simulate LLM function-call generation.
    Returns a dict with 'name' and 'arguments'.
    """
    text_lower = text.lower().strip()

    # Detect intent
    if any(kw in text_lower for kw in ["stat", "statistics", "summary", "overview"]):
        if any(kw in text_lower for kw in ["user", "person", "member"]):
            return _generate_user_stats(text)

    if any(kw in text_lower for kw in ["order", "purchase", "bought", "history", "transaction"]):
        return _generate_order_history(text)

    if any(kw in text_lower for kw in ["product", "item", "goods", "merchandise", "shop", "buy"]):
        return _generate_product_query(text)

    if any(kw in text_lower for kw in ["user", "person", "people", "member", "find", "search", "get", "show", "list", "query"]):
        return _generate_user_query(text)

    # Fallback
    return _generate_generic_query(text)
