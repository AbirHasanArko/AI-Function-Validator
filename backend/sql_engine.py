"""
SQL Engine — SQLite connection manager, schema seeding, and query execution.

Handles database initialization with realistic sample data and provides
safe query execution (SELECT-only) for the function-calling pipeline.
"""

import sqlite3
import os
from typing import Optional

# Database file lives alongside the backend package
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "app.db")


def _get_connection() -> sqlite3.Connection:
    """Create a new SQLite connection with row factory for dict-like access."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Initialize the database: create tables and seed with sample data.
    Safe to call multiple times — uses IF NOT EXISTS.
    """
    conn = _get_connection()
    cursor = conn.cursor()

    # ── Create Tables ──────────────────────────────────────────────────────
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            city TEXT NOT NULL,
            age INTEGER NOT NULL,
            signup_date TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            total REAL NOT NULL,
            order_date TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
    """)

    # ── Seed Data (only if tables are empty) ───────────────────────────────
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        users = [
            ("Rahim Ahmed", "rahim@example.com", "Dhaka", 25, "2024-01-15"),
            ("Fatima Khan", "fatima@example.com", "Chittagong", 30, "2024-02-20"),
            ("Arif Hossain", "arif@example.com", "Dhaka", 19, "2024-03-10"),
            ("Nusrat Jahan", "nusrat@example.com", "Sylhet", 22, "2024-04-05"),
            ("Karim Uddin", "karim@example.com", "Dhaka", 35, "2024-05-12"),
            ("Sadia Islam", "sadia@example.com", "Rajshahi", 28, "2024-06-01"),
            ("Tanvir Alam", "tanvir@example.com", "Khulna", 21, "2024-07-18"),
            ("Mitu Das", "mitu@example.com", "Dhaka", 26, "2024-08-22"),
            ("Jahangir Mirza", "jahangir@example.com", "Comilla", 40, "2024-09-30"),
            ("Rumi Begum", "rumi@example.com", "Dhaka", 17, "2024-10-11"),
            ("Shakil Mahmud", "shakil@example.com", "Barishal", 23, "2024-11-05"),
            ("Priya Sen", "priya@example.com", "Dhaka", 29, "2024-12-15"),
        ]
        cursor.executemany(
            "INSERT INTO users (name, email, city, age, signup_date) VALUES (?, ?, ?, ?, ?)",
            users
        )

    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        products = [
            ("Wireless Earbuds", "Electronics", 1299.99, 150),
            ("Cotton T-Shirt", "Clothing", 499.50, 300),
            ("Python Programming Book", "Books", 750.00, 45),
            ("Stainless Steel Water Bottle", "Home", 350.00, 200),
            ("Mechanical Keyboard", "Electronics", 3500.00, 80),
            ("Running Shoes", "Clothing", 2200.00, 120),
            ("Data Science Handbook", "Books", 950.00, 60),
            ("Desk Lamp LED", "Home", 890.00, 95),
            ("Smartphone Case", "Electronics", 250.00, 500),
            ("Notebook Set (5-pack)", "Stationery", 180.00, 400),
        ]
        cursor.executemany(
            "INSERT INTO products (name, category, price, stock) VALUES (?, ?, ?, ?)",
            products
        )

    cursor.execute("SELECT COUNT(*) FROM orders")
    if cursor.fetchone()[0] == 0:
        orders = [
            (1, 1, 1, 1299.99, "2024-06-15"),
            (1, 5, 1, 3500.00, "2024-07-01"),
            (2, 2, 3, 1498.50, "2024-06-20"),
            (3, 3, 1, 750.00, "2024-08-05"),
            (4, 6, 1, 2200.00, "2024-07-22"),
            (5, 4, 2, 700.00, "2024-09-10"),
            (5, 8, 1, 890.00, "2024-09-10"),
            (6, 9, 2, 500.00, "2024-10-01"),
            (7, 10, 5, 900.00, "2024-10-15"),
            (8, 1, 1, 1299.99, "2024-11-01"),
            (8, 7, 1, 950.00, "2024-11-01"),
            (9, 5, 1, 3500.00, "2024-11-20"),
            (10, 2, 2, 999.00, "2024-12-05"),
            (1, 10, 3, 540.00, "2024-12-25"),
            (12, 3, 2, 1500.00, "2025-01-10"),
        ]
        cursor.executemany(
            "INSERT INTO orders (user_id, product_id, quantity, total, order_date) VALUES (?, ?, ?, ?, ?)",
            orders
        )

    conn.commit()
    conn.close()


# ─── Query Execution ──────────────────────────────────────────────────────────

def execute_query(sql: str) -> dict:
    """
    Execute a SELECT query and return results as a list of dicts.
    Returns: {"columns": [...], "rows": [...], "row_count": int}
    Raises ValueError for non-SELECT queries.
    """
    stripped = sql.strip().upper()
    if not stripped.startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed for safety.")

    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        result_rows = [dict(row) for row in rows]
        return {
            "columns": columns,
            "rows": result_rows,
            "row_count": len(result_rows)
        }
    finally:
        conn.close()


def get_user_stats(user_id: int) -> dict:
    """
    Get aggregated stats for a user: order count, total spent, avg order value.
    """
    conn = _get_connection()
    try:
        cursor = conn.cursor()

        # User info
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user_row = cursor.fetchone()
        if not user_row:
            return {"error": f"User with id {user_id} not found."}

        user = dict(user_row)

        # Order stats
        cursor.execute("""
            SELECT 
                COUNT(*) as order_count,
                COALESCE(SUM(total), 0) as total_spent,
                COALESCE(AVG(total), 0) as avg_order_value,
                MIN(order_date) as first_order,
                MAX(order_date) as last_order
            FROM orders WHERE user_id = ?
        """, (user_id,))
        stats = dict(cursor.fetchone())

        return {
            "columns": ["name", "email", "city", "age", "order_count", "total_spent", "avg_order_value", "first_order", "last_order"],
            "rows": [{**user, **stats}],
            "row_count": 1
        }
    finally:
        conn.close()


def search_products(keyword: str, max_price: Optional[float] = None) -> dict:
    """Search products by keyword with optional price filter."""
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        query = "SELECT * FROM products WHERE (name LIKE ? OR category LIKE ?)"
        params = [f"%{keyword}%", f"%{keyword}%"]

        if max_price is not None:
            query += " AND price <= ?"
            params.append(max_price)

        query += " ORDER BY price ASC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        return {
            "columns": columns,
            "rows": [dict(r) for r in rows],
            "row_count": len(rows)
        }
    finally:
        conn.close()


def get_order_history(user_id: int, limit: int = 10) -> dict:
    """Get order history for a user with product details."""
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                o.id as order_id,
                p.name as product_name,
                p.category,
                o.quantity,
                o.total,
                o.order_date
            FROM orders o
            JOIN products p ON o.product_id = p.id
            WHERE o.user_id = ?
            ORDER BY o.order_date DESC
            LIMIT ?
        """, (user_id, limit))
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        return {
            "columns": columns,
            "rows": [dict(r) for r in rows],
            "row_count": len(rows)
        }
    finally:
        conn.close()
