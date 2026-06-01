# Banana AI

Desktop AI system for banana ripeness detection and quality assessment from images and video.

## Goals (from task doc)
- Ingest data from live camera or local image/video files.
- Run AI detection/classification (YOLO/CNN) with confidence scores.
- Show live view with bounding boxes and real-time statistics.
- Store scan history and export reports by batch/day/month.
- Provide configurable system settings (confidence threshold, camera config).
- Support operator and manager/admin roles.

## Structure
- docs/        Requirements and architecture notes
- configs/     Default configuration
- data/        Data placeholders (raw/processed/annotations/external)
- models/      Model weights
- reports/     Exported reports
- scripts/     Utility scripts
- src/banana_ai/ Core application code
- tests/       Test scaffolding

## Quick start (placeholder)
1) Create a Python environment
2) Install dependencies from requirements.txt
3) Run the app entry at src/banana_ai/app.py

This repository currently contains a project skeleton to be expanded with model training,
inference, and desktop UI implementation.
