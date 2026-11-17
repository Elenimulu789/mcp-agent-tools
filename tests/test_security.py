import hashlib

import pytest

from src.server.tools.math_tool import MathRejected, calculate_expression
from src.server.tools.sql_tool import DATABASE, SQLRejected, query_database


@pytest.mark.parametrize("statement", [
    "CREATE TABLE practice (id INTEGER)",
    "UPDATE inventory SET on_hand = on_hand WHERE 1 = 0",
    "INSERT INTO orders SELECT * FROM orders WHERE 1 = 0",
    "SELECT 1; SELECT 2",
    "SELECT name FROM sqlite_schema",
    "SELECT random()",
])
def test_sql_policy(statement):
    before = hashlib.sha256(DATABASE.read_bytes()).digest()
    with pytest.raises(SQLRejected):
        query_database(statement)
    assert hashlib.sha256(DATABASE.read_bytes()).digest() == before


@pytest.mark.parametrize("expression", ["abs(-5)", "[1, 2]", "'a'.upper()", "2 ** 1000", "10 / 0"])
def test_math_policy(expression):
    with pytest.raises(MathRejected):
        calculate_expression(expression)
