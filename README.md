# inkspect

## Overview

Inkspect is an end‑to‑end document inspection pipeline that ingests PDFs, converts pages to images, runs YOLOv8 object detection (stamps, signatures, QR codes), and exposes results through a FastAPI backend and a React (Vite + Tailwind) dashboard. The repo also contains utilities for dataset preparation, model training, and evaluation.

## Repository Layout

```text
.
├── data.yaml                      # YOLO dataset declaration (train/val split, class names)
├── train_detect.py                # Entry point for training a detection model with Ultralytics YOLO
├── evaluate_selected.py           # Batch evaluation helper for recorded annotations and model weights
├── pdf_to_jpeg.py                 # Utility to rasterize PDF pages into JPEGs
├── prepare_selected_training_data.py
├── qr_detect.py                   # QR-only detector helper script
├── script/
│   ├── backend/                   # FastAPI service and Python business logic
│   │   ├── app/
│   │   │   ├── main.py            # FastAPI application factory
│   │   │   ├── api/routes.py      # REST endpoints exposed to the UI
│   │   │   ├── services/          # Pipeline steps (pdf utils, detector, annotator, heatmap)
│   │   │   ├── models/            # SQLModel-style data structures (in-memory usage)
│   │   │   └── core/config.py     # Central settings (media paths, weights, poppler config)
│   │   ├── tests/test_health.py   # Smoke test for the API
│   │   └── requirements.txt       # Backend dependencies (FastAPI, Ultralytics, etc.)
│   └── frontend/                  # React dashboard (Vite, TypeScript, Tailwind)
│       ├── src/App.tsx            # High-level layout (job list + viewer)
│       ├── src/components/        # Table, viewer, uploader, confidence badges
│       └── package.json           # Frontend dependencies and scripts
└── .gitignore                     # Ensures heavy artifacts (media, runs, weights) stay out of Git
```

Generated artifacts (converted pages, YOLO heatmaps, uploads) land under `media/` (configurable) and are excluded from version control.

## Prerequisites

- Python 3.10+ (tested with CPython 3.13)
- Node.js 18+ and npm
- Git LFS (recommended if you plan to version large weights later)
- Poppler binaries (for high-quality PDF rasterization)
	- Set `POPPLER_PATH` to the folder containing `pdftoppm.exe` on Windows.
- YOLOv8 model weights (`.pt` file). By default the backend looks for:
	1. `DOCSCAN_WEIGHTS_PATH` environment variable, or
	2. `artifacts/yolov8_sign_stamp_qr_best.pt`, or
	3. `runs_custom/sign_stamp_qr/weights/best.pt`.

## Backend (FastAPI) Setup

```powershell
cd script/backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# optional: override defaults
set DOCSCAN_MEDIA_ROOT=C:\path\to\media
set DOCSCAN_WEIGHTS_PATH=C:\path\to\weights\best.pt
set POPPLER_PATH=C:\path\to\poppler\Library\bin

uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Key endpoints (visit `http://localhost:8000/docs` for the interactive schema):

- `POST /jobs/upload` – upload a document (PDF or ZIP) and kick off detection
- `GET /jobs` – list jobs with detection status and counts
- `GET /jobs/{job_id}` – retrieve detailed page-level detections, heatmaps, and metadata

The backend uses an in-memory job registry backed by the filesystem under `media/jobs`. All generated files are namespaced by a UUID job id.

### Backend Testing

```powershell
cd script/backend
pytest
```

## Frontend (React + Vite) Setup

```powershell
cd script/frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

The dashboard exposes three core panels:

- **Upload** – drag-and-drop or browse for PDFs/archives
- **Jobs Table** – sortable list of processed jobs (status, detection counts, timestamps)
- **Job Viewer** – thumbnails, detection overlays, raw metadata grouped by document

For production builds:

```powershell
cd script/frontend
npm run build
npm run preview
```

Serve the built assets from `script/frontend/dist` behind the FastAPI backend or any static file host.

## Detection & Training Utilities

The repo ships a handful of scripts to manage dataset curation and model iteration:

| Script | Purpose | Typical Usage |
| --- | --- | --- |
| `train_detect.py` | Fine-tune YOLOv8 on the dataset defined in `data.yaml`. | `python train_detect.py --model yolov8n.pt --epochs 50 --img 1024` |
| `evaluate_selected.py` | Evaluate a trained model on a curated subset of annotations. Writes metrics and confusion matrices to `runs_custom/`. | `python evaluate_selected.py selected_annotations.json pdfs_jpeg runs_custom/sign_stamp_qr/weights/best.pt` |
| `prepare_selected_training_data.py` | Filter and copy high-value samples into a new training bundle. | `python prepare_selected_training_data.py --input dataset --output dataset_filtered` |
| `pdf_to_jpeg.py` | Batch convert PDFs to page-level JPEGs (uses Poppler). Useful for bootstrap datasets. | `python pdf_to_jpeg.py --input pdfs --output pdfs_jpeg` |
| `qr_detect.py` | Lightweight QR-specific detector for benchmarking QR accuracy. | `python qr_detect.py --images pdfs_jpeg` |

Update `data.yaml` to point YOLO to the correct dataset folders (`train`, `val`, `test`) and class list before training.

## Configuration Reference

- `script/backend/app/core/config.py` centralizes runtime settings. Override with environment variables when deploying (media root, weight path, heatmap parameters).
- `script/backend/media/` (ignored) – working directory for uploaded inputs, per-job extracts, annotated outputs, heatmaps, and temp files.
- `script/media/tmp_test/` – sample pages for quick UI demos.
- `.gitignore` excludes large artifacts (`dataset/`, `runs_custom/`, `*.pt`, `media/`) to keep the repo lightweight.

## Running the Stack Together

1. Start the backend (`uvicorn app.main:app --host 0.0.0.0 --port 8000`).
2. Start the frontend dev server (`npm run dev -- --host 127.0.0.1 --port 5173`).
3. Open `http://localhost:5173` and upload a document. The UI polls the backend for job status and renders detection overlays when ready.

## Deployment Notes

- Use a process manager (systemd, Supervisor, PM2) to keep the FastAPI service alive in production.
- Configure CORS/HTTPS and reverse proxy rules (e.g., Nginx) to serve the frontend and proxy API calls to the backend port.
- Persist the `media/` directory (volume mount) if you need to retain generated jobs across restarts.
- Store model weights in a secure artifact repository or cloud bucket and point `DOCSCAN_WEIGHTS_PATH` to the download location at startup.

With the README in place the repository should now stand on its own—clone, install dependencies, drop in weights, and start scanning.