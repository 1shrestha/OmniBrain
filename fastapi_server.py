"""
app.py

Real-time entry point for the OmniBrain Vision Extraction Service.

Flow:
1. User uploads a PDF -> immediately receives a job_id.
2. PDF extraction runs in the background.
3. Frontend polls GET /status/{job_id}.
4. Once complete, GET /result/{job_id} returns the extracted data.

Run with:
    uvicorn app:app --reload
"""

import os
import uuid
import hashlib
import shutil

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks

from extractor import run_extraction


# ===========================================================
# FASTAPI APP
# ===========================================================

app = FastAPI(
    title="OmniBrain Vision Extraction Service"
)


# ============================================================
# CONFIGURATION
# ============================================================

UPLOAD_DIR = "uploads"

# Maximum PDF size: 200 MB
MAX_FILE_SIZE_MB = 200

# Convert MB to bytes
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


# ============================================================
# IN-MEMORY JOB STORE
# ============================================================

# Fine for a project/demo.
# For production, replace this with Redis or a database.

jobs: dict[str, dict] = {}


# ============================================================
# FILE HASH CACHE
# ============================================================

# Maps:
# file hash -> job_id
#
# If the same PDF is uploaded again, the previous result
# can be returned instead of processing the PDF again.

file_hash_cache: dict[str, str] = {}


# ============================================================
# HASH FILE
# ============================================================

def hash_file(path: str) -> str:
    """
    Generate SHA-256 hash of the PDF contents.

    This checks file CONTENT rather than filename, so the same
    PDF uploaded with a different filename still gets cached.
    """

    sha256 = hashlib.sha256()

    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


# ============================================================
# BACKGROUND PROCESSING
# ============================================================

async def process_job(
    job_id: str,
    pdf_path: str,
    work_dir: str
):
    """
    Process the PDF in the background after the upload response
    has already been sent to the user.
    """

    def on_progress(completed: int, total: int):
        """
        Update extraction progress.
        """

        if job_id in jobs:
            jobs[job_id]["completed_pages"] = completed
            jobs[job_id]["total_pages"] = total

    try:

        # Update job status
        jobs[job_id]["status"] = "processing"

        # Run extraction
        results = await run_extraction(
            pdf_path,
            work_dir,
            progress_callback=on_progress
        )

        # Store successful result
        jobs[job_id]["status"] = "done"
        jobs[job_id]["results"] = results

    except Exception as e:

        # Store error
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)

    finally:

        # Delete uploaded PDF and temporary files
        shutil.rmtree(
            work_dir,
            ignore_errors=True
        )


# ============================================================
# UPLOAD PDF
# ============================================================

@app.post("/upload")
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):

    # --------------------------------------------------------
    # Validate filename
    # --------------------------------------------------------

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No filename provided."
        )

    # Accept PDF based on extension.
    # This avoids problems where the browser sends an unexpected
    # MIME type such as application/octet-stream.

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted."
        )

    # --------------------------------------------------------
    # Create job
    # --------------------------------------------------------

    job_id = str(uuid.uuid4())

    work_dir = os.path.join(
        UPLOAD_DIR,
        job_id
    )

    os.makedirs(
        work_dir,
        exist_ok=True
    )

    pdf_path = os.path.join(
        work_dir,
        "input.pdf"
    )

    # --------------------------------------------------------
    # Save uploaded PDF in chunks
    # --------------------------------------------------------

    size = 0

    try:

        with open(pdf_path, "wb") as f:

            while True:

                # Read 1 MB at a time
                chunk = await file.read(1024 * 1024)

                # End of file
                if not chunk:
                    break

                size += len(chunk)

                # Check file size
                if size > MAX_FILE_SIZE_BYTES:

                    shutil.rmtree(
                        work_dir,
                        ignore_errors=True
                    )

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"File exceeds "
                            f"{MAX_FILE_SIZE_MB}MB limit."
                        )
                    )

                f.write(chunk)

    except HTTPException:
        raise

    except Exception as e:

        shutil.rmtree(
            work_dir,
            ignore_errors=True
        )

        raise HTTPException(
            status_code=500,
            detail=f"Failed to save uploaded file: {str(e)}"
        )

    finally:

        await file.close()

    # --------------------------------------------------------
    # Validate that something was uploaded
    # --------------------------------------------------------

    if size == 0:

        shutil.rmtree(
            work_dir,
            ignore_errors=True
        )

        raise HTTPException(
            status_code=400,
            detail="Uploaded PDF is empty."
        )

    # --------------------------------------------------------
    # Generate content hash
    # --------------------------------------------------------

    content_hash = hash_file(pdf_path)

    # --------------------------------------------------------
    # Check cache
    # --------------------------------------------------------

    if content_hash in file_hash_cache:

        cached_job_id = file_hash_cache[content_hash]

        cached_job = jobs.get(cached_job_id)

        if cached_job and cached_job.get("status") == "done":

            # Remove newly uploaded duplicate
            shutil.rmtree(
                work_dir,
                ignore_errors=True
            )

            return {
                "job_id": cached_job_id,
                "cached": True
            }

    # --------------------------------------------------------
    # Create job record
    # --------------------------------------------------------

    jobs[job_id] = {
        "status": "queued",
        "completed_pages": 0,
        "total_pages": None,
        "results": None,
        "error": None,
        "file_size_bytes": size
    }

    # Store hash -> job ID
    file_hash_cache[content_hash] = job_id

    # --------------------------------------------------------
    # Start background extraction
    # --------------------------------------------------------

    background_tasks.add_task(
        process_job,
        job_id,
        pdf_path,
        work_dir
    )

    # --------------------------------------------------------
    # Return immediately
    # --------------------------------------------------------

    return {
        "job_id": job_id,
        "cached": False,
        "file_size_mb": round(
            size / (1024 * 1024),
            2
        ),
        "max_file_size_mb": MAX_FILE_SIZE_MB
    }


# ============================================================
# GET JOB STATUS
# ============================================================

@app.get("/status/{job_id}")
async def get_status(job_id: str):

    if job_id not in jobs:

        raise HTTPException(
            status_code=404,
            detail="Job not found."
        )

    job = jobs[job_id]

    return {
        "status": job["status"],
        "completed_pages": job["completed_pages"],
        "total_pages": job["total_pages"]
    }


# ============================================================
# GET RESULT
# ============================================================

@app.get("/result/{job_id}")
async def get_result(job_id: str):

    if job_id not in jobs:

        raise HTTPException(
            status_code=404,
            detail="Job not found."
        )

    job = jobs[job_id]

    # Failed job
    if job["status"] == "failed":

        raise HTTPException(
            status_code=500,
            detail=job["error"]
        )

    # Still processing
    if job["status"] != "done":

        raise HTTPException(
            status_code=409,
            detail=(
                f"Job is not finished "
                f"(status: {job['status']})."
            )
        )

    # Successful result
    return {
        "results": job["results"]
    }