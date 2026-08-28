"""
advisory_engine.py — Module B (Environmental Root-Cause Analysis) +
Module C (4-Pillar Advisory Knowledge Engine).

Combines the CNN disease classification with live agro-meteorological context to:
  1. Return structured 4-pillar advisory in native languages (Kannada, Hindi, English).
  2. Compute an accurate continuous Environmental Risk Score explaining why the
     disease emerged and how likely it is to spread under current microclimatic conditions.
"""

import json
from typing import Tuple, List

from app.config import KNOWLEDGE_BASE_PATH, TRANSLATIONS_PATH, DEFAULT_LANGUAGE
from app.models.schemas import Advisory, EnvironmentalRisk, WeatherContext

with open(KNOWLEDGE_BASE_PATH, "r", encoding="utf-8") as f:
    KNOWLEDGE_BASE = json.load(f)

with open(TRANSLATIONS_PATH, "r", encoding="utf-8") as f:
    TRANSLATIONS = json.load(f)


def _get_lang(language: str) -> str:
    return language if language in ("kn", "hi", "en") else DEFAULT_LANGUAGE


def _find_kb_entry(class_id: str):
    if not class_id:
        return None
    if class_id in KNOWLEDGE_BASE:
        return KNOWLEDGE_BASE[class_id]
    # Case-insensitive / alternate capitalization lookup
    cid_clean = class_id.lower().replace(" ", "_")
    for k, v in KNOWLEDGE_BASE.items():
        if k.lower().replace(" ", "_") == cid_clean:
            return v
    # Substring / prefix fallback
    for k, v in KNOWLEDGE_BASE.items():
        if cid_clean in k.lower().replace(" ", "_") or k.lower().replace(" ", "_") in cid_clean:
            return v
    return None


def get_advisory(class_id: str, language: str = "en") -> Advisory:
    lang = _get_lang(language)
    entry = _find_kb_entry(class_id)

    if entry is None:
        name_clean = class_id.replace("_", " ").replace("___", " - ")
        return Advisory(
            disease_name=name_clean,
            scientific_name="Unknown",
            root_cause="Information not available for this class. Consult your local agriculture extension officer.",
            treatment_organic="General care: spray 5ml/L neem oil, apply balanced organic compost.",
            treatment_chemical="Consult a certified agronomist for appropriate chemical treatment.",
            preventive_measures=["Scout fields regularly", "Maintain balanced irrigation", "Rotate crops"],
            severity="Moderate",
        )

    # Localized translation lookup
    translations = entry.get("translations", {})
    t_data = translations.get(lang) or translations.get("en") or {}

    disease_name = t_data.get("disease_name", entry.get("disease_name", class_id))
    root_cause = t_data.get("root_cause", entry.get("root_cause", ""))
    treatment_organic = t_data.get("treatment_organic", entry.get("treatment_organic", ""))
    treatment_chemical = t_data.get("treatment_chemical", entry.get("treatment_chemical", ""))
    preventive_measures = t_data.get("preventive_measures", entry.get("preventive_measures", []))
    severity = entry.get("severity", "Moderate")
    scientific_name = entry.get("scientific_name", "N/A")

    return Advisory(
        disease_name=disease_name,
        scientific_name=scientific_name,
        root_cause=root_cause,
        treatment_organic=treatment_organic,
        treatment_chemical=treatment_chemical,
        preventive_measures=preventive_measures,
        severity=severity,
    )


