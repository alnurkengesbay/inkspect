from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import List

import cv2
import numpy as np
from ultralytics import YOLO

from app.core.config import settings


@dataclass
class DetectionBox:
    label: str
    confidence: float
    bbox: tuple[int, int, int, int]  # x1, y1, x2, y2


class DetectionService:
    def __init__(self, weights_path: Path | None = None) -> None:
        model_path = weights_path or settings.weights_path
        if not model_path.exists():
            raise FileNotFoundError(
                f"Weights file not found at {model_path}. Set DOCSCAN_WEIGHTS_PATH env var."
            )
        self.model = YOLO(str(model_path))

    def detect(self, image: np.ndarray, conf: float = 0.25) -> List[DetectionBox]:
        results = self.model.predict(image, conf=conf, verbose=False)
        boxes: List[DetectionBox] = []
        height, width = image.shape[:2]
        if not results:
            return boxes
        result = results[0]
        names = result.names
        for box in result.boxes:
            cls_id = int(box.cls.item())
            label = names.get(cls_id, str(cls_id))
            confidence = float(box.conf.item())
            x1, y1, x2, y2 = box.xyxy.squeeze().tolist()
            boxes.append(
                DetectionBox(
                    label=label,
                    confidence=confidence,
                    bbox=(
                        max(0, int(x1)),
                        max(0, int(y1)),
                        min(width - 1, int(x2)),
                        min(height - 1, int(y2)),
                    ),
                )
            )
        return boxes


@lru_cache(maxsize=1)
def get_detection_service() -> DetectionService:
    return DetectionService()
