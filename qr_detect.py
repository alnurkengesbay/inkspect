import argparse
import math
from pathlib import Path
from typing import Iterable, List, Tuple

import cv2
import numpy as np

USE_PYZBAR = False
# Heuristic thresholds to suppress obvious false positives
MIN_QR_AREA_RATIO = 1e-3
MAX_QR_AREA_RATIO = 3e-2
MIN_SIDE_PX = 48
ASPECT_RATIO_MIN = 0.7
ASPECT_RATIO_MAX = 1.3
EDGE_RATIO_MAX = 1.25
MIN_TEXT_LENGTH = 4

try:
    from pyzbar.pyzbar import decode as zbar_decode
except ImportError:  # pragma: no cover - optional dependency
    zbar_decode = None  # type: ignore


PointList = List[Tuple[int, int]]


def _ensure_output_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def detect_qr_opencv(image: np.ndarray) -> Tuple[List[str], List[PointList]]:
    detector = cv2.QRCodeDetector()
    result = detector.detectAndDecodeMulti(image)
    data: Iterable[str]
    points = None
    if isinstance(result, tuple):
        if len(result) == 3:
            data, points, _ = result
        elif len(result) == 4:
            _, data, points, _ = result
        else:
            data, points = [], None
    else:  # pragma: no cover - unexpected signature
        data, points = result, None

    if isinstance(data, str):
        data = [data] if data else []
    elif not isinstance(data, list):  # pragma: no cover - guard for cv2 retval
        data = list(data) if data else []

    decoded: List[str] = [d for d in data if d]
    boxes: List[PointList] = []
    if points is not None and len(points) > 0:
        for quad in points:
            quad_points = [(int(x), int(y)) for x, y in quad]
            boxes.append(quad_points)
    return filter_qr_candidates(decoded, boxes, image.shape)


def detect_qr_pyzbar(image: np.ndarray) -> Tuple[List[str], List[PointList]]:
    if not USE_PYZBAR or zbar_decode is None:
        return [], []
    decoded: List[str] = []
    boxes: List[PointList] = []
    for result in zbar_decode(image):
        decoded.append(result.data.decode("utf-8", errors="ignore"))
        boxes.append([(point.x, point.y) for point in result.polygon])
    return filter_qr_candidates(decoded, boxes, image.shape)


def merge_results(primary: Tuple[List[str], List[PointList]], fallback: Tuple[List[str], List[PointList]]) -> Tuple[List[str], List[PointList]]:
    data, boxes = primary
    if data:
        return data, boxes
    return fallback


def filter_qr_candidates(
    decoded: List[str],
    boxes: List[PointList],
    image_shape: Tuple[int, int, int],
) -> Tuple[List[str], List[PointList]]:
    if not decoded or not boxes:
        return [], []

    height, width = image_shape[:2]
    image_area = max(1, height * width)

    filtered_data: List[str] = []
    filtered_boxes: List[PointList] = []

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

        edges = [
            math.hypot(quad[i][0] - quad[(i + 1) % len(quad)][0], quad[i][1] - quad[(i + 1) % len(quad)][1])
            for i in range(len(quad))
        ]
        min_edge = min(edges)
        max_edge = max(edges)
        if min_edge <= 0 or max_edge / min_edge > EDGE_RATIO_MAX:
            continue

        filtered_data.append(text)
        filtered_boxes.append(quad)

    return filtered_data, filtered_boxes


def draw_boxes(image: np.ndarray, boxes: Iterable[PointList]) -> np.ndarray:
    annotated = image.copy()
    for quad in boxes:
        for idx in range(len(quad)):
            pt1 = quad[idx]
            pt2 = quad[(idx + 1) % len(quad)]
            cv2.line(annotated, pt1, pt2, (0, 255, 0), 2)
    return annotated


def process_image(image_path: Path, output_dir: Path | None) -> None:
    image = cv2.imread(str(image_path))
    if image is None:
        print(f"[warn] Не удалось прочитать файл: {image_path}")
        return

    data_cv, boxes_cv = detect_qr_opencv(image)
    data_bar, boxes_bar = detect_qr_pyzbar(image)
    decoded, boxes = merge_results((data_cv, boxes_cv), (data_bar, boxes_bar))

    if not decoded:
        print(f"[miss] QR не найден: {image_path}")
        return

    print(f"\n[hit] QR найдено в {image_path.name}")
    for text in decoded:
        print(f"   -> {text}")

    if output_dir is not None:
        annotated_dir = _ensure_output_dir(output_dir)
        annotated = draw_boxes(image, boxes)
        out_path = annotated_dir / image_path.name
        cv2.imwrite(str(out_path), annotated)
        print(f"   saved: {out_path}")



def iter_images(source: Path) -> Iterable[Path]:
    if source.is_file():
        yield source
    else:
        for path in sorted(source.rglob("*")):
            if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}:
                yield path



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Detect QR codes using OpenCV/PyZbar")
    parser.add_argument("source", type=Path, help="Image file or directory with images")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Directory to save annotated images",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.source.exists():
        raise FileNotFoundError(f"Источник не найден: {args.source}")

    for image_path in iter_images(args.source):
        process_image(image_path, args.out)
if __name__ == "__main__":
    main()
