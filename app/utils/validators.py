"""Upload validation — checks file presence, extension, and size."""

from pathlib import Path
from fastapi import UploadFile, HTTPException, status
from app.config import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_BYTES


async def validate_upload(file: UploadFile) -> bytes:
    """Validate the uploaded file and return its raw bytes."""

    if file is None or file.filename is None or file.filename.strip() == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file uploaded or filename is empty.",
        )

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{ext}'. Accepted: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    contents = await file.read()

    if len(contents) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    if len(contents) > MAX_FILE_SIZE_BYTES:
        size_mb = len(contents) / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size ({size_mb:.1f} MB) exceeds the {MAX_FILE_SIZE_BYTES / (1024 * 1024):.0f} MB limit.",
        )

    return contents
