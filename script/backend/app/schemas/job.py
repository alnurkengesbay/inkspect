from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from pydantic import BaseModel

from app.core.config import settings
from app.models.job import JobResult, PageResult


class DetectionOut(BaseModel):
    label: str
    confidence: float
    bbox: Tuple[int, int, int, int]


class QROut(BaseModel):
    text: str
    polygon: List[Tuple[int, int]]


class PageOut(BaseModel):
    page_name: str
    source_url: Optional[str]
    annotated_url: Optional[str]
    heatmap_url: Optional[str]
    detections: List[DetectionOut]
    qr_codes: List[QROut]
    requires_review: bool


class JobSummaryOut(BaseModel):
    signature: bool
    stamp: bool
    qr: bool


class JobOut(BaseModel):
    job_id: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime]
    summary: JobSummaryOut
    pages: List[PageOut]
    error: Optional[str] = None


def resolve_url(path: Optional[Path]) -> Optional[str]:
    if not path:
        return None
    try:
        relative = path.relative_to(settings.media_root)
    except ValueError:
        relative = path
    return f"/media/{str(relative).replace('\\', '/')}"


def job_to_schema(job: JobResult) -> JobOut:
    summary_data = job.summary
    summary = JobSummaryOut(
        signature=bool(summary_data.get("signature", 0)),
        stamp=bool(summary_data.get("stamp", 0)),
        qr=bool(summary_data.get("qr", 0)),
    )
    pages = [page_to_schema(job.job_id, page) for page in job.pages]
    return JobOut(
        job_id=job.job_id,
        status=job.status.value,
        created_at=job.created_at,
        completed_at=job.completed_at,
        summary=summary,
        pages=pages,
        error=job.error,
    )


def page_to_schema(job_id: str, page: PageResult) -> PageOut:
    return PageOut(
        page_name=page.page_name,
        source_url=resolve_url(page.source_path) if page.source_path else None,
        annotated_url=resolve_url(page.annotated_path) if page.annotated_path else None,
        heatmap_url=resolve_url(page.heatmap_path) if page.heatmap_path else None,
        detections=[DetectionOut(**det.__dict__) for det in page.detections],
        qr_codes=[QROut(text=qr.text, polygon=qr.polygon) for qr in page.qr_codes],
        requires_review=page.requires_review,
    )
