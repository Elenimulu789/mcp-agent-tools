import httpx
import pytest

from src.server.tools.math_tool import calculate_expression
from src.server.tools.sql_tool import query_database
from src.server.tools.weather_tool import WeatherUnavailable, get_current_weather


def test_sql_lookup():
    result = query_database("SELECT order_id, quantity, total_cents FROM orders WHERE order_id = 4492")
    assert result["columns"] == ["order_id", "quantity", "total_cents"]
    assert result["rows"] == [(4492, 24, 248500)]


def test_sql_row_limit():
    result = query_database("SELECT o.order_id FROM orders o CROSS JOIN inventory i")
    assert len(result["rows"]) == 50
    assert result["truncated"]


def test_math_precision():
    assert calculate_expression("2 + 3 * (4 - 1) ** 2") == {"result": "29"}
    assert calculate_expression("248500 / 100 * 0.035") == {"result": "86.975"}


async def test_weather_response():
    def answer(request):
        if request.url.host == "geocoding-api.open-meteo.com":
            assert request.url.params["name"] == "Seattle"
            assert request.url.params["countryCode"] == "US"
            return httpx.Response(200, json={"results": [
                {"latitude": 47.6, "longitude": -122.3, "country_code": "US"}]})
        assert request.url.params["latitude"] == "47.6"
        return httpx.Response(200, json={"current": {
            "time": "2026-11-17T12:00", "weather_code": 61, "temperature_2m": 12.6,
            "precipitation": 1.2, "wind_speed_10m": 12, "note": "discard this field",
        }})
    result = await get_current_weather(" Seattle ", "us", httpx.MockTransport(answer))
    assert result["condition"] == "Drizzle or rain"
    assert result["precipitation_mm"] == 1.2
    assert result["time_utc"] == "2026-11-17T12:00Z"
    assert "note" not in result


async def test_weather_rate_limit():
    with pytest.raises(WeatherUnavailable, match="rate limiting"):
        await get_current_weather("Seattle", transport=httpx.MockTransport(
            lambda request: httpx.Response(429)))
