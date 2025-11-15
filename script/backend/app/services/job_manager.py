from __future__ import annotations

from datetime import datetime
from threading import Lock
from typing import Dict, Optional

from app.models.job import JobResult, JobStatus


class JobManager:
    def __init__(self) -> None:
        self._jobs: Dict[str, JobResult] = {}
        self._lock = Lock()

    def save(self, job: JobResult) -> None:
        with self._lock:
            self._jobs[job.job_id] = job

    def get(self, job_id: str) -> Optional[JobResult]:
        with self._lock:
            return self._jobs.get(job_id)

    def list_all(self) -> list[JobResult]:
        with self._lock:
            return list(self._jobs.values())

    def mark_running(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = JobStatus.running

    def mark_completed(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = JobStatus.completed
            job.completed_at = datetime.utcnow()

    def mark_failed(self, job_id: str, error: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = JobStatus.failed
            job.error = error
            job.completed_at = datetime.utcnow()


job_manager = JobManager()
