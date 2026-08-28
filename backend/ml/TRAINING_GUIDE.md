# Crop Disease Model — Training & Improvement Guide

This guide explains how to train the **MobileNetV2** classifier behind the Smart
Crop Advisory app so it produces **correct** diagnoses, using a local **NVIDIA
GPU (CUDA)**. It also explains *why the output was wrong before* and the one
thing most likely to still hurt accuracy after training (the "lab vs. field"
gap), so you can plan around it.

Read section 1 first — it changes what "good accuracy" even means for this project.

---

## 1. Why the output was wrong, and what "working" really means

There were **two separate problems**. Only the first is fixed in code; the
second is about the data you train on.

**Problem A — the trained model was never actually running.**
The checkpoint the app shipped with (`crop_mobilenet_v2.pt`) was a *placeholder
with a randomly-initialised classifier head* — its weights were never trained.
It also had no `best_val_acc` field, which the real trainer always writes, so it
was never produced by a real training run. On top of that, an earlier build had
a 2-class head loading into a 14-class app, and class indices could be scrambled
between machines. The result: the app either silently fell back to a crude
colour/texture heuristic or mapped predictions to the wrong labels — so the
"disease" and the "Environmental Risk" looked random. **This is now fixed:**
`model.py` refuses to mislabel, `train.py` stores the class list *inside* the
checkpoint, and `/api/health` reports honestly which engine is live. But you
still have to **train a real model** — the app cannot be accurate until you do.

**Problem B — PlantVillage is a lab dataset, not a field dataset.**
Almost every PlantVillage image is a single plucked leaf on a plain grey/black
background under even lighting. A model trained only on that can hit 97-99% on a
PlantVillage validation split and then **drop to roughly 40-65% on real farmer
photos** (soil, hands, sunlight, multiple leaves, blur). This domain gap is the
single biggest reason field predictions look wrong, and no amount of extra
epochs fixes it by itself.

> **Realistic expectation:** aim for **~95-99% validation accuracy on your
> held-out split** and treat **real field-photo accuracy** (section 7) as the
> number that actually matters. Ignore any claim of a fixed ">98% in the field"
> — that is not achievable from PlantVillage alone.

---

## 2. Assemble a clean 14-class dataset (this is the critical step)

The app expects **exactly these 14 classes**, and the trainer derives the class
count from the folders it finds. Your training directory must contain **these 14
sub-folders and nothing else** — if extra PlantVillage folders (e.g. other
tomato diseases) are present, the model will train on 15+ classes and won't match
the app.

```text
crop_dataset/
├── Tomato___Early_Blight/
├── Tomato___Late_Blight/
├── Tomato___Healthy/
├── Potato___Early_Blight/
├── Potato___Late_Blight/
├── Potato___Healthy/
├── Corn___Common_Rust/
├── Corn___Healthy/
├── Pepper_Bell___Bacterial_Spot/
├── Pepper_Bell___Healthy/
├── Rice___Bacterial_Leaf_Blight/
├── Rice___Healthy/
├── Wheat___Leaf_Rust/
└── Wheat___Healthy/
```

`train.py` auto-normalises common naming variants (e.g. PlantVillage's
`Corn_(maize)___Common_rust_` or `Pepper,_bell___bacterial_spot`), so you can
copy those folders in as-is — but the **four Rice/Wheat folders you add yourself
must be named exactly as above** (any capitalisation is fine).

### Where each class comes from

**PlantVillage has NO rice and NO wheat.** It covers 8 of your 14 classes; you
must source the other 6 (2 rice + 2 wheat + confirm 2 corn) elsewhere.

| Class (app) | Source | Native folder / class to grab |
| :--- | :--- | :--- |
| Tomato___Early_Blight | PlantVillage | `Tomato___Early_blight` |
| Tomato___Late_Blight | PlantVillage | `Tomato___Late_blight` |
| Tomato___Healthy | PlantVillage | `Tomato___healthy` |
| Potato___Early_Blight | PlantVillage | `Potato___Early_blight` |
| Potato___Late_Blight | PlantVillage | `Potato___Late_blight` |
| Potato___Healthy | PlantVillage | `Potato___healthy` |
| Corn___Common_Rust | PlantVillage | `Corn_(maize)___Common_rust_` |
| Corn___Healthy | PlantVillage | `Corn_(maize)___healthy` |
| Pepper_Bell___Bacterial_Spot | PlantVillage | `Pepper,_bell___Bacterial_spot` |
| Pepper_Bell___Healthy | PlantVillage | `Pepper,_bell___healthy` |
| Rice___Bacterial_Leaf_Blight | **Paddy Doctor** | `bacterial_leaf_blight` |
| Rice___Healthy | **Paddy Doctor** | `normal` |
| Wheat___Leaf_Rust | **Wheat rust dataset** | `leaf_rust` / `brown rust` (verify) |
| Wheat___Healthy | **Wheat rust dataset** | `healthy` / `healthy_wheat` (verify) |

