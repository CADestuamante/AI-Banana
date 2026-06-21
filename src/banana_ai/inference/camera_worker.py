"""CameraWorker — QThread đọc camera hoặc file video, chạy YOLO inference."""
from __future__ import annotations

import time
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage, QPixmap
from ultralytics import YOLO

from banana_ai.inference.predictor import Prediction


class CameraWorker(QThread):
    frame_ready = Signal(QPixmap, list, float)  # pixmap, predictions, latency_ms
    error = Signal(str)

    def __init__(
        self,
        model_path: str,
        confidence_threshold: float = 0.4,
        device: str = "0",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._model_path = model_path
        self._confidence = confidence_threshold
        self._device = device
        self._source: str | int = 0
        self._running = False
        self._paused = False

    def set_source(self, source: str | int) -> None:
        self._source = source

    def set_confidence(self, value: float) -> None:
        self._confidence = value

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        try:
            model = YOLO(self._model_path)
        except Exception as e:
            self.error.emit(f"Không tải được model: {e}")
            return

        cap = cv2.VideoCapture(self._source)
        if not cap.isOpened():
            self.error.emit(f"Không mở được nguồn: {self._source}")
            return

        self._running = True
        while self._running:
            if self._paused:
                time.sleep(0.05)
                continue

            ret, frame = cap.read()
            if not ret:
                # File video hết — loop lại
                if isinstance(self._source, str):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                break

            t0 = time.perf_counter()
            results = model(frame, conf=self._confidence, device=self._device, verbose=False)
            latency_ms = (time.perf_counter() - t0) * 1000

            predictions: List[Prediction] = []
            for r in results:
                for box in r.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    conf = float(box.conf[0])
                    cls = int(box.cls[0])
                    label = model.names[cls]
                    predictions.append(Prediction(label=label, confidence=conf, box=[x1, y1, x2, y2]))

            pixmap = _frame_to_pixmap(frame)
            self.frame_ready.emit(pixmap, predictions, latency_ms)

        cap.release()


def _frame_to_pixmap(frame: np.ndarray) -> QPixmap:
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb.shape
    img = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
    return QPixmap.fromImage(img)