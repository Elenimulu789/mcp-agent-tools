"""Serve the three operations tools using the official MCP SDK."""
from typing import Any

from mcp.server.fastmcp import FastMCP

from src.server.tools import math_tool, sql_tool, weather_tool

mcp = FastMCP("enterprise-operations")


@mcp.tool()
def query_database(sql_query: str) -> dict[str, Any]:
    """Read fixture data with one SQLite SELECT (no CTEs). Tables: orders
    (order_id, customer_id, city, sku, quantity, total_cents), inventory
    (city, sku, on_hand), customers (customer_id, account_name). Currency is USD cents.
    """
    try:
        return {"ok": True, **sql_tool.query_database(sql_query)}
    except sql_tool.SQLRejected as error:
        return {"ok": False, "code": "sql_rejected", "error": str(error)}


@mcp.tool()
async def get_current_weather(city: str, country_code: str = "US") -> dict[str, Any]:
    """Get current modeled conditions from Open-Meteo in Celsius, mm and km/h.
    Provide the city and optional ISO two-letter country code. No alert feed.
    """
    try:
        return {"ok": True, **await weather_tool.get_current_weather(city, country_code)}
    except weather_tool.WeatherUnavailable as error:
        return {"ok": False, "code": "weather_unavailable", "error": str(error)}


@mcp.tool()
def calculate_expression(expression: str) -> dict[str, Any]:
    """Evaluate decimal arithmetic with numbers, parentheses and + - * / % **.
    Returns a decimal string. Supply all input values explicitly.
    """
    try:
        return {"ok": True, **math_tool.calculate_expression(expression)}
    except math_tool.MathRejected as error:
        return {"ok": False, "code": "math_rejected", "error": str(error)}


if __name__ == "__main__":
    mcp.run(transport="stdio")
