"""weather_service.py — Live environmental context via Open-Meteo (no API key)."""

from datetime import datetime, timezone
from typing import Optional

import httpx

from app.config import OPEN_METEO_URL, DEFAULT_LAT, DEFAULT_LON, DEFAULT_CITY
from app.models.schemas import WeatherContext

# WMO weather codes -> short human-readable condition
WMO_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    80: "Rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Severe thunderstorm",
}


async def fetch_weather(lat: Optional[float] = None, lon: Optional[float] = None,
                         location_name: Optional[str] = None) -> WeatherContext:
    lat = lat if lat is not None else DEFAULT_LAT
    lon = lon if lon is not None else DEFAULT_LON
    name = location_name or DEFAULT_CITY

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation,weather_code",
        "timezone": "auto",
    }

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(OPEN_METEO_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
            current = data["current"]
            code = int(current.get("weather_code", 0))
            return WeatherContext(
                location_name=name,
                latitude=lat,
                longitude=lon,
                temperature_c=float(current.get("temperature_2m", 27.0)),
                humidity_pct=float(current.get("relative_humidity_2m", 65.0)),
                wind_speed_kmh=float(current.get("wind_speed_10m", 8.0)),
                rain_mm=float(current.get("precipitation", 0.0)),
                condition=WMO_CODES.get(code, "Unknown"),
                fetched_at=datetime.now(timezone.utc).isoformat(),
                is_fallback=False,
            )
    except Exception:
        # Network unavailable / API down -> safe agronomic default for
        # Karnataka's tropical-savanna climate so the pipeline never breaks.
        return WeatherContext(
            location_name=f"{name} (offline default estimate)",
            latitude=lat,
            longitude=lon,
            temperature_c=27.0,
            humidity_pct=72.0,
            wind_speed_kmh=9.0,
            rain_mm=0.0,
            condition="Data unavailable — using regional seasonal average",
            fetched_at=datetime.now(timezone.utc).isoformat(),
            is_fallback=True,
        )
