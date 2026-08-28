"""schemas.py — Pydantic models for all API request/response payloads."""

from typing import List, Optional
from pydantic import BaseModel, Field


class WeatherContext(BaseModel):
    location_name: str
    latitude: float
    longitude: float
    temperature_c: float
    humidity_pct: float
    wind_speed_kmh: float
    rain_mm: float
    condition: str
    fetched_at: str
    is_fallback: bool = False  # True when live weather couldn't be fetched and
    # a regional seasonal estimate is used instead (so the UI/risk can say so).


class EnvironmentalRisk(BaseModel):
    risk_level: str  # "Low" | "Moderate" | "High" | "Critical"
    risk_score: float  # 0..100
    triggers: List[str]
    explanation: str


class Advisory(BaseModel):
    disease_name: str
    scientific_name: str
    root_cause: str
    treatment_organic: str
    treatment_chemical: str
    preventive_measures: List[str]
    severity: str  # "Healthy" | "Moderate" | "Critical"


class ClassificationResult(BaseModel):
    class_id: str
    confidence: float
    top3: List[dict]
    model_backend: str


class AnalyzeCropResponse(BaseModel):
    classification: ClassificationResult
    gradcam_image_base64: str
    original_image_base64: str
    weather: WeatherContext
    environmental_risk: EnvironmentalRisk
    advisory: Advisory
    language: str
    voice_summary_text: str


class WeatherContextResponse(BaseModel):
    weather: WeatherContext
    agro_notes: List[str]


class VoiceQueryRequest(BaseModel):
    transcript: str = Field(..., description="Raw STT transcript from the client")
    source_language: str = Field(default="kn", description="kn | hi | en")
    target_language: str = Field(default="kn", description="kn | hi | en")
    context_disease: Optional[str] = None


class VoiceQueryResponse(BaseModel):
    recognized_intent: str
    reply_text: str
    reply_language: str
