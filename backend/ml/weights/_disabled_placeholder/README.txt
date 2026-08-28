These files were an UNTRAINED PLACEHOLDER, not a real model.

Verification (2026-08-26): the checkpoint's classifier head weights are
randomly initialised (bias values sit within the +-1/sqrt(1280) = +-0.028
default-init bound; standard deviation matches a fresh uniform init), and the
file has no `best_val_acc` field, which the real trainer always writes. Loading
it made the app report a working CNN ("torch-mobilenetv2") while producing
essentially random predictions -- worse than the honest heuristic fallback.

They were moved here so the app honestly falls back to the colour/texture
heuristic (and /api/health says so) until you train a real model.

To restore (not recommended): move both files back up to backend/ml/weights/.
Training a real model per ../TRAINING_GUIDE.md will overwrite them with a proper
checkpoint in backend/ml/weights/.
