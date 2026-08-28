"""config.py — Centralised app settings."""

import os

APP_NAME = "Smart Visual Crop Advisory API"
APP_VERSION = "1.0.0"

# CORS: allow the local Vite dev server + any origin in dev mode
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]
ALLOW_ALL_ORIGINS_DEV = os.getenv("ALLOW_ALL_ORIGINS", "true").lower() == "true"

# Default location: Bangalore, Karnataka (used when no GPS coords supplied)
DEFAULT_LAT = 12.9716
DEFAULT_LON = 77.5946
DEFAULT_CITY = "Bengaluru, Karnataka"

# Weather provider (Open-Meteo needs no API key)
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
DATA_DIR = os.path.join(BASE_DIR, "app", "data")
KNOWLEDGE_BASE_PATH = os.path.join(DATA_DIR, "crop_knowledge_base.json")
TRANSLATIONS_PATH = os.path.join(DATA_DIR, "translations.json")

SUPPORTED_LANGUAGES = ["kn", "hi", "en"]
DEFAULT_LANGUAGE = "kn"
