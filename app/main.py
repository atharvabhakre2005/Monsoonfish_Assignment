"""
FastAPI application entry point.

Run with:
    uvicorn app.main:app --reload
"""

import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import OUTPUT_DIR

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
    datefmt="%H:%M:%S",
)

# App instance
app = FastAPI(
    title="Logo Processing & Email Delivery Service",
    description=(
        "Upload a logo image, receive 3 CV-processed outputs "
        "(silhouette, border, grayscale), and get them emailed automatically."
    ),
    version="1.0.0",
)

# Mount static files for output downloads
app.mount("/static-outputs", StaticFiles(directory=str(OUTPUT_DIR)), name="outputs")

# Register routes
app.include_router(router)
