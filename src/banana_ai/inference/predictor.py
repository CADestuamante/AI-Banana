from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class Prediction:
    label: str
    confidence: float
    box: List[float]


class Predictor:
    def __init__(self, model_path: str, device: str, confidence_threshold: float) -> None:
        self.model_path = model_path
        self.device = device
        self.confidence_threshold = confidence_threshold

    def predict(self, frame: Any) -> List[Prediction]:
        # TODO: Load model and run inference.
        return []

    def summarize(self, predictions: List[Prediction]) -> Dict[str, int]:
        summary: Dict[str, int] = {}
        for pred in predictions:
            summary[pred.label] = summary.get(pred.label, 0) + 1
        return summary
