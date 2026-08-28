"""
train.py — High-Performance Transfer-Learning Trainer for Crop Disease MobileNetV2.

Features
--------
1. Robust PlantVillage folder name normalisation (handles 'Early_blight' vs 'Early_Blight').
2. Two-phase transfer learning (Head warmup -> Full backbone fine-tuning).
3. Class-weighted CrossEntropyLoss to tackle severe dataset class imbalance.
4. Comprehensive data augmentation (ColorJitter, RandomRotation, RandomAffine, Flips).
5. Cosine Annealing Learning Rate scheduling.
6. Checkpoint auto-packaging with embedded class names and sidecar class_names.json.

Usage
-----
    # Train locally on CPU/GPU:
    python backend/ml/train.py --data_dir /path/to/PlantVillage --epochs 15 --batch_size 32

    # Fast validation test:
    python backend/ml/train.py --data_dir /path/to/PlantVillage --epochs 5 --freeze_epochs 2
"""

import argparse
import json
import os
import sys
from typing import Dict, List, Optional

sys.path.append(os.path.dirname(__file__))

# Canonical alias mapping for standard PlantVillage folder variations
PLANTVILLAGE_ALIASES: Dict[str, str] = {
    "tomato___early_blight": "Tomato___Early_Blight",
    "tomato___late_blight": "Tomato___Late_Blight",
    "tomato___healthy": "Tomato___Healthy",
    "potato___early_blight": "Potato___Early_Blight",
    "potato___late_blight": "Potato___Late_Blight",
    "potato___healthy": "Potato___Healthy",
    "corn_(maize)___common_rust_": "Corn___Common_Rust",
    "corn___common_rust": "Corn___Common_Rust",
    "corn_(maize)___healthy": "Corn___Healthy",
    "corn___healthy": "Corn___Healthy",
    "pepper,_bell___bacterial_spot": "Pepper_Bell___Bacterial_Spot",
    "pepper_bell___bacterial_spot": "Pepper_Bell___Bacterial_Spot",
    "pepper,_bell___healthy": "Pepper_Bell___Healthy",
    "pepper_bell___healthy": "Pepper_Bell___Healthy",
    "rice___bacterial_leaf_blight": "Rice___Bacterial_Leaf_Blight",
    "rice___healthy": "Rice___Healthy",
    "wheat___leaf_rust": "Wheat___Leaf_Rust",
    "wheat___healthy": "Wheat___Healthy",
}


def normalize_class_name(raw_name: str) -> str:
    key = raw_name.strip().lower().replace(" ", "_")
    return PLANTVILLAGE_ALIASES.get(key, raw_name)


def validate_classes_against_kb(class_names: List[str]) -> None:
    kb_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "app", "data", "crop_knowledge_base.json")
    )
    try:
        with open(kb_path, "r", encoding="utf-8") as f:
            kb = json.load(f)
    except Exception as exc:
        print(f"[WARN] Could not read knowledge base for validation ({exc}).")
        return

    kb_keys = set(kb.keys())
    folder_set = set(class_names)

    missing_in_kb = sorted(folder_set - kb_keys)
    missing_folders = sorted(kb_keys - folder_set)

    if missing_in_kb:
        print("\n" + "=" * 76)
        print("[NOTICE] Discovered dataset classes without direct knowledge-base matches:")
        for c in missing_in_kb:
            print(f"    - {c}")
        print("These will train properly; default fallback advisories will be generated.")
        print("=" * 76 + "\n")
    if missing_folders:
        print(f"[INFO] {len(missing_folders)} knowledge-base classes not in training dataset: {missing_folders}")
    if not missing_in_kb:
        print(f"[OK] All {len(class_names)} dataset classes match knowledge-base keys.")


def save_checkpoint(model, class_names: List[str], img_size: int, weights_path: str, val_acc: float) -> None:
    import torch

    os.makedirs(os.path.dirname(weights_path), exist_ok=True)
    checkpoint = {
        "model_state": model.state_dict(),
        "classes": list(class_names),
        "img_size": img_size,
        "arch": "mobilenet_v2",
        "num_classes": len(class_names),
        "best_val_acc": round(float(val_acc), 4),
    }
    torch.save(checkpoint, weights_path)

    sidecar = os.path.join(os.path.dirname(weights_path), "class_names.json")
    with open(sidecar, "w", encoding="utf-8") as f:
        json.dump(
            {
                "classes": list(class_names),
                "img_size": img_size,
                "num_classes": len(class_names),
                "val_acc": round(float(val_acc), 4),
            },
            f,
            indent=2,
        )


