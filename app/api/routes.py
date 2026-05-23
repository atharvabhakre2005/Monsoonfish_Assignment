"""
API routes for the logo processing service.

Endpoints
---------
POST /process   – Upload an image, run CV transformations, email results.
GET  /outputs/{filename} – Download a generated output file.
GET  /           – Serve the frontend HTML page.
"""

import uuid
import logging
from pathlib import Path

from fastapi import APIRouter, File, UploadFile, HTTPException, status
from fastapi.responses import FileResponse, HTMLResponse

from app.config import OUTPUT_DIR, BASE_DIR
from app.utils.validators import validate_upload
from app.services.image_processor import process_image
from app.services.email_service import send_results_email

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/process")
async def process_logo(file: UploadFile = File(...)):
    """
    Accept an image upload, run all 3 CV transformations,
    send the results via email, and return a JSON confirmation.
    """
    # ── 1. Validate the upload ───────────────────────────────────────────
    raw_bytes = await validate_upload(file)

    # ── 2. Create a unique output directory for this request ─────────────
    request_id = uuid.uuid4().hex[:12]
    output_dir = OUTPUT_DIR / request_id
    logger.info("Processing request %s — file: %s", request_id, file.filename)

    # ── 3. Run image processing pipeline ─────────────────────────────────
    try:
        output_paths = process_image(raw_bytes, output_dir)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Image processing failed: {exc}",
        )
    except Exception as exc:
        logger.exception("Unexpected processing error for request %s", request_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Processing failed unexpectedly: {exc}",
        )

    # ── 4. Send email with attachments ───────────────────────────────────
    try:
        email_status = send_results_email(output_paths)
    except RuntimeError as exc:
        # Missing email configuration — processing succeeded, email did not
        email_status = f"failed: {exc}"
        logger.warning("Email skipped: %s", exc)
    except Exception as exc:
        email_status = f"failed: {exc}"
        logger.exception("Email delivery error for request %s", request_id)

    # ── 5. Build response ────────────────────────────────────────────────
    return {
        "request_id": request_id,
        "silhouette": "generated",
        "border": "generated",
        "grayscale": "generated",
        "email_status": email_status,
        "downloads": {
            name: f"/outputs/{request_id}/{path.name}"
            for name, path in output_paths.items()
        },
    }


@router.get("/outputs/{request_id}/{filename}")
async def download_output(request_id: str, filename: str):
    """Serve a generated output file for download / preview."""
    filepath = OUTPUT_DIR / request_id / filename

    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Output file '{filename}' not found for request '{request_id}'.",
        )

    return FileResponse(
        path=str(filepath),
        media_type="image/png",
        filename=filename,
    )


@router.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the minimal frontend HTML page."""
    html_path = BASE_DIR / "static" / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
