"""
extractor.py

CHANGED FOR REAL-TIME USE:
- Pages are processed CONCURRENTLY (up to MAX_CONCURRENT_VLM_CALLS at
  once) instead of one-by-one. A 40-page PDF that took 40x the
  per-page latency before now takes roughly (40 / concurrency) x that
  latency.
- Takes a `progress_callback` so the caller (app.py) can update a job
  status object as each page finishes — this is what lets the
  frontend show "12 / 40 pages processed" instead of a blank spinner.
- No longer writes results straight to a fixed file; returns them so
  app.py decides where they go (per-job, not a single shared file).
"""

import os
import asyncio
import fitz  # PyMuPDF — pip install pymupdf
from vlm_client import extract_from_page

# Tune this based on your API tier's rate limit. 5 is a safe starting
# point — raise it if you're not hitting 429s, lower it if you are.
MAX_CONCURRENT_VLM_CALLS = 5


def render_pdf_to_images(pdf_path: str, output_dir: str) -> list[str]:
    """Convert every page of the PDF into a PNG image."""
    os.makedirs(output_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    image_paths = []

    for page_index in range(len(doc)):
        page = doc[page_index]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # zoom=2 keeps small text readable
        image_path = os.path.join(output_dir, f"page_{page_index + 1}.png")
        pix.save(image_path)
        image_paths.append(image_path)

    doc.close()
    return image_paths


async def run_extraction(pdf_path: str, work_dir: str, progress_callback=None) -> list[dict]:
    """
    Full pipeline: render -> extract concurrently -> collect.

    `progress_callback(completed, total)` is called after every page
    finishes, so the job status store always reflects real progress
    even mid-batch — not just "started" then "done".
    """
    image_dir = os.path.join(work_dir, "page_images")
    image_paths = render_pdf_to_images(pdf_path, image_dir)
    total_pages = len(image_paths)

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_VLM_CALLS)
    completed = 0
    lock = asyncio.Lock()

    async def process_one(image_path: str, page_number: int) -> dict:
        nonlocal completed
        result = await extract_from_page(image_path, page_number, semaphore)
        async with lock:
            completed += 1
            if progress_callback:
                progress_callback(completed, total_pages)
        return result

    tasks = [process_one(path, i + 1) for i, path in enumerate(image_paths)]
    all_results = await asyncio.gather(*tasks)

    # Clean up rendered page images once we're done with them — a
    # real-time app that keeps every uploaded PDF's pages on disk
    # forever will run out of space fast.
    for path in image_paths:
        try:
            os.remove(path)
        except OSError:
            pass

    # Only keep pages where something was actually found.
    return [r for r in all_results if r["type"] != "none"]
