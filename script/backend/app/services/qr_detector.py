from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

import cv2
import numpy as np

try:
    from pyzbar.pyzbar import decode as zbar_decode
except ImportError:
    zbar_decode = None  # type: ignore


Point = Tuple[int, int]


@dataclass
class QRDetection:
    text: str
    polygon: Sequence[Point]


class QRDetector:
    def __init__(self) -> None:
        self._detector = cv2.QRCodeDetector()

    def detect(self, image: np.ndarray) -> List[QRDetection]:
        decoded_cv, boxes_cv = self._detect_opencv(image)
        if decoded_cv:
            return [QRDetection(text=t, polygon=box) for t, box in zip(decoded_cv, boxes_cv)]

        decoded_zbar, boxes_zbar = self._detect_pyzbar(image)
        return [QRDetection(text=t, polygon=box) for t, box in zip(decoded_zbar, boxes_zbar)]

    def _detect_opencv(self, image: np.ndarray) -> Tuple[List[str], List[List[Point]]]:
        result = self._detector.detectAndDecodeMulti(image)
        data: Iterable[str]
        points = None
        if isinstance(result, tuple):
            if len(result) == 3:
                data, points, _ = result
            elif len(result) == 4:
                _, data, points, _ = result
            else:  # unexpected signature
                data, points = [], None
        else:
            data, points = result, None

        if isinstance(data, str):
            data = [data] if data else []
        elif not isinstance(data, list):
            data = list(data) if data else []

        decoded = [d for d in data if d]
        boxes: List[List[Point]] = []
        if points is not None and len(points) > 0:
            for quad in points:
                boxes.append([(int(x), int(y)) for x, y in quad])
        return self._filter(decoded, boxes, image.shape)

    def _detect_pyzbar(self, image: np.ndarray) -> Tuple[List[str], List[List[Point]]]:
        if zbar_decode is None:
            return [], []
        decoded: List[str] = []
        boxes: List[List[Point]] = []
        for result in zbar_decode(image):
            decoded.append(result.data.decode("utf-8", errors="ignore"))
            boxes.append([(point.x, point.y) for point in result.polygon])
        return self._filter(decoded, boxes, image.shape)

    def _filter(
        self,
        decoded: List[str],
        boxes: List[List[Point]],
        image_shape: Tuple[int, int, int],
    ) -> Tuple[List[str], List[List[Point]]]:
        if not decoded or not boxes:
            return [], []

        height, width = image_shape[:2]
        image_area = max(1, height * width)
        filtered_data: List[str] = []
        filtered_boxes: List[List[Point]] = []

        MIN_TEXT_LENGTH = 4
        MIN_QR_AREA_RATIO = 1e-3
        MAX_QR_AREA_RATIO = 3e-2
        MIN_SIDE_PX = 48
        ASPECT_RATIO_MIN = 0.7
        ASPECT_RATIO_MAX = 1.3
        EDGE_RATIO_MAX = 1.25

        for text, quad in zip(decoded, boxes):
            if not text or len(text.strip()) < MIN_TEXT_LENGTH:
                continue

            xs = [pt[0] for pt in quad]
            ys = [pt[1] for pt in quad]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)

            width_px = max_x - min_x
            height_px = max_y - min_y
            if width_px <= 0 or height_px <= 0:
                continue
            if width_px < MIN_SIDE_PX or height_px < MIN_SIDE_PX:
                continue

            area_ratio = (width_px * height_px) / image_area
            if area_ratio < MIN_QR_AREA_RATIO or area_ratio > MAX_QR_AREA_RATIO:
                continue

            aspect_ratio = width_px / height_px if height_px else 0.0
            if not (ASPECT_RATIO_MIN <= aspect_ratio <= ASPECT_RATIO_MAX):
                continue

            edge_lengths = []
            for idx in range(len(quad)):
                x1, y1 = quad[idx]
                x2, y2 = quad[(idx + 1) % len(quad)]
                edge_lengths.append(float(np.hypot(x1 - x2, y1 - y2)))
            if not edge_lengths:
                continue
            min_edge = min(edge_lengths)
            max_edge = max(edge_lengths)
            if min_edge <= 0 or max_edge / min_edge > EDGE_RATIO_MAX:
                continue

            filtered_data.append(text)
            filtered_boxes.append(quad)

        return filtered_data, filtered_boxes


def polygon_to_bbox(points: Iterable[Point]) -> Tuple[int, int, int, int]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)
