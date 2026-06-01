# Requirements Summary

## Core objectives
- Build a desktop application to detect and assess banana ripeness from images and video.
- Support real-time processing with low latency in varied lighting conditions.
- Automate classification to reduce human error in sorting and quality control.

## Functional scope
- Input sources: live camera (webcam/industrial camera) and local files (PNG/JPG/JPEG/video).
- AI inference: auto-activate YOLO/CNN model when input is available.
- Detection: draw bounding boxes around bananas or banana clusters.
- Classification: label ripeness classes with confidence scores.
- Live view: display processed frames and real-time counts by class.
- Reporting: store scan history and export reports by batch/day/month.
- Settings: adjust confidence threshold and camera connection parameters.

## Roles
- Operator: select input source, monitor live view, read quick statistics.
- Manager/Admin: all operator capabilities plus history access, report export,
  and system configuration changes.

## Process flow
1) Select input source (camera or file).
2) Auto-run AI detection/classification.
3) Display results and real-time statistics.
4) Store history and export reports.
