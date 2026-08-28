"""ml_service.py — Thin bridge between the FastAPI layer and backend/ml/."""

import base64
import io
import os
import sys
from typing import Tuple

from PIL import Image

# backend/ml is a sibling of backend/app — add backend/ to path once
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from ml.model import predict as ml_predict, get_backend_name, get_backend_detail  # noqa: E402
from ml.gradcam import overlay_heatmap  # noqa: E402
from app.models.schemas import ClassificationResult  # noqa: E402


def image_to_base64(pil_image: Image.Image, fmt: str = "PNG") -> str:
    buf = io.BytesIO()
    pil_image.convert("RGB").save(buf, format=fmt)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    mime = "image/png" if fmt.upper() == "PNG" else "image/jpeg"
    return f"data:{mime};base64,{b64}"


def analyze_image(image_bytes: bytes) -> Tuple[ClassificationResult, str, str]:
    """
    Runs classification + Grad-CAM overlay on raw uploaded image bytes.
    Returns: (ClassificationResult, gradcam_base64_datauri, original_base64_datauri)
    """
    pil_image = Image.open(io.BytesIO(image_bytes))
    pil_image.load()

    result = ml_predict(pil_image)

    gradcam_uri = overlay_heatmap(pil_image, result.saliency_map)
    original_uri = image_to_base64(pil_image)

    classification = ClassificationResult(
        class_id=result.class_name,
        confidence=round(result.confidence, 4),
        top3=[{"class_id": c, "confidence": round(p, 4)} for c, p in result.top3],
        model_backend=result.backend,
    )

    return classification, gradcam_uri, original_uri


def current_backend() -> str:
    return get_backend_name()


def current_backend_detail() -> str:
    return get_backend_detail()
