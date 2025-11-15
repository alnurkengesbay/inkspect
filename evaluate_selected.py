import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import cv2
import numpy as np
from ultralytics import YOLO

from qr_detect import detect_qr_opencv, detect_qr_pyzbar, merge_results


@dataclass
class BoundingBox:
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float = 1.0

    def as_array(self) -> np.ndarray:
        return np.array([self.x1, self.y1, self.x2, self.y2], dtype=np.float32)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate detections against selected annotations")
    parser.add_argument("annotations", type=Path, help="Path to selected_annotations.json")
    parser.add_argument("images_root", type=Path, help="Root directory with JPEG pages grouped by PDF name")
    parser.add_argument("weights", type=Path, help="Path to YOLO weights for signature/stamp detection")
    parser.add_argument("--iou", type=float, default=0.5, help="IoU threshold for TP matching (default: 0.5)")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold for YOLO predictions")
    return parser.parse_args()


def load_annotations(path: Path) -> Dict[str, Dict[int, Dict]]:
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    parsed: Dict[str, Dict[int, Dict]] = {}
    for pdf_name, pages in raw.items():
        parsed[pdf_name] = {}
        for page_key, info in pages.items():
            page_idx = int(page_key.split("_")[-1])
            parsed[pdf_name][page_idx] = info
    return parsed


def scale_bbox(bbox: Dict[str, float], scale_x: float, scale_y: float) -> BoundingBox:
    x1 = bbox["x"] * scale_x
    y1 = bbox["y"] * scale_y
    x2 = (bbox["x"] + bbox["width"]) * scale_x
    y2 = (bbox["y"] + bbox["height"]) * scale_y
    return BoundingBox(x1, y1, x2, y2)


def compute_iou(box_a: BoundingBox, box_b: BoundingBox) -> float:
    a = box_a.as_array()
    b = box_b.as_array()
    inter = np.array([
        max(a[0], b[0]),
        max(a[1], b[1]),
        min(a[2], b[2]),
        min(a[3], b[3]),
    ])
    inter_w = max(0.0, inter[2] - inter[0])
    inter_h = max(0.0, inter[3] - inter[1])
    if inter_w == 0.0 or inter_h == 0.0:
        return 0.0
    inter_area = inter_w * inter_h
    area_a = max(0.0, (a[2] - a[0]) * (a[3] - a[1]))
    area_b = max(0.0, (b[2] - b[0]) * (b[3] - b[1]))
    union = area_a + area_b - inter_area
    return inter_area / union if union else 0.0


def match_predictions(gt_boxes: List[BoundingBox], pred_boxes: List[BoundingBox], iou_threshold: float) -> Tuple[int, int, int]:
    if not gt_boxes and not pred_boxes:
        return 0, 0, 0
    matched_gt = set()
    tp = 0
    fp = 0
    for pred in sorted(pred_boxes, key=lambda b: b.confidence, reverse=True):
        best_iou = 0.0
        best_idx = -1
        for idx, gt in enumerate(gt_boxes):
            if idx in matched_gt:
                continue
            iou = compute_iou(gt, pred)
            if iou > best_iou:
                best_iou = iou
                best_idx = idx
        if best_iou >= iou_threshold and best_idx >= 0:
            matched_gt.add(best_idx)
            tp += 1
        else:
            fp += 1
    fn = len(gt_boxes) - len(matched_gt)
    return tp, fp, fn


def gather_yolo_predictions(model: YOLO, image_path: Path, conf_threshold: float) -> Dict[str, List[BoundingBox]]:
    result = model.predict(source=str(image_path), conf=conf_threshold, verbose=False)[0]
    predictions: Dict[str, List[BoundingBox]] = defaultdict(list)
    for box, cls_id, conf in zip(result.boxes.xyxy.cpu().numpy(), result.boxes.cls.cpu().numpy(), result.boxes.conf.cpu().numpy()):
        class_name = model.names[int(cls_id)]
        predictions[class_name].append(BoundingBox(x1=float(box[0]), y1=float(box[1]), x2=float(box[2]), y2=float(box[3]), confidence=float(conf)))
    return predictions


def gather_qr_predictions(image_path: Path) -> List[BoundingBox]:
    image = cv2.imread(str(image_path))
    if image is None:
        return []
    data_cv, boxes_cv = detect_qr_opencv(image)
    data_bar, boxes_bar = detect_qr_pyzbar(image)
    _, boxes = merge_results((data_cv, boxes_cv), (data_bar, boxes_bar))
    predictions = []
    for quad in boxes:
        xs = [pt[0] for pt in quad]
        ys = [pt[1] for pt in quad]
        predictions.append(BoundingBox(x1=float(min(xs)), y1=float(min(ys)), x2=float(max(xs)), y2=float(max(ys)), confidence=1.0))
    return predictions


def evaluate(args: argparse.Namespace) -> None:
    annotations = load_annotations(args.annotations)
    model = YOLO(str(args.weights))

    metrics = {"signature": {"tp": 0, "fp": 0, "fn": 0}, "stamp": {"tp": 0, "fp": 0, "fn": 0}, "qr": {"tp": 0, "fp": 0, "fn": 0}}

    for pdf_name, pages in annotations.items():
        pdf_dir = args.images_root / Path(pdf_name).stem
        for page_idx, info in pages.items():
            image_path = pdf_dir / f"page_{page_idx:03d}.jpg"
            if not image_path.exists():
                print(f"[warn] Missing image for {pdf_name} page {page_idx}: {image_path}")
                continue

            page_width = info["page_size"]["width"]
            page_height = info["page_size"]["height"]

            image = cv2.imread(str(image_path))
            if image is None:
                print(f"[warn] Unable to read image: {image_path}")
                continue
            img_h, img_w = image.shape[:2]
            scale_x = img_w / page_width
            scale_y = img_h / page_height

            gt_boxes: Dict[str, List[BoundingBox]] = defaultdict(list)
            for annotation_entry in info.get("annotations", []):
                ann = next(iter(annotation_entry.values()))
                category = ann["category"]
                bbox = ann["bbox"]
                gt_boxes[category].append(scale_bbox(bbox, scale_x, scale_y))

            predictions = gather_yolo_predictions(model, image_path, args.conf)
            predictions.setdefault("qr", [])
            qr_preds = gather_qr_predictions(image_path)
            predictions["qr"].extend(qr_preds)

            for category in metrics.keys():
                tp, fp, fn = match_predictions(gt_boxes.get(category, []), predictions.get(category, []), args.iou)
                metrics[category]["tp"] += tp
                metrics[category]["fp"] += fp
                metrics[category]["fn"] += fn

    print("\nEvaluation results:")
    for category, values in metrics.items():
        tp = values["tp"]
        fp = values["fp"]
        fn = values["fn"]
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        support = tp + fn
        print(f"- {category:9s} | precision: {precision:.3f} | recall: {recall:.3f} | f1: {f1:.3f} | support: {support}")


if __name__ == "__main__":
    evaluate(parse_args())
