from __future__ import annotations

import os
import shutil
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .processor import model_files_ready, run_face_morph

ROOT = Path(__file__).resolve().parents[1]
JOBS_DIR = ROOT / "jobs"
MAX_VIDEO_BYTES = int(os.getenv("MAX_VIDEO_MB", "1024")) * 1024 * 1024
MAX_IMAGE_BYTES = int(os.getenv("MAX_IMAGE_MB", "20")) * 1024 * 1024
ALLOWED_VIDEO = {".mp4", ".mov", ".webm", ".mkv"}
ALLOWED_IMAGE = {".jpg", ".jpeg", ".png", ".webp"}
jobs: dict[str, dict] = {}
jobs_lock = threading.Lock()

app = FastAPI(title="FaceMorph Studio API", version="1.0.0")
origins = [item.strip() for item in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",") if item.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["*"])


async def save_upload(upload: UploadFile, destination: Path, allowed: set[str], limit: int) -> None:
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in allowed:
        raise HTTPException(400, f"Unsupported file type: {suffix or 'unknown'}")
    size = 0
    with destination.open("wb") as output:
        while chunk := await upload.read(8 * 1024 * 1024):
            size += len(chunk)
            if size > limit:
                output.close()
                destination.unlink(missing_ok=True)
                raise HTTPException(413, "Uploaded file is larger than the configured limit.")
            output.write(chunk)
    await upload.close()


def update_job(job_id: str, status: str, processed: int, total: int, matched: int, message: str) -> None:
    with jobs_lock:
        jobs[job_id].update(status=status, processed_frames=processed, total_frames=total, matched_frames=matched, message=message, updated_at=datetime.now(timezone.utc).isoformat())


def execute(job_id: str, video: Path, source: Path, target: Path, output: Path) -> None:
    try:
        run_face_morph(video, source, target, output, lambda status, done, total, matched, message: update_job(job_id, status, done, total, matched, message))
    except Exception as error:
        update_job(job_id, "failed", jobs[job_id]["processed_frames"], jobs[job_id]["total_frames"], jobs[job_id]["matched_frames"], str(error))


@app.get("/api/health")
def health():
    return {"status": "ok", "models_ready": model_files_ready()}


@app.post("/api/jobs", status_code=202)
async def create_job(video: UploadFile = File(...), source_face: UploadFile = File(...), target_face: UploadFile = File(...), consent: bool = Form(...)):
    if not consent:
        raise HTTPException(400, "Consent confirmation is required.")
    job_id = uuid.uuid4().hex
    folder = JOBS_DIR / job_id
    folder.mkdir(parents=True, exist_ok=False)
    video_path = folder / f"input{Path(video.filename or 'video.mp4').suffix.lower()}"
    source_path = folder / f"source{Path(source_face.filename or 'source.jpg').suffix.lower()}"
    target_path = folder / f"target{Path(target_face.filename or 'target.jpg').suffix.lower()}"
    try:
        await save_upload(video, video_path, ALLOWED_VIDEO, MAX_VIDEO_BYTES)
        await save_upload(source_face, source_path, ALLOWED_IMAGE, MAX_IMAGE_BYTES)
        await save_upload(target_face, target_path, ALLOWED_IMAGE, MAX_IMAGE_BYTES)
    except Exception:
        shutil.rmtree(folder, ignore_errors=True)
        raise
    output = folder / "final.mp4"
    now = datetime.now(timezone.utc).isoformat()
    with jobs_lock:
        jobs[job_id] = {"job_id": job_id, "status": "queued", "processed_frames": 0, "total_frames": 0, "matched_frames": 0, "message": "Job queued.", "created_at": now, "updated_at": now, "output_path": str(output)}
    threading.Thread(target=execute, args=(job_id, video_path, source_path, target_path, output), daemon=True).start()
    return {"job_id": job_id, "status": "queued"}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            raise HTTPException(404, "Job not found.")
        return {key: value for key, value in job.items() if key != "output_path"}


@app.get("/api/jobs/{job_id}/output")
def get_output(job_id: str):
    return output_response(job_id, download=False)


@app.get("/api/jobs/{job_id}/download")
def download_output(job_id: str):
    return output_response(job_id, download=True)


def output_response(job_id: str, download: bool):
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            raise HTTPException(404, "Job not found.")
        if job["status"] != "completed":
            raise HTTPException(409, "The output is not ready yet.")
        path = Path(job["output_path"])
    if not path.exists():
        raise HTTPException(404, "Output file is missing.")
    if download:
        return FileResponse(path, media_type="video/mp4", filename="face-morphed-video.mp4")
    return FileResponse(path, media_type="video/mp4", headers={"Content-Disposition": "inline"})
