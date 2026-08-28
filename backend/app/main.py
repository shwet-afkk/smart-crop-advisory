"""
main.py — FastAPI entrypoint for the Smart Visual Crop Advisory backend.

Endpoints
---------
POST /api/analyze-crop     Image (+ optional lat/lon/language) -> full localized advisory
GET  /api/weather-context   Live agro-meteorological snapshot
POST /api/voice-query       Voice transcript -> localized voice advisory reply
GET  /api/knowledge-base    Raw knowledge base (for offline caching on frontend)
GET  /api/health            Liveness + which ML backend is active
"""

from typing import Optional

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.config import APP_NAME, APP_VERSION, ALLOWED_ORIGINS, ALLOW_ALL_ORIGINS_DEV, DEFAULT_LANGUAGE
from app.models.schemas import (
    AnalyzeCropResponse,
    WeatherContextResponse,
    VoiceQueryRequest,
    VoiceQueryResponse,
)
from app.services import ml_service, weather_service, advisory_engine, translation_service
from app.services.advisory_engine import KNOWLEDGE_BASE

app = FastAPI(title=APP_NAME, version=APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if ALLOW_ALL_ORIGINS_DEV else ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "status": "online",
        "app": APP_NAME,
        "version": APP_VERSION,
        "health_check": "/api/health",
        "docs": "/docs",
    }


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "app": APP_NAME,
        "version": APP_VERSION,
        "ml_backend": ml_service.current_backend(),
        "ml_backend_detail": ml_service.current_backend_detail(),
    }


@app.get("/api/knowledge-base")
async def get_knowledge_base():
    return KNOWLEDGE_BASE


@app.get("/api/weather-context", response_model=WeatherContextResponse)
async def weather_context(
    lat: Optional[float] = Query(default=None),
    lon: Optional[float] = Query(default=None),
    location_name: Optional[str] = Query(default=None),
):
    weather = await weather_service.fetch_weather(lat, lon, location_name)

    notes = []
    if weather.humidity_pct >= 80:
        notes.append("High humidity — elevated fungal/bacterial disease pressure expected. Scout fields today.")
    if 22 <= weather.temperature_c <= 30:
        notes.append("Warm temperatures are within the favourable range for several common leaf blights.")
    if weather.rain_mm > 0:
        notes.append("Recent rainfall increases leaf-wetness duration; avoid additional overhead irrigation.")
    if weather.wind_speed_kmh > 15:
        notes.append("Elevated wind may accelerate spread of airborne fungal spores (e.g. rust).")
    if not notes:
        notes.append("Conditions are currently within a moderate, lower-risk range for common leaf diseases.")

    return WeatherContextResponse(weather=weather, agro_notes=notes)


@app.post("/api/analyze-crop", response_model=AnalyzeCropResponse)
async def analyze_crop(
    image: UploadFile = File(...),
    lat: Optional[float] = Form(default=None),
    lon: Optional[float] = Form(default=None),
    location_name: Optional[str] = Form(default=None),
    language: str = Form(default=DEFAULT_LANGUAGE),
):
    if image.content_type not in ("image/jpeg", "image/png", "image/webp", "image/jpg"):
        raise HTTPException(status_code=400, detail="Please upload a JPEG, PNG, or WEBP image.")

    image_bytes = await image.read()
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded image file is empty.")

    try:
        classification, gradcam_uri, original_uri = ml_service.analyze_image(image_bytes)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=422, detail=f"Could not process image: {exc}")

    lang = language if language in ("kn", "hi", "en") else DEFAULT_LANGUAGE
    weather = await weather_service.fetch_weather(lat, lon, location_name)
    risk = advisory_engine.compute_environmental_risk(classification.class_id, weather, lang)
    advisory = advisory_engine.get_advisory(classification.class_id, lang)
    voice_summary = translation_service.build_voice_summary(advisory, classification.confidence, lang)

    return AnalyzeCropResponse(
        classification=classification,
        gradcam_image_base64=gradcam_uri,
        original_image_base64=original_uri,
        weather=weather,
        environmental_risk=risk,
        advisory=advisory,
        language=lang,
        voice_summary_text=voice_summary,
    )


@app.post("/api/voice-query", response_model=VoiceQueryResponse)
async def voice_query(payload: VoiceQueryRequest):
    lang = payload.target_language if payload.target_language in ("kn", "hi", "en") else DEFAULT_LANGUAGE
    context_advisory = None
    if payload.context_disease:
        context_advisory = advisory_engine.get_advisory(payload.context_disease, lang)

    weather = await weather_service.fetch_weather()

    intent, reply = translation_service.handle_voice_query(
        transcript=payload.transcript,
        source_language=payload.source_language,
        target_language=lang,
        context_advisory=context_advisory,
        weather=weather,
    )

    return VoiceQueryResponse(
        recognized_intent=intent,
        reply_text=reply,
        reply_language=lang,
    )
