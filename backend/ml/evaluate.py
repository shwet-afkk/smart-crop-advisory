"""
evaluate.py — Measure REAL per-class accuracy of a trained crop-disease model.

Training accuracy alone is misleading: a model can score 98% on a PlantVillage
holdout split (clean lab photos) yet collapse to 40-60% on real field photos.
This script tells you *which* classes actually work, using a confusion matrix
and a per-class precision / recall / F1 table.

Point --data_dir at a HELD-OUT test set structured exactly like the training set
(ImageFolder: one sub-folder per class). Ideally use real field photos the model
never saw during training — that is the number that matters for farmers.

Usage (from the backend/ directory, with your project venv active):

    python ml/evaluate.py --data_dir "D:/datasets/crop_test"

    # optional flags:
    #   --weights ml/weights/crop_mobilenet_v2.pt   (default)
    #   --batch_size 32
    #   --out ml/weights/confusion_matrix.png       (saved if matplotlib is available)

Requires: torch, torchvision (same as training). matplotlib is optional — if it
is not installed the confusion matrix is still printed as text + saved as CSV.
"""

import argparse
import json
import os
import sys

import numpy as np
import torch
from torch.utils.data import DataLoader
from torchvision import datasets, transforms

# Reuse the exact model + preprocessing the app uses, and the same folder-name
# normalisation the trainer uses, so evaluation matches production behaviour.
sys.path.insert(0, os.path.dirname(__file__))
from model import CropMobileNetV2, IMG_SIZE, WEIGHTS_PATH  # noqa: E402

try:
    from train import normalize_class_name  # reuse PlantVillage alias mapping
except Exception:
    def normalize_class_name(raw_name: str) -> str:
        return raw_name


def load_model(weights_path: str, device: torch.device):
    """Load a trained checkpoint and return (model, class_names)."""
    raw = torch.load(weights_path, map_location=device)
    if isinstance(raw, dict) and "model_state" in raw:
        state = raw["model_state"]
        classes = raw.get("classes")
    else:
        # legacy bare state_dict — fall back to the sidecar class list
        state = raw
        classes = None

    if classes is None:
        sidecar = os.path.join(os.path.dirname(weights_path), "class_names.json")
        if os.path.exists(sidecar):
            with open(sidecar, encoding="utf-8") as f:
                classes = json.load(f).get("classes")
    if not classes:
        raise SystemExit(
            "Checkpoint has no embedded class list and no class_names.json sidecar.\n"
            "Re-train with the current train.py so labels are stored WITH the weights."
        )

    model = CropMobileNetV2(num_classes=len(classes), pretrained_backbone=False)
    model.load_state_dict(state)
    model.to(device).eval()
    return model, list(classes)


def main():
    ap = argparse.ArgumentParser(description="Per-class evaluation of the crop disease model")
    ap.add_argument("--data_dir", required=True,
                    help="Held-out test set (ImageFolder: one sub-folder per class)")
    ap.add_argument("--weights", default=WEIGHTS_PATH)
    ap.add_argument("--batch_size", type=int, default=32)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(WEIGHTS_PATH), "confusion_matrix.png"))
    args = ap.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    model, classes = load_model(args.weights, device)
    class_to_idx = {c: i for i, c in enumerate(classes)}
    n = len(classes)
    print(f"Model classes ({n}): {classes}\n")

    tf = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    ds = datasets.ImageFolder(args.data_dir, transform=tf)

    # Map each dataset folder (idx) -> model class idx, via alias normalisation.
    ds_to_model = {}
    unmatched = []
    for name, ds_idx in ds.class_to_idx.items():
        canon = normalize_class_name(name)
        if canon in class_to_idx:
            ds_to_model[ds_idx] = class_to_idx[canon]
        else:
            unmatched.append(name)
    if unmatched:
        print("WARNING: these test folders don't match any model class and are ignored:")
        for u in unmatched:
            print(f"   - {u}  (normalised: {normalize_class_name(u)})")
        print("   Rename them to match the model's class list above.\n")

    loader = DataLoader(ds, batch_size=args.batch_size, shuffle=False,
                        num_workers=0 if os.name == "nt" else 2)

    cm = np.zeros((n, n), dtype=np.int64)   # rows = true, cols = predicted
    total, correct, skipped = 0, 0, 0
    with torch.no_grad():
        for imgs, ds_labels in loader:
            imgs = imgs.to(device)
            preds = model(imgs).argmax(1).cpu().numpy()
            for p, dl in zip(preds, ds_labels.numpy()):
                if dl not in ds_to_model:
                    skipped += 1
                    continue
                true_idx = ds_to_model[dl]
                cm[true_idx, p] += 1
                total += 1
                correct += int(p == true_idx)

    if total == 0:
        raise SystemExit("No evaluable images. Check that test folder names match the model classes.")

    overall = correct / total
    print("=" * 68)
    print(f"Overall accuracy: {overall * 100:.2f}%  ({correct}/{total} images"
          + (f", {skipped} skipped)" if skipped else ")"))
    print("=" * 68)

    # Per-class precision / recall / F1 (pure numpy, no sklearn dependency)
    print(f"\n{'class':32s} {'prec':>6s} {'recall':>7s} {'f1':>6s} {'support':>8s}")
    print("-" * 64)
    for i, c in enumerate(classes):
        tp = cm[i, i]
        support = cm[i, :].sum()
        pred_pos = cm[:, i].sum()
        prec = tp / pred_pos if pred_pos else 0.0
        rec = tp / support if support else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        flag = "  <-- weak" if (support and rec < 0.70) else ""
        print(f"{c:32s} {prec:6.2f} {rec:7.2f} {f1:6.2f} {support:8d}{flag}")

    # Confusion matrix as text + CSV (always) and PNG (if matplotlib present)
    print("\nConfusion matrix (rows = true, cols = predicted):")
    header = "true\\pred".ljust(14) + "".join(f"{j:>5d}" for j in range(n))
    print(header)
    for i in range(n):
        print(f"{i:>2d} {classes[i][:10]:11s}" + "".join(f"{cm[i, j]:>5d}" for j in range(n)))

    csv_path = os.path.splitext(args.out)[0] + ".csv"
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("," + ",".join(classes) + "\n")
        for i in range(n):
            f.write(classes[i] + "," + ",".join(str(int(x)) for x in cm[i]) + "\n")
    print(f"\nConfusion matrix CSV saved: {csv_path}")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        cmn = cm / cm.sum(axis=1, keepdims=True).clip(min=1)
        fig, ax = plt.subplots(figsize=(9, 8))
        im = ax.imshow(cmn, cmap="Greens", vmin=0, vmax=1)
        ax.set_xticks(range(n)); ax.set_yticks(range(n))
        ax.set_xticklabels(classes, rotation=90, fontsize=7)
        ax.set_yticklabels(classes, fontsize=7)
        ax.set_xlabel("Predicted"); ax.set_ylabel("True")
        ax.set_title(f"Normalised confusion matrix (acc {overall*100:.1f}%)")
        for i in range(n):
            for j in range(n):
                if cmn[i, j] > 0.01:
                    ax.text(j, i, f"{cmn[i, j]:.2f}", ha="center", va="center",
                            fontsize=6, color="white" if cmn[i, j] > 0.5 else "black")
        fig.colorbar(im, fraction=0.046, pad=0.04)
        fig.tight_layout()
        fig.savefig(args.out, dpi=140)
        print(f"Confusion matrix image saved: {args.out}")
    except Exception as e:
        print(f"(matplotlib not available, skipped PNG: {e})")


if __name__ == "__main__":
    main()
