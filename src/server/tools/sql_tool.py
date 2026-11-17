"""Read synthetic operations data under a SQLite authorization policy."""
from pathlib import Path
import sqlite3
import time

from sqlglot import exp, parse
from sqlglot.errors import SqlglotError

DATABASE = Path(__file__).resolve().parents[3] / "data" / "enterprise_ops.db"
TABLES = {"orders", "inventory", "customers"}
FUNCTIONS = {"abs", "avg", "coalesce", "count", "length", "lower", "max", "min", "round", "sum", "total", "upper"}
ROW_LIMIT = 50


class SQLRejected(ValueError):
    """A safe diagnostic for a rejected query."""


def _validate(sql: str) -> None:
    if not sql.strip() or len(sql) > 3000:
        raise SQLRejected("Provide a SELECT query between 1 and 3,000 characters.")
    statement = sql.strip().removesuffix(";")
    if ";" in statement:
        raise SQLRejected("Only one SELECT statement is allowed.")
    try:
        statements = parse(statement, read="sqlite")
    except (SqlglotError, RecursionError):
        raise SQLRejected("The SQL could not be parsed.") from None
    if len(statements) != 1 or not isinstance(statements[0], exp.Select):
        raise SQLRejected("Only a SELECT query is allowed.")
    query = statements[0]
    if query.find(exp.CTE) or query.find(exp.Into):
        raise SQLRejected("CTEs and SELECT INTO are outside the query policy.")
    for table in query.find_all(exp.Table):
        if table.name.lower() not in TABLES or table.db or table.catalog:
            raise SQLRejected("Only orders, inventory, and customers may be read.")


def _authorize(action: int, arg1: str | None, arg2: str | None,
               database: str | None, _origin: str | None) -> int:
    if action == sqlite3.SQLITE_SELECT:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_READ and (arg1 or "").lower() in TABLES:
        # SQLite may omit the schema for a table read that names no column.
        if database == "main" or (database is None and arg2 == ""):
            return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_FUNCTION and (arg2 or "").lower() in FUNCTIONS:
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def query_database(sql_query: str, database: Path = DATABASE) -> dict:
    """Run one bounded SELECT. Enforce read-only access again inside SQLite."""
    _validate(sql_query)
    try:
        db = sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True, timeout=0.25)
    except sqlite3.Error:
        raise SQLRejected("The operations database is unavailable.") from None
    try:
        db.execute("PRAGMA query_only = ON")
        db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 16_384)
        db.setlimit(sqlite3.SQLITE_LIMIT_COLUMN, 32)
        db.setlimit(sqlite3.SQLITE_LIMIT_EXPR_DEPTH, 48)
        db.setlimit(sqlite3.SQLITE_LIMIT_COMPOUND_SELECT, 4)
        db.set_authorizer(_authorize)
        deadline = time.monotonic() + 0.35
        db.set_progress_handler(lambda: int(time.monotonic() >= deadline), 500)
        cursor = db.execute(sql_query)
        rows = cursor.fetchmany(ROW_LIMIT + 1)
        if any(isinstance(value, bytes) for row in rows for value in row):
            raise SQLRejected("Binary result values are outside the query policy.")
        return {
            "columns": [entry[0] for entry in cursor.description],
            "rows": rows[:ROW_LIMIT],
            "truncated": len(rows) > ROW_LIMIT,
        }
    except sqlite3.Error:
        raise SQLRejected("SQLite rejected the query or its execution limit was reached.") from None
    finally:
        db.close()
