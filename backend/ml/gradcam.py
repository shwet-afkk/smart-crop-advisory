"""
gradcam.py — Explainable AI (XAI) heatmap generation.

Implements Grad-CAM (Selvaraju et al., 2017) for the torch backend: hooks
the last convolutional layer of MobileNetV2, backpropagates the winning
class score, and combines gradients + activations into a class-discriminative
localisation map — exactly the technique surveyed in Adadi & Berrada (2020)
for making CNN plant-disease decisions interpretable to agronomists.

For the heuristic fallback backend (no torch), `model.py` already produces
an equivalent spatial saliency map directly from colour/texture analysis;
`overlay_heatmap()` below is backend-agnostic and works on any HxW map in
[0, 1], whether it came from real gradients or the heuristic pipeline.
"""

from __future__ import annotations

import base64
import io
from typing import Tuple

import cv2
import numpy as np
from PIL import Image

try:
    import torch
    import torch.nn.functional as F

    TORCH_AVAILABLE = True
except Exception:
    TORCH_AVAILABLE = False


if TORCH_AVAILABLE:

    class GradCAM:
        """Hooks a target conv layer and computes a Grad-CAM saliency map."""

        def __init__(self, model, target_layer):
            self.model = model
            self.target_layer = target_layer
            self._activations = None
            self._gradients = None
            self.target_layer.register_forward_hook(self._save_activation)
            self.target_layer.register_full_backward_hook(self._save_gradient)

        def _save_activation(self, module, inp, out):
            self._activations = out.detach()

        def _save_gradient(self, module, grad_in, grad_out):
            self._gradients = grad_out[0].detach()

        def generate(self, input_tensor: "torch.Tensor") -> Tuple["torch.Tensor", np.ndarray]:
            self.model.zero_grad()
            logits, _ = self.model(input_tensor)
            class_idx = int(torch.argmax(logits, dim=1).item())
            score = logits[0, class_idx]
            score.backward(retain_graph=False)

            gradients = self._gradients[0]  # C,H,W
            activations = self._activations[0]  # C,H,W
            weights = gradients.mean(dim=(1, 2))  # C

            cam = torch.zeros(activations.shape[1:], dtype=torch.float32)
            for c, w in enumerate(weights):
                cam += w * activations[c]
            cam = F.relu(cam)
            cam = cam - cam.min()
            if cam.max() > 0:
                cam = cam / cam.max()
            cam_np = cam.numpy().astype(np.float32)
            cam_np = cv2.resize(cam_np, (input_tensor.shape[-1], input_tensor.shape[-2]))
            return logits, cam_np


def overlay_heatmap(original: Image.Image, saliency: np.ndarray, alpha: float = 0.45) -> str:
    """
    Blend a 0..1 saliency map onto the original leaf image with a
    jet colormap and return a base64-encoded PNG data URI, ready for the
    frontend HeatmapViewer component.
    """
    rgb = np.array(original.convert("RGB").resize((saliency.shape[1], saliency.shape[0])))
    heat_u8 = np.uint8(255 * np.clip(saliency, 0, 1))
    heatmap_color = cv2.applyColorMap(heat_u8, cv2.COLORMAP_JET)
    heatmap_color = cv2.cvtColor(heatmap_color, cv2.COLOR_BGR2RGB)

    blended = (rgb.astype(np.float32) * (1 - alpha) + heatmap_color.astype(np.float32) * alpha).astype(np.uint8)
    out_img = Image.fromarray(blended)

    buf = io.BytesIO()
    out_img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"
