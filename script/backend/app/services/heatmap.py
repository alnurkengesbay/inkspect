from __future__ import annotations

from pathlib import Path
from typing import Iterable

import cv2
import numpy as np

from app.core.config import settings
from app.services.detector import DetectionBox
from app.services.qr_detector import polygon_to_bbox


def generate_heatmap(
    image: np.ndarray,
    detections: Iterable[DetectionBox],
    qr_polygons: Iterable[list[tuple[int, int]]],
    output_path: Path,
) -> Path:
    height, width = image.shape[:2]
    heatmap = np.zeros((height, width), dtype=np.float32)

    for box in detections:
        add_gaussian_to_heatmap(heatmap, box.bbox, box.confidence)

    for polygon in qr_polygons:
        x1, y1, x2, y2 = polygon_to_bbox(polygon)
        add_gaussian_to_heatmap(heatmap, (x1, y1, x2, y2), 0.9)

    if heatmap.max() > 0:
        heatmap /= heatmap.max()

    colored = cv2.applyColorMap((heatmap * 255).astype(np.uint8), cv2.COLORMAP_JET)
    overlay = cv2.addWeighted(colored, 0.6, image, 0.4, 0)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), overlay)
    return output_path


def add_gaussian_to_heatmap(
    heatmap: np.ndarray,
    bbox: tuple[int, int, int, int],
    confidence: float,
) -> None:
    x1, y1, x2, y2 = bbox
    cx = (x1 + x2) // 2
    cy = (y1 + y2) // 2
    w = max(1, x2 - x1)
    h = max(1, y2 - y1)
    sigma_x = max(1.0, w * settings.heatmap_sigma_scale)
    sigma_y = max(1.0, h * settings.heatmap_sigma_scale)

    xs = np.arange(heatmap.shape[1])
    ys = np.arange(heatmap.shape[0])
    x_grid, y_grid = np.meshgrid(xs, ys)

    gaussian = np.exp(
        -(
            ((x_grid - cx) ** 2) / (2 * sigma_x**2)
            + ((y_grid - cy) ** 2) / (2 * sigma_y**2)
        )
    )
    heatmap += gaussian * confidence
