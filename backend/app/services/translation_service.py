"""
translation_service.py — Multilingual voice phrase builder and natural speech intent engine
for Kannada (kn-IN), Hindi (hi-IN), and English (en-IN).

Generates pure, natural speech strings for the client Web Speech API (TTS) and
parses farmer speech transcripts (STT) into domain actions.
"""

import json
from typing import Optional, Tuple

from app.config import TRANSLATIONS_PATH, SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE
from app.models.schemas import Advisory, WeatherContext

with open(TRANSLATIONS_PATH, "r", encoding="utf-8") as f:
    TRANSLATIONS = json.load(f)


def _lang(language: Optional[str]) -> str:
    if language in SUPPORTED_LANGUAGES:
        return language
    return DEFAULT_LANGUAGE


def build_voice_summary(advisory: Advisory, confidence: float, language: str) -> str:
    lang = _lang(language)
    strings = TRANSLATIONS.get(lang, TRANSLATIONS["en"])

    if advisory.severity == "Healthy":
        crop = advisory.disease_name.replace("Healthy", "").replace("ಆರೋಗ್ಯಕರ", "").replace("स्वस्थ", "").strip()
        crop_clean = crop if crop else ("ಬೆಳೆ" if lang == "kn" else ("फसल" if lang == "hi" else "crop"))
        return strings.get("voice_healthy_template", "").format(crop=crop_clean)

    template = strings.get("voice_result_template", "")
    prevention_text = ". ".join(advisory.preventive_measures) if advisory.preventive_measures else ""
    return template.format(
        disease=advisory.disease_name,
        confidence=round(confidence * 100),
        cause=advisory.root_cause,
        organic=advisory.treatment_organic,
        chemical=advisory.treatment_chemical,
        prevention=prevention_text,
    )


# --- Multilingual Keyword Sets for Farmer Intent Matching ---

_ORGANIC_KEYWORDS = [
    "organic", "neem", "bio", "natural", "herbal", "compost", "home remedy",
    "जैविक", "नीम", "देसी", "प्राकृतिक", "वर्मीकंपोस्ट", "घरेलू", "घरेलू उपाय",
    "ಸಾವಯವ", "ಬೇವಿನ", "ಜೈವಿಕ", "ಬೇವಿನೆಣ್ಣೆ", "ಎರೆಹುಳು", "ದೇಶಿ", "ಮನೆಮದ್ದು"
]

_CHEMICAL_KEYWORDS = [
    "chemical", "pesticide", "fungicide", "spray", "mancozeb", "ridomil", "medicine", "dosage", "saaf",
    "रासायनिक", "दवा", "दवाई", "कीटनाशक", "फफूंदनाशक", "केमिकल", "छिड़काव", "मात्रा",
    "ರಾಸಾಯನಿಕ", "ಕ್ರಿಮಿನಾಶಕ", "ಕೀಟನಾಶಕ", "ಶಿಲೀಂಧ್ರನಾಶಕ", "ಔಷಧಿ", "ಸಿಂಪಡಿಸು", "ಸಿಂಪರಣೆ", "ಔಷಧ"
]

_PREVENTION_KEYWORDS = [
    "prevent", "prevention", "control", "stop", "avoid", "protect", "rotation", "future",
    "बचाव", "रोकथाम", "रोकें", "नियंत्रण", "सुरक्षा", "सावधानी", "उपाय",
    "ತಡೆಗಟ್ಟು", "ತಡೆಗಟ್ಟುವಿಕೆ", "ಮುನ್ನೆಚ್ಚರಿಕೆ", "ನಿಯಂತ್ರಣ", "ರಕ್ಷಣೆ", "ತಡೆ", "ಕ್ರಮಗಳು"
]

_CAUSE_KEYWORDS = [
    "cause", "why", "reason", "emerge", "origin", "how come", "happen",
    "कारण", "क्यों", "वजह", "उत्पत्ति", "फैलने", "हुआ",
    "ಏಕೆ", "ಕಾರಣ", "ಯಾಕೆ", "ಹೇಗೆ ಬಂತು", "ಮೂಲ ಕಾರಣ", "ಬಂತು"
]

_SEVERITY_KEYWORDS = [
    "severe", "severity", "danger", "risk", "critical", "bad", "serious",
    "गंभीर", "खतरा", "नुकसान", "कितना नुकसान",
    "ತೀವ್ರ", "ಅಪಾಯ", "ಗಂಭೀರ", "ಹೆಚ್ಚಾಗಿದೆಯಾ"
]

_TREATMENT_KEYWORDS = [
    "treatment", "cure", "medicine", "spray", "solution", "heal", "remedy", "what to do",
    "उपचार", "दवा", "इलाज", "दवाई", "छिड़काव", "समाधान", "क्या करें",
    "ಚಿಕಿತ್ಸೆ", "ಔಷಧ", "ಮದ್ದು", "ಪರಿಹಾರ", "ನಿವಾರಣೆ", "ಸಿಂಪಡಣೆ", "ಏನು ಮಾಡಬೇಕು"
]

