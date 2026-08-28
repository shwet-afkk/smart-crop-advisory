# 🌾 Smart Visual Crop Advisory for One-Tap Farm Decisions

**BE Computer Science Final Year Project — Visvesvaraya Technological University (VTU)**

A production-ready, full-stack agricultural advisory web app that lets a farmer photograph a
crop leaf and instantly receive an explainable disease diagnosis, the environmental root cause,
and a 4-pillar treatment plan — all read aloud in **Kannada, Hindi, or English**.

---

## 1. What this project does

1. **Snap a photo** of a leaf (camera or gallery, one tap).
2. A **CNN classifier** (MobileNetV2 transfer-learning architecture) identifies the disease.
3. A **Grad-CAM heatmap** shows *exactly which part of the leaf* drove the diagnosis (Explainable AI).
4. Live **weather data** (temperature, humidity, wind, rain) is combined with the diagnosis to
   compute an **Environmental Risk Score** and explain *why* the disease is emerging now.
5. A **4-pillar advisory** is generated: root cause, organic treatment, chemical treatment
   (with dosage), and preventive measures.
6. Everything can be **read aloud** and **queried by voice** in Kannada / Hindi / English using
   the browser's built-in Speech-to-Text / Text-to-Speech.

Academic grounding: Mohanty et al. (2016), Ferentinos (2018) for CNN plant-disease classification;
Adadi & Berrada (2020) for Grad-CAM/XAI; Afrianto et al. (2020) for the context-aware
(environment + disease) advisory gap this project addresses.

---

## 2. Project structure

```text
smart-crop-advisory/
├── backend/                 FastAPI service (Python 3.10+)
│   ├── app/
│   │   ├── main.py          All API endpoints
│   │   ├── config.py        Settings, CORS, default location (Bengaluru)
│   │   ├── models/schemas.py Pydantic request/response models
│   │   ├── services/
│   │   │   ├── ml_service.py          Bridges API <-> ml/ package
│   │   │   ├── weather_service.py     Open-Meteo live weather fetch
│   │   │   ├── advisory_engine.py     Root-cause + 4-pillar advisory logic
│   │   │   └── translation_service.py Kannada/Hindi/English voice text
│   │   └── data/
│   │       ├── crop_knowledge_base.json   14 disease classes, full advisories
│   │       └── translations.json          UI/voice phrase templates (kn/hi/en)
│   ├── ml/
│   │   ├── model.py         MobileNetV2 CNN + automatic heuristic-CV fallback
│   │   ├── gradcam.py       Grad-CAM heatmap generator
│   │   └── train.py         Standalone transfer-learning trainer
│   ├── requirements.txt
│   └── run.py
├── frontend/                 React 18 + Vite + Tailwind CSS
│   └── src/
│       ├── components/       CameraCapture, HeatmapViewer, AdvisoryCard,
│       │                     VoiceAssistant, WeatherWidget, LanguageSelector
│       ├── locales/          en.json, hi.json, kn.json
│       ├── lib/               api.js (backend client), i18n.js
│       └── App.jsx
└── README.md (this file)
```

---

## 3. Important note on the ML model (read this first)

This repository ships **two interchangeable classifier backends**, auto-selected at server
startup — the app always runs, with no missing-dependency errors:

| Backend | When it's used | What it does |
|---|---|---|
| **`torch-mobilenetv2`** | `torch` + `torchvision` are installed | Real MobileNetV2 CNN + real Grad-CAM (backprop-based). This is the production path described in the project brief. |
| **`heuristic-cv`** | torch isn't installed, or no internet access to fetch ImageNet weights | A deterministic OpenCV colour/texture analyser (HSV thresholding for chlorosis, necrosis, rust, blight + Laplacian texture) that returns an equivalent saliency map. Lets the **entire pipeline** (upload → diagnose → heatmap → advisory → voice) run anywhere, instantly, with no GPU or dataset download. |

**To use the real CNN in production:**

```bash
cd backend
pip install torch torchvision
python ml/train.py --data_dir /path/to/PlantVillage-style/dataset --epochs 10
```

This trains and saves `backend/ml/weights/crop_mobilenet_v2.pt`. The next time you start the
server, it is picked up automatically and `model_backend` in the API response switches to
`torch-mobilenetv2`. The dataset folder must follow the standard `ImageFolder` layout, with one
subfolder per class (see class names in `backend/ml/model.py::CLASS_NAMES`, matching
`crop_knowledge_base.json`).

---

## 4. Running locally

### Prerequisites
- Python 3.10+
- Node.js 18+

### Backend

```bash
cd backend
pip install -r requirements.txt
python run.py
# or: uvicorn app.main:app --reload
```

Backend runs at **http://localhost:8000**. Interactive API docs at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at **http://localhost:5173** and proxies `/api/*` to the backend automatically
(see `vite.config.js`), so no `.env` configuration is required for local development.

Open `http://localhost:5173` on your phone or laptop, allow camera/location/microphone
permissions when prompted, and tap the big gold camera button to scan a leaf.

---

## 5. API reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/analyze-crop` | multipart form: `image` (file), `lat`, `lon`, `location_name`, `language` → full diagnosis + Grad-CAM + weather + risk + advisory |
| `GET`  | `/api/weather-context?lat=&lon=` | Live agro-meteorological snapshot + human-readable risk notes |
| `POST` | `/api/voice-query` | JSON `{transcript, source_language, target_language, context_disease}` → translated reply text |
| `GET`  | `/api/knowledge-base` | Full raw disease knowledge base (for offline caching) |
| `GET`  | `/api/health` | Liveness probe + which ML backend is currently active |

---

## 6. Voice & accessibility notes

- Speech-to-Text and Text-to-Speech run **client-side** via the browser's Web Speech API
  (`SpeechRecognition` / `speechSynthesis`), so no external voice API keys are required.
  Best supported in Chrome (desktop and Android). iOS Safari has partial `SpeechRecognition`
  support; TTS (`speechSynthesis`) works broadly.
- Voice reply *text* is generated server-side from reviewed phrase templates
  (`app/data/translations.json`) rather than machine-translated on the fly, so treatment names
  and dosages are never garbled by translation — important for an agricultural safety tool.
- UI uses large touch targets, colour-coded severity badges (green/yellow/red), and high-contrast
  type for outdoor/low-literacy use, with visible keyboard focus and `prefers-reduced-motion`
  support.

---

## 7. Extending the knowledge base

Add a new crop/disease by adding an entry to both:
1. `backend/ml/model.py` → `CLASS_NAMES` list
2. `backend/app/data/crop_knowledge_base.json` → matching key with `disease_name`,
   `scientific_name`, `severity`, `root_cause`, `treatment_organic`, `treatment_chemical`,
   `preventive_measures`, and optional `environmental_thresholds`.

No frontend changes are required — the advisory card renders any class in the knowledge base
automatically.

---

## 8. Disclaimer

Chemical dosages in `crop_knowledge_base.json` are illustrative examples drawn from common
agricultural-extension guidance and **must be verified against current, locally approved product
labels and application rates** (e.g. via your State Department of Agriculture or nearest Krishi
Vigyan Kendra) before real-world use. This is an academic project, not a substitute for
professional agronomic or regulatory advice.
