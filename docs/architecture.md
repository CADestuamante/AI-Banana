# Architecture Notes

## Modules
- ui: desktop UI and live view rendering
- inference: model loading and prediction pipeline
- data: dataset utilities and data ingestion
- reporting: statistics, aggregation, and export
- storage: local history and report persistence
- utils: shared helpers (logging, config)

## High-level flow
Input -> Preprocess -> Inference -> Postprocess -> UI + Storage -> Reports
