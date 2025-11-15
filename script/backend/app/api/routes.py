from __future__ import annotations

from typing import List

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile

from app.core.config import settings
from app.models.job import JobResult, JobStatus, create_job_id
from app.schemas.job import JobOut, job_to_schema
from app.services.job_manager import job_manager
from app.services.pipeline import process_job

router = APIRouter(prefix="/api")


@router.post("/jobs", response_model=JobOut)
async def create_job(file: UploadFile, background_tasks: BackgroundTasks) -> JobOut:
    if file.filename is None:
        raise HTTPException(status_code=400, detail="Filename is required")

    job_id = create_job_id()
    job = JobResult(job_id=job_id, status=JobStatus.pending, source_files=[])
    job_manager.save(job)

    temp_path = (settings.media_root / "tmp" / f"{job_id}_{file.filename}").resolve()
    temp_path.parent.mkdir(parents=True, exist_ok=True)

    content = await file.read()
    with temp_path.open("wb") as buffer:
        buffer.write(content)

    background_tasks.add_task(process_job, job_id, temp_path)

    return job_to_schema(job)


@router.get("/jobs", response_model=List[JobOut])
async def list_jobs() -> List[JobOut]:
    jobs = [job_to_schema(job) for job in job_manager.list_all()]
    return sorted(jobs, key=lambda item: item.created_at, reverse=True)


@router.get("/jobs/{job_id}", response_model=JobOut)
async def get_job(job_id: str) -> JobOut:
    job = job_manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job_to_schema(job)
