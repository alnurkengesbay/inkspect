from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import List

import cv2

from app.core.config import settings
from app.models.job import (
    DetectionRecord,
    JobResult,
    JobStatus,
    PageResult,
    QRRecord,
)
from app.services import archive_utils
from app.services.annotator import annotate_image
from app.services.detector import DetectionBox, get_detection_service
from app.services.heatmap import generate_heatmap
from app.services.job_manager import job_manager
from app.services.pdf_utils import pdf_to_images
from app.services.qr_detector import QRDetector


qr_detector = QRDetector()


def process_job(job_id: str, upload_path: Path) -> None:
    job = job_manager.get(job_id)
    if not job:
        raise RuntimeError(f"Job {job_id} not registered")

    job_manager.mark_running(job_id)

    try:
        job_dir = job.job_dir
        input_dir = job_dir / "input"
        pages_dir = job_dir / "pages"
        annotated_dir = job_dir / "annotated"
        heatmap_dir = job_dir / "heatmaps"

        for directory in (input_dir, pages_dir, annotated_dir, heatmap_dir):
            directory.mkdir(parents=True, exist_ok=True)

        upload_target = input_dir / upload_path.name
        shutil.move(str(upload_path), upload_target)

        page_images = prepare_pages(upload_target, pages_dir)
        job.source_files = [upload_target]

        detection_service = get_detection_service()

        page_results: List[PageResult] = []
        summary_counts: dict[str, int] = {"signature": 0, "stamp": 0, "qr": 0}

        for page_path in page_images:
            try:
                relative_page = page_path.relative_to(pages_dir)
            except ValueError:
                relative_page = Path(page_path.name)

            image = cv2.imread(str(page_path))
            if image is None:
                continue

            detections = detection_service.detect(image)
            detections = filter_signature_overlaps(detections)
            qr_hits = qr_detector.detect(image)
            qr_polygons = [list(qr.polygon) for qr in qr_hits]

            annotated_target = annotated_dir / relative_page
            annotated_target.parent.mkdir(parents=True, exist_ok=True)

            annotated_path = annotate_image(
                image,
                detections,
                qr_polygons,
                annotated_target,
            )

            heatmap_path = None
            if settings.enable_heatmap:
                heatmap_target = heatmap_dir / relative_page
                heatmap_target.parent.mkdir(parents=True, exist_ok=True)
                heatmap_path = generate_heatmap(
                    image,
                    detections,
                    qr_polygons,
                    heatmap_target,
                )

            detection_records = [
                DetectionRecord(label=det.label, confidence=det.confidence, bbox=det.bbox)
                for det in detections
            ]
            qr_records = [QRRecord(text=qr.text, polygon=list(qr.polygon)) for qr in qr_hits]

            for det in detections:
                if det.label in summary_counts:
                    summary_counts[det.label] += 1
            summary_counts["qr"] += len(qr_hits)

            requires_review = analyze_review_need(detections, qr_hits)

            page_results.append(
                PageResult(
                    page_name=page_path.name,
                    source_path=page_path,
                    annotated_path=annotated_path,
                    heatmap_path=heatmap_path,
                    detections=detection_records,
                    qr_codes=qr_records,
                    requires_review=requires_review,
                )
            )

        job.pages = page_results
        job.summary = summary_counts
        job.status = JobStatus.completed
        job_manager.mark_completed(job_id)
    except Exception as exc:  # pragma: no cover - pipeline should not crash silently
        job_manager.mark_failed(job_id, str(exc))
        raise


def prepare_pages(upload_target: Path, pages_dir: Path) -> List[Path]:
    if archive_utils.is_pdf(upload_target):
        pdf_folder = pages_dir / upload_target.stem
        return pdf_to_images(upload_target, pdf_folder)

    if upload_target.suffix.lower() == ".zip":
        extracted_dir = archive_utils.extract_zip(upload_target, pages_dir / "unzipped")
        page_images: List[Path] = []
        for file_path in archive_utils.iter_supported_files(extracted_dir):
            if archive_utils.is_pdf(file_path):
                pdf_folder = pages_dir / file_path.stem
                page_images.extend(pdf_to_images(file_path, pdf_folder))
            else:
                target = pages_dir / file_path.name
                archive_utils.copy_file(file_path, target)
                page_images.append(target)
        return _sort_paths(page_images, base=pages_dir)

    if archive_utils.is_image(upload_target):
        target = pages_dir / upload_target.name
        archive_utils.copy_file(upload_target, target)
        return [target]

    raise ValueError(f"Unsupported file type: {upload_target.suffix}")


_NATURAL_PATTERN = re.compile(r"(\d+)")


def _natural_key(text: str) -> list[object]:
    lowered = text.lower()
    return [int(part) if part.isdigit() else part for part in _NATURAL_PATTERN.split(lowered)]


def _sort_paths(paths: List[Path], base: Path | None = None) -> List[Path]:
    if not paths:
        return []

    def sort_key(path: Path) -> list[object]:
        value = path
        if base is not None:
            try:
                value = path.relative_to(base)
            except ValueError:
                value = path
        return _natural_key(value.as_posix())

    return sorted(paths, key=sort_key)


def analyze_review_need(
    detections: List[DetectionBox],
    qr_hits: List,
) -> bool:
    if not detections and not qr_hits:
        return False

    review_low = max(0.0, settings.low_conf_threshold * 0.6)
    review_high = max(review_low, settings.high_conf_threshold * 0.6)

    for det in detections:
        if det.confidence < review_low:
            return True
        if review_low <= det.confidence < review_high:
            return True
    return False


def filter_signature_overlaps(detections: List[DetectionBox]) -> List[DetectionBox]:
    if not detections:
        return detections

    stamps = [det for det in detections if det.label == "stamp"]
    if not stamps:
        return detections

    filtered: List[DetectionBox] = []
    for det in detections:
        if det.label != "signature":
            filtered.append(det)
            continue

        if _signature_inside_stamp(det, stamps):
            continue
        filtered.append(det)
    return filtered


def _signature_inside_stamp(signature: DetectionBox, stamps: List[DetectionBox]) -> bool:
    sig_box = signature.bbox
    sig_area = _bbox_area(sig_box)
    if sig_area == 0:
        return False

    for stamp in stamps:
        stamp_box = stamp.bbox
        inter_area = _intersection_area(sig_box, stamp_box)
        if inter_area == 0:
            continue

        coverage = inter_area / sig_area
        if coverage >= 0.9:
            return True

        stamp_area = _bbox_area(stamp_box)
        if stamp_area == 0:
            continue
        iou = inter_area / (sig_area + stamp_area - inter_area)
        if iou >= 0.6:
            return True
    return False


def _bbox_area(box: tuple[int, int, int, int]) -> float:
    x1, y1, x2, y2 = box
    return max(0, x2 - x1) * max(0, y2 - y1)


def _intersection_area(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    if inter_x2 <= inter_x1 or inter_y2 <= inter_y1:
        return 0.0
    return (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
