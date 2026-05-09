#!/usr/bin/env python3
"""Fetch current weather for a city from Open-Meteo and log it to SQLite."""

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
DB_PATH = Path.home() / ".weather-app-cli" / "weather.db"
HTTP_TIMEOUT = 10

WMO_DESCRIPTIONS: dict[int, str] = {
    0: "Clear",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="weather",
        description=(
            "Fetch current weather for a city using the free Open-Meteo API "
            "and save the result to a local SQLite database."
        ),
    )
    parser.add_argument(
        "city",
        nargs="+",
        help="city name (multi-word names do not need quotes, e.g. San Francisco)",
    )
    return parser.parse_args(argv)


def geocode(city: str) -> dict:
    response = requests.get(
        GEOCODING_URL,
        params={"name": city, "count": 1, "language": "en", "format": "json"},
        timeout=HTTP_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    results = payload.get("results") or []
    if not results:
        raise LookupError(f"city '{city}' not found")
    return results[0]


def fetch_weather(lat: float, lon: float) -> dict:
    response = requests.get(
        FORECAST_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "current": (
                "temperature_2m,relative_humidity_2m,apparent_temperature,"
                "weather_code,wind_speed_10m"
            ),
            "daily": "temperature_2m_max,temperature_2m_min",
            "timezone": "auto",
        },
        timeout=HTTP_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS weather_lookups (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              fetched_at TEXT NOT NULL,
              city_input TEXT NOT NULL,
              resolved_name TEXT NOT NULL,
              country TEXT,
              latitude REAL NOT NULL,
              longitude REAL NOT NULL,
              temperature_c REAL NOT NULL,
              apparent_temperature_c REAL,
              humidity_pct INTEGER,
              wind_speed_kmh REAL,
              weather_code INTEGER,
              weather_description TEXT,
              high_c REAL,
              low_c REAL,
              raw_json TEXT NOT NULL
            )
            """
        )
        conn.commit()


def save_record(
    db_path: Path,
    *,
    fetched_at: str,
    city_input: str,
    geo: dict,
    weather: dict,
    description: str,
) -> None:
    current = weather["current"]
    daily = weather["daily"]
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO weather_lookups (
              fetched_at, city_input, resolved_name, country,
              latitude, longitude, temperature_c, apparent_temperature_c,
              humidity_pct, wind_speed_kmh, weather_code, weather_description,
              high_c, low_c, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fetched_at,
                city_input,
                geo["name"],
                geo.get("country"),
                geo["latitude"],
                geo["longitude"],
                current["temperature_2m"],
                current.get("apparent_temperature"),
                current.get("relative_humidity_2m"),
                current.get("wind_speed_10m"),
                current.get("weather_code"),
                description,
                daily["temperature_2m_max"][0],
                daily["temperature_2m_min"][0],
                json.dumps(weather),
            ),
        )
        conn.commit()


def format_output(geo: dict, weather: dict, description: str) -> str:
    current = weather["current"]
    daily = weather["daily"]
    location = geo["name"]
    country = geo.get("country")
    header = f"{location}, {country}" if country else location
    return (
        f"{header}\n"
        f"Now: {current['temperature_2m']:.1f}°C "
        f"(feels {current['apparent_temperature']:.1f}°C) · {description}\n"
        f"Humidity: {int(current['relative_humidity_2m'])}% · "
        f"Wind: {current['wind_speed_10m']:.1f} km/h\n"
        f"Today: H {daily['temperature_2m_max'][0]:.1f}°C / "
        f"L {daily['temperature_2m_min'][0]:.1f}°C"
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    city_input = " ".join(args.city)

    try:
        geo = geocode(city_input)
        weather = fetch_weather(geo["latitude"], geo["longitude"])
        description = WMO_DESCRIPTIONS.get(
            weather["current"].get("weather_code"), "Unknown"
        )
        init_db(DB_PATH)
        save_record(
            DB_PATH,
            fetched_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            city_input=city_input,
            geo=geo,
            weather=weather,
            description=description,
        )
    except LookupError as exc:
        print(f"weather: error: {exc}", file=sys.stderr)
        return 2
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "?"
        print(f"weather: error: weather service returned {status}", file=sys.stderr)
        return 2
    except requests.RequestException:
        print("weather: error: could not reach weather service", file=sys.stderr)
        return 2

    print(format_output(geo, weather, description))
    return 0


if __name__ == "__main__":
    sys.exit(main())
