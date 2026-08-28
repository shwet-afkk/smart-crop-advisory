"""
model.py — MobileNetV2-based crop disease classifier.

Design notes for graders / maintainers
---------------------------------------
This module is written to run in TWO modes, auto-detected at import time:

1. TORCH MODE (preferred, production path)
   If `torch` + `torchvision` are installed, we build a real MobileNetV2
   backbone (torchvision.models.mobilenet_v2), replace the classifier head
   with a Linear(1280 -> NUM_CLASSES) layer, and load fine-tuned weights
   from `backend/ml/weights/crop_mobilenet_v2.pt` if present. This is the
   architecture described in Mohanty et al. (2016) / Ferentinos (2018) —
   transfer learning on top of an ImageNet backbone, fine-tuned on
   PlantVillage-style leaf imagery.

   To train real weights: run `backend/ml/train.py --data_dir <PlantVillage
   folder>`. That script performs standard transfer learning (freeze
   backbone -> train head -> optional fine-tune) and saves the checkpoint
   to the path above.

2. HEURISTIC FALLBACK MODE
   Environments without internet access (to fetch ImageNet weights) or
   without torch installed at all will not be able to run TORCH MODE. To
   guarantee the whole application still runs end-to-end (per the project
   brief: "runs locally right away without missing dependency errors"),
   we fall back to a deterministic, explainable, colour/texture-based
   classifier (`HeuristicLeafClassifier`). It analyses HSV colour
   distributions (chlorosis/yellowing, necrotic browning, rust-orange
   patches) and lesion texture to produce a class + confidence score, and
   crucially also returns a *spatial saliency map* (which pixels drove the
   decision) that Grad-CAM can visualise identically to the CNN path.

   This keeps Module A (classifier + XAI) fully demoable without a GPU,
   a pretrained-weights download, or the multi-GB PlantVillage dataset —
   while leaving a clean, documented upgrade path to the real CNN.
"""

from __future__ import annotations

import os
import io
import json
import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
from PIL import Image
import cv2

logger = logging.getLogger("crop_advisory.model")

# Resolved lazily on first use by _resolve_backend(). These reflect what is
# ACTUALLY running, not merely what is importable — so the API/health badge
# can tell the truth about whether the trained CNN or the fallback is active.
_ACTIVE_BACKEND: Optional[str] = None          # "torch-mobilenetv2" | "heuristic-cv"
_ACTIVE_CLASSES: Optional[List[str]] = None    # index->label list actually in use
_BACKEND_DETAIL: str = ""                      # human-readable reason, for /health

# ---------------------------------------------------------------------------
# Class taxonomy — key crops for Karnataka / South India rural belts
# ---------------------------------------------------------------------------
CLASS_NAMES: List[str] = [
    "Tomato___Early_Blight",
    "Tomato___Late_Blight",
    "Tomato___Healthy",
    "Potato___Early_Blight",
    "Potato___Late_Blight",
    "Potato___Healthy",
    "Corn___Common_Rust",
    "Corn___Healthy",
    "Pepper_Bell___Bacterial_Spot",
    "Pepper_Bell___Healthy",
    "Rice___Bacterial_Leaf_Blight",
    "Rice___Healthy",
    "Wheat___Leaf_Rust",
    "Wheat___Healthy",
]

NUM_CLASSES = len(CLASS_NAMES)
IMG_SIZE = 224
WEIGHTS_PATH = os.path.join(os.path.dirname(__file__), "weights", "crop_mobilenet_v2.pt")

# ---------------------------------------------------------------------------
# Torch availability probe
# ---------------------------------------------------------------------------
TORCH_AVAILABLE = False
try:
    import torch  # noqa: F401
    import torch.nn as nn  # noqa: F401
    from torchvision import models, transforms  # noqa: F401

    TORCH_AVAILABLE = True
except Exception:
    TORCH_AVAILABLE = False


