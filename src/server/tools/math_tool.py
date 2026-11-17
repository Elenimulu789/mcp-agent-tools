"""Perform bounded decimal arithmetic with a Python syntax tree."""
import ast
from decimal import Decimal, DecimalException, localcontext
import operator
import re

OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
       ast.Div: operator.truediv, ast.Mod: operator.mod, ast.Pow: operator.pow}
NUMBER = re.compile(r"(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]{1,2})?")


class MathRejected(ValueError):
    """A safe diagnostic for an invalid expression."""


def calculate_expression(expression: str) -> dict:
    """Evaluate numeric literals, parentheses, and allowlisted arithmetic."""
    source = expression.strip()
    if not 1 <= len(source) <= 160:
        raise MathRejected("Provide an arithmetic expression up to 160 characters.")
    try:
        tree = ast.parse(source, mode="eval")
    except (SyntaxError, RecursionError):
        raise MathRejected("The expression is not valid arithmetic.") from None
    if sum(1 for _ in ast.walk(tree)) > 48:
        raise MathRejected("The expression is too complex.")

    def visit(node: ast.AST) -> Decimal:
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            token = ast.get_source_segment(source, node) or ""
            if len(token) > 30 or not NUMBER.fullmatch(token):
                raise MathRejected("Use bounded decimal number literals.")
            result = Decimal(token)
        elif isinstance(node, ast.UnaryOp) and type(node.op) in (ast.UAdd, ast.USub):
            value = visit(node.operand)
            result = value if isinstance(node.op, ast.UAdd) else -value
        elif isinstance(node, ast.BinOp) and type(node.op) in OPS:
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Pow) and (right != right.to_integral_value() or abs(right) > 12):
                raise MathRejected("Powers require an integer exponent between -12 and 12.")
            result = OPS[type(node.op)](left, right)
        else:
            raise MathRejected("Use only numbers, parentheses, and arithmetic operators.")
        if not result.is_finite() or (result and abs(result.adjusted()) > 40):
            raise MathRejected("The result exceeds the supported magnitude.")
        return result

    try:
        with localcontext() as ctx:
            ctx.prec = 34
            result = visit(tree.body)
            return {"result": format(result.normalize(), "f") if result else "0"}
    except DecimalException:
        raise MathRejected("The arithmetic operation is undefined or exceeded its limits.") from None
