"""
app.py

The real-time entry point. This is what your teammates' agents will
eventually sit behind too, but for your part it does one job:

  1. User uploads a PDF -> respond immediately with a job_id
     (never make the user's browser sit on an open request for
     minutes while a 500-page PDF processes).
  2. Extraction runs in the background.
  3. Frontend polls GET /status/{job_id} to show progress.
  4. Once done, GET /result/{job_id} returns the extracted data.

Run with:
    uvicorn app:app --reload
"""

import os
import uuid
import hashlib
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from extractor import run_extraction

app = FastAPI(title="OmniBrain Vision Extraction Service")

UPLOAD_DIR = "uploads"
MAX_FILE_SIZE_MB = 50

# In-memory job store. Fine for a project/demo; swap for Redis if you
# need this to survive a server restart or run across multiple workers.
jobs: dict[str, dict] = {}

# Maps file hash -> job_id, so re-uploading the same PDF returns the
# already-computed result instantly instead of re-running the VLM on
# every page again.
file_hash_cache: dict[str, str] = {}


def hash_file(path: str) -> str:
    """Content hash, not filename — so the same PDF uploaded under a
    different name still hits the cache."""
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


async def process_job(job_id: str, pdf_path: str, work_dir: str):
    """Runs in the background after the upload response has already
    been sent back to the user."""
    def on_progress(completed: int, total: int):
        jobs[job_id]["completed_pages"] = completed
        jobs[job_id]["total_pages"] = total

    try:
        jobs[job_id]["status"] = "processing"
        results = await run_extraction(pdf_path, work_dir, progress_callback=on_progress)
        jobs[job_id]["status"] = "done"
        jobs[job_id]["results"] = results
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
    finally:
        # Don't keep the raw uploaded PDF around after we're done with it.
        shutil.rmtree(work_dir, ignore_errors=True)


@app.post("/upload")
async def upload_pdf(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    job_id = str(uuid.uuid4())
    work_dir = os.path.join(UPLOAD_DIR, job_id)
    os.makedirs(work_dir, exist_ok=True)
    pdf_path = os.path.join(work_dir, "input.pdf")

    # Stream to disk in chunks rather than reading the whole upload
    # into memory at once — matters once files get large.
    size = 0
    with open(pdf_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_FILE_SIZE_MB * 1024 * 1024:
                f.close()
                shutil.rmtree(work_dir, ignore_errors=True)
                raise HTTPException(status_code=400, detail=f"File exceeds {MAX_FILE_SIZE_MB}MB limit.")
            f.write(chunk)

    # Cache check: same content already processed before?
    content_hash = hash_file(pdf_path)
    if content_hash in file_hash_cache:
        cached_job_id = file_hash_cache[content_hash]
        if jobs.get(cached_job_id, {}).get("status") == "done":
            shutil.rmtree(work_dir, ignore_errors=True)
            return {"job_id": cached_job_id, "cached": True}

    jobs[job_id] = {"status": "queued", "completed_pages": 0, "total_pages": None, "results": None}
    file_hash_cache[content_hash] = job_id

    background_tasks.add_task(process_job, job_id, pdf_path, work_dir)
    return {"job_id": job_id, "cached": False}


@app.get("/status/{job_id}")
async def get_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found.")
    job = jobs[job_id]
    return {
        "status": job["status"],
        "completed_pages": job["completed_pages"],
        "total_pages": job["total_pages"],
    }


@app.get("/result/{job_id}")
async def get_result(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found.")
    job = jobs[job_id]
    if job["status"] != "done":
        raise HTTPException(status_code=409, detail=f"Job is not finished (status: {job['status']}).")
    return {"results": job["results"]}