**Recommended sources:**

- **PlantVillage** — search Kaggle for "PlantVillage" (the `abdallahalidev/plantvillage-dataset` "color" version is the usual one). Copy only the 8 folders above; do **not** copy the other tomato/corn/apple/grape/etc. folders.
- **Rice → Paddy Doctor** (`kaggle.com/competitions/paddy-disease-classification`). ~10,000 real field photos from Tamil Nadu with a `bacterial_leaf_blight` folder and a `normal` folder — use those two, rename `normal` → `Rice___Healthy` and `bacterial_leaf_blight` → `Rice___Bacterial_Leaf_Blight`. Because these are field images, they also help close the lab/field gap for rice.
- **Wheat → a wheat-rust image dataset.** Options: the Kaggle "Wheat Leaf Dataset" (classes typically *healthy* / *leaf rust* / *septoria* or *stripe rust*), the **CGIAR Computer Vision for Crop Disease** competition data (`leaf_rust`, `stem_rust`, `healthy_wheat`), or a Roboflow Universe wheat-rust set. **Verify the rust type:** *leaf rust* (brown rust, *Puccinia triticina*) is what the app's advisory describes. If a set only has *stripe/yellow rust*, either find a leaf-rust set or knowingly relabel — mislabelled training data means the app gives farmers the wrong chemical, so confirm before you train.

> **Data-quality warning:** open a dozen images from each downloaded folder and
> confirm they actually show that disease before training. Wrong labels here
> propagate all the way to the spray recommendation a farmer acts on.

### Balance and size

Aim for a **similar number of images per class** (a few hundred to a few thousand
each). PlantVillage is very imbalanced and Paddy Doctor is large, so if one class
dwarfs the others, cap it (e.g. keep ~1,500 images/class). The trainer also
applies class-weighted loss (section 6) to compensate, but rough balance still
helps. Hold back ~10-15% of each class as a **separate test set** for section 5 —
ideally real field photos.

---

## 3. Local NVIDIA GPU (CUDA) setup

**Step 1 — create a virtual environment** (from the project root):

```bat
python -m venv backend\venv
backend\venv\Scripts\activate
```

**Step 2 — check your CUDA driver.** Run `nvidia-smi`. The top-right "CUDA
Version" is the *maximum* your driver supports; you can install a PyTorch build
at or below it.

**Step 3 — install the CUDA build of PyTorch** (not the default CPU wheel). Pick
the index URL that matches your driver — `cu121` works for the vast majority of
recent NVIDIA drivers:

```bat
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install pillow numpy
```

**Step 4 — verify the GPU is visible to PyTorch:**

```bat
python -c "import torch; print(torch.__version__); print('CUDA available:', torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU only')"
```

If it prints `CUDA available: True` and your GPU name, you're set. If it says
`False`, you installed the CPU wheel — uninstall (`pip uninstall torch
torchvision`) and reinstall with the `cu121` index URL above. `train.py` picks
the GPU automatically (`cuda if torch.cuda.is_available() else cpu`) — there is
no flag to set.

**Batch size vs. GPU memory** (MobileNetV2 @ 224px is light):

| GPU VRAM | Suggested `--batch_size` |
| :--- | :--- |
| 4 GB (e.g. GTX 1650) | 16 |
| 6 GB (GTX 1660 / RTX 2060) | 32 |
| 8 GB (RTX 3060 / 4060) | 64 |
| 12 GB+ | 96-128 |

If you hit `CUDA out of memory`, halve `--batch_size`. Expect roughly **1-3
minutes per epoch** on a mid-range GPU for ~20k images — the whole run (15
epochs) is well under an hour. On Windows the data loader uses 0 worker
processes (a platform limitation), so most time is GPU-bound.

---

## 4. Run the training

From the `backend/` directory, with the venv active:

```bat
backend\venv\Scripts\python.exe ml\train.py ^
    --data_dir "D:\datasets\crop_dataset" ^
    --epochs 15 ^
    --freeze_epochs 3 ^
    --batch_size 32 ^
    --lr 0.001 ^
    --val_split 0.15
```