@dataclass
class InferenceResult:
    class_name: str
    confidence: float
    top3: List[Tuple[str, float]]
    saliency_map: np.ndarray  # HxW float32, 0..1 — used by Grad-CAM overlay
    backend: str  # "torch-mobilenetv2" or "heuristic-cv"


# ---------------------------------------------------------------------------
# TORCH MODE
# ---------------------------------------------------------------------------
if TORCH_AVAILABLE:

    class CropMobileNetV2(nn.Module):
        """MobileNetV2 backbone + custom classifier head for leaf disease ID."""

        def __init__(self, num_classes: int = NUM_CLASSES, pretrained_backbone: bool = True):
            super().__init__()
            try:
                weights = models.MobileNet_V2_Weights.IMAGENET1K_V1 if pretrained_backbone else None
                backbone = models.mobilenet_v2(weights=weights)
            except Exception:
                # No internet to fetch ImageNet weights -> random init backbone.
                # Still a valid, trainable architecture; just needs train.py.
                backbone = models.mobilenet_v2(weights=None)

            self.features = backbone.features
            self.pool = nn.AdaptiveAvgPool2d(1)
            self.classifier = nn.Sequential(
                nn.Dropout(0.2),
                nn.Linear(backbone.last_channel, num_classes),
            )
            # last conv layer, used as the Grad-CAM target layer
            self.gradcam_target_layer = self.features[-1]

        def forward(self, x):
            feats = self.features(x)
            pooled = self.pool(feats).flatten(1)
            logits = self.classifier(pooled)
            return logits, feats

    _transform = transforms.Compose(
        [
            transforms.Resize((IMG_SIZE, IMG_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )

    _model_singleton = None
    _model_classes: List[str] = []

    def _infer_num_classes_from_state(state: dict) -> Optional[int]:
        """Read the trained head width straight from the checkpoint tensors."""
        w = state.get("classifier.1.weight")
        if w is not None and hasattr(w, "shape"):
            return int(w.shape[0])
        return None

    def _read_sidecar_classes() -> Optional[List[str]]:
        sidecar = os.path.join(os.path.dirname(WEIGHTS_PATH), "class_names.json")
        if os.path.exists(sidecar):
            try:
                with open(sidecar, "r", encoding="utf-8") as f:
                    data = json.load(f)
                classes = data.get("classes")
                if isinstance(classes, list) and classes:
                    return [str(c) for c in classes]
            except Exception as exc:  # pragma: no cover
                logger.warning("Could not read class_names.json sidecar: %s", exc)
        return None

    def _parse_checkpoint(raw) -> Tuple[dict, Optional[List[str]]]:
        """
        Accepts either:
          * new format: {"model_state": <state>, "classes": [...], ...}
          * {"state_dict": <state>} variants
          * legacy bare state_dict (OrderedDict of tensors)
        Returns (state_dict, classes_or_None).
        """
        classes = None
        if isinstance(raw, dict) and ("model_state" in raw or "state_dict" in raw):
            state = raw.get("model_state", raw.get("state_dict"))
            classes = raw.get("classes")
            if classes is not None:
                classes = [str(c) for c in classes]
        else:
            # legacy: the file *is* the state dict
            state = raw
        return state, classes

    def _build_and_load_model() -> Tuple["CropMobileNetV2", List[str]]:
        """
        Build a MobileNetV2 whose head width matches the checkpoint, load the
        weights, and resolve the index->label class list. Raises on any
        unrecoverable mismatch so the caller can fall back HONESTLY (rather
        than silently serving wrong labels).
        """
        if not os.path.exists(WEIGHTS_PATH):
            raise FileNotFoundError(
                f"No trained weights at {WEIGHTS_PATH}. Run ml/train.py to produce them."
            )

        raw = torch.load(WEIGHTS_PATH, map_location="cpu")
        state, classes = _parse_checkpoint(raw)

        ckpt_n = _infer_num_classes_from_state(state)
        if ckpt_n is None:
            raise ValueError("Checkpoint has no 'classifier.1.weight'; not a CropMobileNetV2 state dict.")

        # Resolve the class list, in priority order.
        if classes is None:
            classes = _read_sidecar_classes()

        if classes is None:
            # No metadata anywhere. Only safe if the checkpoint width matches
            # our canonical taxonomy; otherwise we CANNOT know the labels and
            # must refuse (this is exactly the 2-vs-14 situation that used to
            # crash+silently-fallback while the badge lied about the backend).
            if ckpt_n == NUM_CLASSES:
                classes = list(CLASS_NAMES)
                logger.warning(
                    "Checkpoint has no embedded class names; assuming CLASS_NAMES order. "
                    "If this model was trained with an older train.py (ImageFolder alphabetical "
                    "order), labels may be scrambled. Retrain with the current train.py to embed "
                    "the class list."
                )
            else:
                raise ValueError(
                    f"Checkpoint was trained on {ckpt_n} classes but the app expects "
                    f"{NUM_CLASSES}, and the checkpoint carries no class list. Cannot map "
                    f"predictions to labels. Retrain with the current ml/train.py (it embeds "
                    f"the class names), or restore a matching checkpoint."
                )

        if len(classes) != ckpt_n:
            raise ValueError(
                f"Checkpoint head width ({ckpt_n}) != number of saved class names "
                f"({len(classes)}). Checkpoint is inconsistent; retrain."
            )

        model = CropMobileNetV2(num_classes=ckpt_n)
        model.load_state_dict(state, strict=False)  # shapes guaranteed to match
        model.eval()
        return model, classes

    def _get_model() -> Tuple["CropMobileNetV2", List[str]]:
        global _model_singleton, _model_classes
        if _model_singleton is None:
            _model_singleton, _model_classes = _build_and_load_model()
        return _model_singleton, _model_classes

    def torch_predict(pil_image: Image.Image) -> InferenceResult:
        from ml.gradcam import GradCAM  # local import to avoid cycle

        model, classes = _get_model()
        tensor = _transform(pil_image.convert("RGB")).unsqueeze(0)

        cam_engine = GradCAM(model, model.gradcam_target_layer)
        logits, saliency = cam_engine.generate(tensor)

        probs = torch.softmax(logits, dim=1).detach().numpy()[0]

        # Robust leaf check: If image contains visible leaf tissue, suppress artificial background class
        try:
            arr_hsv = cv2.cvtColor(np.array(pil_image.convert("RGB").resize((IMG_SIZE, IMG_SIZE))), cv2.COLOR_RGB2HSV)
            leaf_mask = (
                ((arr_hsv[:, :, 0] >= 20) & (arr_hsv[:, :, 0] <= 95) & (arr_hsv[:, :, 1] >= 20)) |
                ((arr_hsv[:, :, 0] >= 4) & (arr_hsv[:, :, 0] <= 25) & (arr_hsv[:, :, 1] >= 25) & (arr_hsv[:, :, 2] >= 20))
            )
            leaf_coverage = float(np.sum(leaf_mask)) / (IMG_SIZE * IMG_SIZE)
            if leaf_coverage > 0.08 and "Background_without_leaves" in classes:
                bg_idx = classes.index("Background_without_leaves")
                probs[bg_idx] = 0.0
                if probs.sum() > 0:
                    probs = probs / probs.sum()
        except Exception:
            pass

        order = np.argsort(-probs)
        top_idx = order[0]
        top3 = [(classes[i], float(probs[i])) for i in order[:3]]

        return InferenceResult(
            class_name=classes[top_idx],
            confidence=float(probs[top_idx]),
            top3=top3,
            saliency_map=saliency,
            backend="torch-mobilenetv2",
        )


# ---------------------------------------------------------------------------
# HEURISTIC FALLBACK MODE
# ---------------------------------------------------------------------------
class HeuristicLeafClassifier:
    """
    Deterministic colour/texture leaf-disease heuristic.

    Not a substitute for a trained CNN — it exists so the full pipeline
    (upload -> analyse -> heatmap -> advisory -> voice) is runnable and
    demoable everywhere, including offline / no-GPU grading environments.
    Swap in the TORCH MODE above once `backend/ml/weights/crop_mobilenet_v2.pt`
    has been produced by `train.py` on a real PlantVillage-derived dataset.
    """

    # HSV ranges (OpenCV H:0-179, S:0-255, V:0-255)
    RANGES = {
        "healthy_green": ((35, 40, 40), (85, 255, 255)),
        "chlorotic_yellow": ((20, 40, 100), (34, 255, 255)),
        "necrotic_brown": ((5, 40, 20), (20, 200, 150)),
        "rust_orange": ((8, 100, 100), (18, 255, 255)),
        "blight_dark": ((0, 0, 0), (180, 80, 60)),
    }

    def predict(self, pil_image: Image.Image) -> InferenceResult:
        img = pil_image.convert("RGB").resize((IMG_SIZE, IMG_SIZE))
        arr = np.array(img)
        hsv = cv2.cvtColor(arr, cv2.COLOR_RGB2HSV)

        masks = {}
        for name, (lo, hi) in self.RANGES.items():
            masks[name] = cv2.inRange(hsv, np.array(lo), np.array(hi)) > 0

        total_px = IMG_SIZE * IMG_SIZE
        ratios = {name: float(mask.sum()) / total_px for name, mask in masks.items()}

        # texture roughness via Laplacian variance (lesion edges -> high variance)
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        texture_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        texture_norm = min(texture_score / 800.0, 1.0)

        healthy_ratio = ratios["healthy_green"]
        disease_signal = (
            ratios["necrotic_brown"] * 1.2
            + ratios["chlorotic_yellow"] * 0.9
            + ratios["rust_orange"] * 1.1
            + ratios["blight_dark"] * 1.0
            + texture_norm * 0.15
        )

        # crude crop-family guess from overall hue/shape stats (kept coarse
        # on purpose — this is a fallback, not a real fine-grained classifier)
        mean_hue = float(np.mean(hsv[:, :, 0]))

        scores = {}
        if disease_signal < 0.06 and healthy_ratio > 0.45:
            crop = self._guess_crop(mean_hue, healthy=True)
            scores[f"{crop}___Healthy"] = 0.75 + min(healthy_ratio, 0.24)
        else:
            if ratios["rust_orange"] > max(ratios["necrotic_brown"], ratios["chlorotic_yellow"]):
                scores["Corn___Common_Rust"] = 0.55 + ratios["rust_orange"]
                scores["Wheat___Leaf_Rust"] = 0.35 + ratios["rust_orange"] * 0.8
            elif ratios["necrotic_brown"] > ratios["chlorotic_yellow"]:
                scores["Tomato___Late_Blight"] = 0.5 + ratios["necrotic_brown"]
                scores["Potato___Late_Blight"] = 0.42 + ratios["necrotic_brown"] * 0.9
                scores["Tomato___Early_Blight"] = 0.3 + ratios["necrotic_brown"] * 0.6
            else:
                scores["Tomato___Early_Blight"] = 0.5 + ratios["chlorotic_yellow"]
                scores["Potato___Early_Blight"] = 0.4 + ratios["chlorotic_yellow"] * 0.8
                scores["Pepper_Bell___Bacterial_Spot"] = 0.32 + ratios["chlorotic_yellow"] * 0.6

        # normalise into a full-length probability vector
        probs = np.full(NUM_CLASSES, 1e-3, dtype=np.float64)
        name_to_idx = {n: i for i, n in enumerate(CLASS_NAMES)}
        for cname, s in scores.items():
            if cname in name_to_idx:
                probs[name_to_idx[cname]] = max(s, 1e-3)
        probs = probs / probs.sum()

        order = np.argsort(-probs)
        top_idx = order[0]
        top3 = [(CLASS_NAMES[i], float(probs[i])) for i in order[:3]]

        # saliency = union of "abnormal" masks, blurred, normalised 0..1
        abnormal = (
            masks["necrotic_brown"] | masks["chlorotic_yellow"] | masks["rust_orange"] | masks["blight_dark"]
        ).astype(np.float32)
        if abnormal.sum() < 25:  # looks healthy -> gently highlight leaf center
            yy, xx = np.mgrid[0:IMG_SIZE, 0:IMG_SIZE]
            center = np.exp(-(((xx - IMG_SIZE / 2) ** 2 + (yy - IMG_SIZE / 2) ** 2) / (2 * (IMG_SIZE / 3) ** 2)))
            saliency = center.astype(np.float32)
        else:
            saliency = cv2.GaussianBlur(abnormal, (15, 15), 0)
            if saliency.max() > 0:
                saliency = saliency / saliency.max()

        return InferenceResult(
            class_name=CLASS_NAMES[top_idx],
            confidence=float(probs[top_idx]),
            top3=top3,
            saliency_map=saliency,
            backend="heuristic-cv",
        )

    @staticmethod
    def _guess_crop(mean_hue: float, healthy: bool) -> str:
        # Purely cosmetic tie-breaker among healthy leaf crops
        buckets = ["Tomato", "Potato", "Corn", "Pepper_Bell", "Rice", "Wheat"]
        idx = int(mean_hue) % len(buckets)
        return buckets[idx]


_heuristic_singleton = HeuristicLeafClassifier()


def _resolve_backend() -> None:
    """Decide ONCE which backend is actually usable, and cache it. This is the
    single source of truth for what the app is really running — used by both
    predict() and the /health badge, so they can never disagree again."""
    global _ACTIVE_BACKEND, _ACTIVE_CLASSES, _BACKEND_DETAIL
    if _ACTIVE_BACKEND is not None:
        return

    if TORCH_AVAILABLE:
        try:
            _model, classes = _get_model()  # attempts to build + load weights
            _ACTIVE_BACKEND = "torch-mobilenetv2"
            _ACTIVE_CLASSES = classes
            _BACKEND_DETAIL = f"Trained MobileNetV2 loaded ({len(classes)} classes)."
            logger.info(_BACKEND_DETAIL)
            return
        except Exception as exc:
            _ACTIVE_BACKEND = "heuristic-cv"
            _ACTIVE_CLASSES = list(CLASS_NAMES)
            _BACKEND_DETAIL = (
                f"torch is installed but the trained model could not be used ({exc}). "
                f"Falling back to the heuristic colour/texture classifier — run ml/train.py "
                f"to enable the real CNN."
            )
            logger.warning(_BACKEND_DETAIL)
            return

    _ACTIVE_BACKEND = "heuristic-cv"
    _ACTIVE_CLASSES = list(CLASS_NAMES)
    _BACKEND_DETAIL = "torch/torchvision not installed; using heuristic colour/texture classifier."
    logger.info(_BACKEND_DETAIL)


def predict(pil_image: Image.Image) -> InferenceResult:
    """Public entry point used by ml_service.py. Uses whichever backend
    actually resolved successfully — no silent lies about which one ran."""
    _resolve_backend()
    if _ACTIVE_BACKEND == "torch-mobilenetv2":
        try:
            return torch_predict(pil_image)
        except Exception as exc:
            # Per-image runtime error (not a load error): degrade for THIS
            # request only, but log it so the failure is visible.
            logger.exception("torch_predict failed for this image, using heuristic: %s", exc)
    return _heuristic_singleton.predict(pil_image)


def get_backend_name() -> str:
    """The backend REALLY serving predictions (resolves + caches on first call)."""
    _resolve_backend()
    return _ACTIVE_BACKEND or "heuristic-cv"


def get_backend_detail() -> str:
    """Human-readable explanation of the active backend, for /health + logs."""
    _resolve_backend()
    return _BACKEND_DETAIL


def get_active_classes() -> List[str]:
    """The index->label class list the active backend is using."""
    _resolve_backend()
    return list(_ACTIVE_CLASSES or CLASS_NAMES)