def main():
    parser = argparse.ArgumentParser(description="Train the crop disease MobileNetV2 classifier on PlantVillage")
    parser.add_argument("--data_dir", required=True, help="Path to ImageFolder-structured dataset directory")
    parser.add_argument("--epochs", type=int, default=15, help="Total training epochs")
    parser.add_argument("--freeze_epochs", type=int, default=3, help="Warmup epochs with frozen backbone")
    parser.add_argument("--batch_size", type=int, default=32, help="Batch size for training")
    parser.add_argument("--lr", type=float, default=1e-3, help="Initial learning rate for classification head")
    parser.add_argument("--val_split", type=float, default=0.15, help="Validation set fraction")
    args = parser.parse_args()

    try:
        import torch
        import torch.nn as nn
        from torch.utils.data import DataLoader, random_split
        from torchvision import datasets, transforms
    except ImportError:
        print("ERROR: torch and torchvision are required for training. Install them via:")
        print("  pip install torch torchvision")
        sys.exit(1)

    from model import CropMobileNetV2, IMG_SIZE, WEIGHTS_PATH

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"==================================================")
    print(f"  Smart Crop Advisory — CNN Training Pipeline")
    print(f"  Compute Device: {device}")
    print(f"==================================================")

    # 1. Advanced Agricultural Data Augmentations
    train_transform = transforms.Compose([
        transforms.Resize((IMG_SIZE + 32, IMG_SIZE + 32)),
        transforms.RandomCrop((IMG_SIZE, IMG_SIZE)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomVerticalFlip(p=0.2),
        transforms.RandomRotation(degrees=25),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.05),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    val_transform = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    # 2. Load dataset
    raw_dataset = datasets.ImageFolder(args.data_dir)
    discovered_classes = [normalize_class_name(c) for c in raw_dataset.classes]
    num_classes = len(discovered_classes)

    print(f"Discovered {num_classes} classes: {discovered_classes}")
    validate_classes_against_kb(discovered_classes)

    # Split dataset
    val_size = max(1, int(len(raw_dataset) * args.val_split))
    train_size = len(raw_dataset) - val_size
    train_subset, val_subset = random_split(raw_dataset, [train_size, val_size])

    # Apply split-specific transforms
    class TransformedSubset(torch.utils.data.Dataset):
        def __init__(self, subset, transform):
            self.subset = subset
            self.transform = transform

        def __getitem__(self, idx):
            x, y = self.subset[idx]
            return self.transform(x), y

        def __len__(self):
            return len(self.subset)

    train_ds = TransformedSubset(train_subset, train_transform)
    val_ds = TransformedSubset(val_subset, val_transform)

    num_workers = 0 if os.name == "nt" else 2
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, num_workers=num_workers)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=num_workers)

    # 3. Model instantiation
    model = CropMobileNetV2(num_classes=num_classes, pretrained_backbone=True).to(device)

    # 4. Class-imbalance weighted cross-entropy
    counts = [0] * num_classes
    for _, label in raw_dataset.samples:
        counts[label] += 1
    counts_t = torch.tensor(counts, dtype=torch.float32)
    weights = counts_t.sum() / (counts_t.clamp(min=1) * num_classes)
    criterion = nn.CrossEntropyLoss(weight=weights.to(device))

    print(f"Per-class sample distribution: {dict(zip(discovered_classes, counts))}")

    def set_backbone_trainable(trainable: bool):
        for p in model.features.parameters():
            p.requires_grad = trainable

    best_val_acc = 0.0

    # 5. Training Loop
    for epoch in range(args.epochs):
        stage_frozen = epoch < args.freeze_epochs
        set_backbone_trainable(not stage_frozen)

        stage_name = "Phase 1: Head Warmup" if stage_frozen else "Phase 2: Fine-tuning Backbone"
        base_lr = args.lr if stage_frozen else args.lr * 0.1

        optimizer = torch.optim.AdamW(
            filter(lambda p: p.requires_grad, model.parameters()),
            lr=base_lr,
            weight_decay=1e-4,
        )

        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=max(1, args.epochs - args.freeze_epochs), eta_min=1e-6
        )

        # Train epoch
        model.train()
        running_loss, running_correct, seen = 0.0, 0, 0
        for imgs, labels in train_loader:
            imgs, labels = imgs.to(device), labels.to(device)
            optimizer.zero_grad()
            logits, _ = model(imgs)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * imgs.size(0)
            running_correct += (logits.argmax(1) == labels).sum().item()
            seen += imgs.size(0)

        if not stage_frozen:
            scheduler.step()

        train_acc = running_correct / max(seen, 1)

        # Validation epoch
        model.eval()
        val_correct, val_seen, val_loss = 0, 0, 0.0
        with torch.no_grad():
            for imgs, labels in val_loader:
                imgs, labels = imgs.to(device), labels.to(device)
                logits, _ = model(imgs)
                loss = criterion(logits, labels)
                val_loss += loss.item() * imgs.size(0)
                val_correct += (logits.argmax(1) == labels).sum().item()
                val_seen += imgs.size(0)

        val_acc = val_correct / max(val_seen, 1)
        avg_val_loss = val_loss / max(val_seen, 1)

        print(
            f"Epoch [{epoch + 1}/{args.epochs}] ({stage_name}) -> "
            f"Train Acc: {train_acc * 100:.1f}%, Val Acc: {val_acc * 100:.1f}%, Val Loss: {avg_val_loss:.4f}"
        )

        if val_acc >= best_val_acc:
            best_val_acc = val_acc
            save_checkpoint(model, discovered_classes, IMG_SIZE, WEIGHTS_PATH, val_acc)
            print(f"  [SAVED] New best model saved to {WEIGHTS_PATH} (Accuracy: {val_acc * 100:.2f}%)")

    print(f"\n==================================================")
    print(f"  Training Complete!")
    print(f"  Best Validation Accuracy: {best_val_acc * 100:.2f}%")
    print(f"  Model Checkpoint: {WEIGHTS_PATH}")
    print(f"==================================================")


if __name__ == "__main__":
    main()