def compute_environmental_risk(class_id: str, weather: WeatherContext, language: str = "en") -> EnvironmentalRisk:
    lang = _get_lang(language)
    entry = _find_kb_entry(class_id) or {}
    thresholds = entry.get("environmental_thresholds", {}) or {}
    severity = entry.get("severity", "Moderate")
    strings = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    trigger_dict = strings.get("risk_triggers", {})

    translations = entry.get("translations", {})
    t_data = translations.get(lang) or translations.get("en") or {}
    localized_disease = t_data.get("disease_name", entry.get("disease_name", class_id))

    if severity == "Healthy" or not thresholds:
        explanation = trigger_dict.get(
            "healthy_leaf",
            "No disease detected. Current field conditions present minimal environmental risk."
        )
        return EnvironmentalRisk(
            risk_level="Low",
            risk_score=5.0,
            triggers=[explanation],
            explanation=explanation,
        )

    triggers: List[str] = []
    score = 0.0

    # 1. Biological baseline severity
    if severity == "Critical":
        score += 40.0
        triggers.append(
            trigger_dict.get("baseline_pathogen", "Pathogen severity is categorized as Critical.").format(severity=severity)
        )
    elif severity == "Moderate":
        score += 20.0

    # 2. Humidity & Spore Germination
    hum_min = thresholds.get("humidity_pct_min")
    if hum_min is not None:
        if weather.humidity_pct >= hum_min:
            score += 25.0
            triggers.append(
                trigger_dict.get(
                    "humidity_high",
                    "High humidity ({humidity}% >= {threshold}%) favours fungal/bacterial spore germination."
                ).format(humidity=round(weather.humidity_pct), threshold=hum_min)
            )
        elif weather.humidity_pct >= hum_min - 10:
            score += 12.0
            triggers.append(
                trigger_dict.get(
                    "humidity_high",
                    "Moderate-to-high humidity ({humidity}% close to {threshold}%) creates favorable moisture."
                ).format(humidity=round(weather.humidity_pct), threshold=hum_min)
            )

    # 3. Temperature & Incubation Zone
    t_min = thresholds.get("temp_c_min")
    t_max = thresholds.get("temp_c_max")
    if t_min is not None and t_max is not None:
        if t_min <= weather.temperature_c <= t_max:
            score += 25.0
            triggers.append(
                trigger_dict.get(
                    "temp_optimal",
                    "Field temperature ({temp}°C) is inside the optimal {min_temp}-{max_temp}°C pathogen incubation range."
                ).format(temp=round(weather.temperature_c, 1), min_temp=t_min, max_temp=t_max)
            )
        elif (t_min - 3.0) <= weather.temperature_c <= (t_max + 3.0):
            score += 12.0
            triggers.append(
                trigger_dict.get(
                    "temp_near",
                    "Field temperature ({temp}°C) is close to the pathogen development threshold."
                ).format(temp=round(weather.temperature_c, 1))
            )

    # 4. Rainfall & Leaf Wetness
    if weather.rain_mm > 0:
        score += 10.0
        triggers.append(
            trigger_dict.get(
                "rain_wetness",
                "Recent rainfall ({rain} mm) prolongs leaf surface wetness, accelerating infection."
            ).format(rain=round(weather.rain_mm, 1))
        )

    # 5. Wind & Airborne Spore Dispersion
    if weather.wind_speed_kmh > 12 and thresholds.get("wind_sensitive", True):
        score += 8.0
        triggers.append(
            trigger_dict.get(
                "wind_dispersion",
                "Elevated wind speed ({wind} km/h) can disperse airborne spores."
            ).format(wind=round(weather.wind_speed_kmh))
        )

    # Clamp score between 5 and 98
    score = max(5.0, min(score, 98.0))

    if score >= 70.0:
        level = "Critical"
    elif score >= 45.0:
        level = "High"
    elif score >= 20.0:
        level = "Moderate"
    else:
        level = "Low"

    # Fallback trigger if none matched
    if len(triggers) == 0 or (len(triggers) == 1 and severity == "Moderate"):
        triggers.append(
            trigger_dict.get(
                "unfavourable_weather",
                "Current weather is not strongly favourable for pathogen reproduction, but active visual symptoms require prompt treatment."
            )
        )

    level_localized = strings.get(f"risk_{level.lower()}", level)

    expl_template = strings.get(
        "risk_explanation_template",
        "Detected '{disease}' combined with today's microclimate ({temp}°C, {humidity}% RH) produces a {level} environmental risk score of {score}/100."
    )
    explanation = expl_template.format(
        disease=localized_disease,
        temp=round(weather.temperature_c, 1),
        humidity=round(weather.humidity_pct),
        level=level_localized,
        score=round(score)
    )

    return EnvironmentalRisk(
        risk_level=level,
        risk_score=round(score, 1),
        triggers=triggers,
        explanation=explanation,
    )
