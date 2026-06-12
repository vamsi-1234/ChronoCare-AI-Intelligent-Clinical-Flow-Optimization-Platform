"""ChronoCare AI – FastAPI application entry point."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.api.appointments_routes import router as appointments_router
from app.db.database import init_db
from app.ml.models import load_models
from app.utils.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

# ── Lifespan (replaces deprecated on_event) ───────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup / shutdown logic."""
    logger.info("ChronoCare AI starting up …")
    # Initialise database tables
    try:
        init_db()
    except Exception as exc:  # noqa: BLE001
        logger.error("DB init failed (non-fatal): %s", exc)

    # Load ML models
    load_models()
    logger.info("Startup complete.")
    yield
    logger.info("ChronoCare AI shutting down.")


# ── App factory ────────────────────────────────────────────────────────────

app = FastAPI(
    title="ChronoCare AI",
    description=(
        "Intelligent Clinical Flow Optimization Platform – "
        "ML-powered appointment duration prediction, no-show risk assessment, "
        "dynamic schedule optimisation, and daily appointment management."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "System", "description": "Health and status"},
        {"name": "Predictions", "description": "Duration and no-show ML predictions"},
        {"name": "Scheduling", "description": "Simulation, optimisation, waiting time"},
        {"name": "Appointments", "description": "Daily appointment management and assessment"},
    ],
)

# ── CORS ───────────────────────────────────────────────────────────────────

_cors_origins_raw = os.getenv(
    "CORS_ORIGINS", "http://localhost:3000,http://localhost:8080"
)
_cors_origins = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global exception handler ───────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception for %s %s", request.method, request.url)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred.",
                "detail": str(exc),
            }
        },
    )


# ── Routes ─────────────────────────────────────────────────────────────────

app.include_router(router)
app.include_router(appointments_router)


# ── Root redirect to docs ──────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def root() -> JSONResponse:
    return JSONResponse(
        {"message": "ChronoCare AI API – visit /docs for interactive documentation."}
    )

