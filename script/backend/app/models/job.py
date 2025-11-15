from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from app.core.config import settings


class JobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


@dataclass
class DetectionRecord:
    label: str
    confidence: float
    bbox: tuple[int, int, int, int]


@dataclass
class QRRecord:
    text: str
    polygon: list[tuple[int, int]]


@dataclass
class PageResult:
    page_name: str
    source_path: Path
    annotated_path: Optional[Path]
    heatmap_path: Optional[Path]
    detections: List[DetectionRecord]
    qr_codes: List[QRRecord]
    requires_review: bool


@dataclass
class JobResult:
    job_id: str
    status: JobStatus
    source_files: List[Path]
    pages: List[PageResult] = field(default_factory=list)
    summary: Dict[str, int] = field(
        default_factory=lambda: {"signature": 0, "stamp": 0, "qr": 0}
    )
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    @property
    def job_dir(self) -> Path:
        return settings.media_root / "jobs" / self.job_id


def create_job_id() -> str:
    return uuid.uuid4().hex