(`^` is the Windows line-continuation character; on Linux/Colab use `\`.)

What the flags mean:

- `--data_dir` — your clean 14-folder dataset from section 2 (**required**).
- `--epochs` — total passes over the data (15 is a good start; raise to 25-30 if val accuracy is still climbing).
- `--freeze_epochs` — warm-up epochs with the ImageNet backbone frozen (only the new head trains), before the whole network unfreezes for fine-tuning.
- `--batch_size` — from the VRAM table above.
- `--lr` — initial learning rate for the head (1e-3 is sensible).
- `--val_split` — fraction held out for validation each run (0.15 = 15%).

The script prints per-class image counts and, each time validation accuracy
improves, saves the best model. When it finishes you'll have:

- `backend/ml/weights/crop_mobilenet_v2.pt` — weights **plus** the embedded class list, image size, arch, and `best_val_acc`.
- `backend/ml/weights/class_names.json` — the sidecar class list.

Watch the log: **train accuracy rising while val accuracy stalls or falls** means
overfitting (see section 7). A healthy run has both climbing and ending close
together.

---

## 5. Evaluate what you actually built

A single accuracy number hides which classes fail. Use the included evaluator
against your **held-out test set** (section 2) — real field photos if you have
them:

```bat
backend\venv\Scripts\python.exe ml\evaluate.py --data_dir "D:\datasets\crop_test"
```

It prints overall accuracy, a **per-class precision / recall / F1 table** (flagging
any class with recall < 0.70), and a **confusion matrix** (saved as
`confusion_matrix.csv`, plus a `.png` heatmap if matplotlib is installed:
`pip install matplotlib`).

How to read it: the confusion matrix rows are the true class and columns are the
prediction, so off-diagonal clusters tell you *what gets mistaken for what*
(e.g. Early vs. Late Blight confusion is common and points to needing more/clearer
images of both). A class with high train accuracy but low test recall is
overfitting to lab conditions.

---

## 6. Techniques already built into `train.py`

| Technique | What it does |
| :--- | :--- |
| Two-phase transfer learning | Phase 1 freezes the ImageNet backbone and trains only the new classifier head; Phase 2 unfreezes the whole network at a lower rate to fine-tune. |
| Cosine-annealing LR | Smoothly decays the learning rate across epochs for stable convergence. |
| Data augmentation | RandomCrop, horizontal/vertical flips, ±25° rotation, and ColorJitter (brightness/contrast/saturation/hue) to simulate outdoor lighting. |
| Class-weighted loss | Each class's loss is weighted by `total_images / (class_images × num_classes)`, so rare classes aren't ignored in favour of common ones. |
| Class list saved with weights | The exact class order is stored inside the checkpoint and in `class_names.json`, so labels can never be scrambled across machines. |

---

## 7. Making it work better on real field photos

If validation accuracy is high but field photos still misfire, the fix is
almost always **data and augmentation**, not a bigger model:

1. **Add real field images** — the highest-impact change. Even 100-300 phone photos per crop, taken in real conditions (with soil, hands, sun, shade), mixed into training dramatically improves field accuracy. Paddy Doctor already gives you field-condition rice.
2. **Photograph the way farmers will** — if the app is used on whole plants at arm's length, don't train only on tight single-leaf crops. Match training data to real usage.
3. **Train longer with early stopping in mind** — bump `--epochs` to 25-30; if val accuracy plateaus for several epochs, the current best checkpoint is already your model.
4. **Stronger augmentation for the lab/field gap** — because PlantVillage backgrounds are uniform, consider adding random backgrounds or heavier blur/perspective jitter to `train_transform` so the model stops relying on the clean backdrop.
5. **Fix weak classes specifically** — use the section-5 confusion matrix to find the 2-3 worst classes and add images for exactly those, rather than collecting more of everything.
6. **Keep the test set honest** — never evaluate on images that appear in training, and prefer field photos for the test set so your reported number reflects real use.

---

## 8. Verify it's live in the app

1. Confirm the new checkpoint exists: `backend/ml/weights/crop_mobilenet_v2.pt` and `class_names.json`.
2. Restart the backend (`python run.py`).
3. Open `http://localhost:8000/api/health`. You want:

```json
{
  "status": "ok",
  "ml_backend": "torch-mobilenetv2",
  "ml_backend_detail": "Trained MobileNetV2 loaded (14 classes)."
}
```

If it instead says `heuristic-cv`, the weights didn't load — check the backend
log: a class-count mismatch or a corrupt file will make `model.py` refuse the
checkpoint (by design, so it never shows fake results) and fall back to the
heuristic. Re-train per section 4 and confirm the file wrote successfully.

---

## 9. Common pitfalls (recap)

- **Extra folders in `--data_dir`.** Anything beyond the 14 target folders becomes an extra class and breaks the match to the app. Copy only the 14.
- **Missing rice/wheat.** PlantVillage has neither — you must add Paddy Doctor (rice) and a wheat-rust set (section 2), or the model can't recognise those crops at all.
- **Wrong rust type / mislabelled folders.** Verify each folder's contents; wrong labels become wrong spray advice for farmers.
- **CPU wheel installed by accident.** If `torch.cuda.is_available()` is `False`, training falls back to CPU (slow) — reinstall the `cu121` build.
- **Judging success by val accuracy alone.** A great PlantVillage score can still fail in the field — trust the section-5 evaluation on real photos.
