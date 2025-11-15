from __future__ import annotations

from pathlib import Path
from typing import Iterable

import cv2
import numpy as np

from app.services.detector import DetectionBox
from app.services.qr_detector import Point

COLORS = {
    "signature": (0, 255, 0),
    "stamp": (255, 0, 0),
    "qr": (0, 128, 255),
}


def annotate_image(
    image: np.ndarray,
    detections: Iterable[DetectionBox],
    qr_polygons: Iterable[list[Point]],
    output_path: Path,
) -> Path:
    annotated = image.copy()

    for det in detections:
        color = COLORS.get(det.label, (0, 255, 255))
        x1, y1, x2, y2 = det.bbox
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        text = f"{det.label} {det.confidence:.2f}"
        cv2.putText(annotated, text, (x1, max(0, y1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    for polygon in qr_polygons:
        color = COLORS["qr"]
        points = np.array(polygon, dtype=np.int32)
        cv2.polylines(annotated, [points], isClosed=True, color=color, thickness=2)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), annotated)
    return output_path