_WEATHER_KEYWORDS = [
    "weather", "temperature", "humidity", "rain", "climate", "wind", "forecast", "cloud",
    "मौसम", "तापमान", "हवामान", "आर्द्रता", "बारिश", "हवा", "धूप", "बादल",
    "ಹವಾಮಾನ", "ತಾಪಮಾನ", "ಮಳೆ", "ಗಾಳಿ", "ತೇವಾಂಶ", "ಬಿಸಿಲು", "ಮೋಡ"
]

_GREETING_KEYWORDS = [
    "hello", "hi", "hey", "namaste", "namaskar", "namaskara",
    "नमस्ते", "नमस्कार", "प्रणाम",
    "ನಮಸ್ಕಾರ", "ನಮಸ್ತೆ", "ಹಲೋ", "ಹಾಯ್"
]


def handle_voice_query(
    transcript: str,
    source_language: str,
    target_language: str,
    context_advisory: Optional[Advisory],
    weather: Optional[WeatherContext]
) -> Tuple[str, str]:
    lang = _lang(target_language)
    strings = TRANSLATIONS[lang]["voice_intents"]
    text_lower = transcript.strip().lower()

    if not text_lower:
        return "greeting", strings["greeting"]

    # 1. Greetings
    if any(k in text_lower for k in _GREETING_KEYWORDS) and len(text_lower.split()) <= 3:
        return "greeting", strings["greeting"]

    # 2. Weather
    if any(k in text_lower for k in _WEATHER_KEYWORDS):
        if weather is not None:
            return "ask_weather", strings["ask_weather"].format(
                location=weather.location_name.split(",")[0],
                temp=round(weather.temperature_c, 1),
                humidity=round(weather.humidity_pct)
            )
        return "ask_weather", strings["ask_weather"].format(location="ಕ್ಷೇತ್ರ/खेत", temp=27, humidity=70)

    # 3. If disease context is present:
    if context_advisory is not None:
        disease = context_advisory.disease_name
        organic = context_advisory.treatment_organic
        chemical = context_advisory.treatment_chemical
        cause = context_advisory.root_cause
        severity = context_advisory.severity
        prevention = " ".join(context_advisory.preventive_measures[:3]) if context_advisory.preventive_measures else ""

        # Severity query
        if any(k in text_lower for k in _SEVERITY_KEYWORDS):
            return "ask_severity", strings.get("ask_severity", strings["ask_treatment"]).format(
                disease=disease, severity=severity, organic=organic, chemical=chemical
            )

        # Organic query
        if any(k in text_lower for k in _ORGANIC_KEYWORDS):
            return "ask_organic", strings["ask_organic"].format(disease=disease, organic=organic)

        # Chemical query
        if any(k in text_lower for k in _CHEMICAL_KEYWORDS):
            return "ask_chemical", strings["ask_chemical"].format(disease=disease, chemical=chemical)

        # Prevention query
        if any(k in text_lower for k in _PREVENTION_KEYWORDS):
            return "ask_prevention", strings["ask_prevention"].format(disease=disease, prevention=prevention)

        # Cause query
        if any(k in text_lower for k in _CAUSE_KEYWORDS):
            return "ask_cause", strings["ask_cause"].format(disease=disease, cause=cause)

        # General treatment query
        if any(k in text_lower for k in _TREATMENT_KEYWORDS):
            return "ask_treatment", strings["ask_treatment"].format(disease=disease, organic=organic, chemical=chemical)

        # Default disease fallback in the selected language
        return "ask_treatment", strings["ask_treatment"].format(disease=disease, organic=organic, chemical=chemical)

    # 4. Fallback when no leaf is scanned yet
    if any(k in text_lower for k in _TREATMENT_KEYWORDS + _ORGANIC_KEYWORDS + _CHEMICAL_KEYWORDS):
        if lang == "kn":
            return "prompt_scan", "ದಯವಿಟ್ಟು ಮೊದಲು ರೋಗಪೀಡಿತ ಎಲೆಯ ಫೋಟೋ ಸ್ಕ್ಯಾನ್ ಮಾಡಿ, ನಂತರ ನಾನು ಸೂಕ್ತ ಔಷಧ ತಿಳಿಸುತ್ತೇನೆ."
        elif lang == "hi":
            return "prompt_scan", "कृपया पहले रोगग्रस्त पत्ते की फोटो स्कैन करें, फिर मैं सही दवा और उपचार बताऊंगा।"
        else:
            return "prompt_scan", "Please scan a photo of the affected leaf first, then I will provide specific treatments."

    return "unknown", strings["unknown"]
