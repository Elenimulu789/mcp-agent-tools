"""Fetch validated, compact observations from two fixed Open-Meteo endpoints."""
import asyncio
import json
import math
import re

import httpx

GEOCODER = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST = "https://api.open-meteo.com/v1/forecast"
FIELDS = ("temperature_2m", "precipitation", "weather_code", "wind_speed_10m")
TIME = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d")


class WeatherUnavailable(ValueError):
    """A safe diagnostic for invalid, missing, or unavailable weather data."""


async def _get(client: httpx.AsyncClient, url: str, params: dict) -> dict:
    async with client.stream("GET", url, params=params) as response:
        if response.status_code == 429:
            raise WeatherUnavailable("Open-Meteo is rate limiting requests. Try again later.")
        response.raise_for_status()
        body = bytearray()
        async for chunk in response.aiter_bytes():
            body.extend(chunk)
            if len(body) > 24_000:
                raise WeatherUnavailable("Open-Meteo returned too much data.")
    parsed = json.loads(body)
    if not isinstance(parsed, dict):
        raise WeatherUnavailable("Open-Meteo returned an unexpected payload.")
    return parsed


def _number(source: dict, key: str, low: float, high: float) -> float:
    value = source[key]
    if type(value) not in (int, float) or not low <= value <= high or not math.isfinite(value):
        raise WeatherUnavailable("Open-Meteo returned an invalid measurement.")
    return float(value)


def _condition(code: int) -> str:
    if code == 0:
        return "Clear"
    if 1 <= code <= 3:
        return "Partly cloudy or overcast"
    if code in (45, 48):
        return "Fog"
    if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
        return "Drizzle or rain"
    if code in (71, 73, 75, 77, 85, 86):
        return "Snow"
    if code in (95, 96, 99):
        return "Thunderstorm"
    return "Unknown"


async def get_current_weather(city: str, country_code: str = "US",
                              transport: httpx.AsyncBaseTransport | None = None) -> dict:
    """Geocode a city within a country and return current metric conditions."""
    city = " ".join(city.split())
    country = country_code.strip().upper()
    if not 2 <= len(city) <= 70 or not all(c.isalpha() or c in " .'-" for c in city):
        raise WeatherUnavailable("Provide a city name with 2 to 70 characters.")
    if not re.fullmatch(r"[A-Z]{2}", country):
        raise WeatherUnavailable("Provide a two-letter country code.")
    try:
        async with asyncio.timeout(8), httpx.AsyncClient(
            timeout=3, follow_redirects=False, trust_env=False, transport=transport
        ) as client:
            geo = await _get(client, GEOCODER, {"name": city, "countryCode": country, "count": 1, "language": "en"})
            candidates = geo.get("results") or []
            if not candidates:
                raise WeatherUnavailable("No matching city was found in that country.")
            place = candidates[0]
            if place["country_code"] != country:
                raise WeatherUnavailable("No matching city was found in that country.")
            latitude = _number(place, "latitude", -90, 90)
            longitude = _number(place, "longitude", -180, 180)
            forecast = await _get(client, FORECAST, {
                "latitude": latitude, "longitude": longitude, "current": ",".join(FIELDS),
                "timezone": "GMT", "temperature_unit": "celsius",
                "wind_speed_unit": "kmh", "precipitation_unit": "mm",
            })
            current = forecast["current"]
            timestamp = current["time"]
            code = _number(current, "weather_code", 0, 99)
            if not isinstance(timestamp, str) or not TIME.fullmatch(timestamp) or not code.is_integer():
                raise WeatherUnavailable("Open-Meteo returned an invalid observation.")
            return {
                "city": city, "country_code": country, "time_utc": timestamp + "Z",
                "temperature_c": _number(current, "temperature_2m", -100, 100),
                "precipitation_mm": _number(current, "precipitation", 0, 2000),
                "wind_kmh": _number(current, "wind_speed_10m", 0, 700),
                "condition": _condition(int(code)), "source": "Open-Meteo",
            }
    except (httpx.HTTPError, TimeoutError):
        raise WeatherUnavailable("Open-Meteo is temporarily unavailable.") from None
    except (KeyError, IndexError, TypeError, UnicodeError, json.JSONDecodeError, RecursionError):
        raise WeatherUnavailable("Open-Meteo returned an unexpected payload.") from None
