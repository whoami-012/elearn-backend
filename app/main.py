"""
main.py — FastAPI application entry point for the e-learn backend.

Responsibilities:
- Creates and configures the FastAPI app instance
- Registers all API routers under /api/v1
- Wires up lifespan events (startup / shutdown)
- Configures CORS for frontend access
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.api import api_router
from app.api.v1.endpoints.auth import google_router
from app.db.init_db import init_db

# ALLOWED_ORIGINS: comma-separated list set via env var in production.
# Falls back to localhost origins for local development.
_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]


# ---------------------------------------------------------------------------
# Lifespan — startup & shutdown logic
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs once on startup (before the yield) and once on shutdown (after).

    Startup:
      - Calls init_db() in development to auto-create tables.
      - In production, this is skipped — use 'alembic upgrade head' instead.

    Shutdown:
      - Reserved for cleanup (e.g. closing connection pools, flushing caches).
    """
    # Startup
    env = os.getenv("APP_ENV", "development").lower()

    if env in {"development", "dev", "local"}:
      await init_db()
    # Ensure upload directories exist
    Path("static/thumbnails").mkdir(parents=True, exist_ok=True)
    yield
    # Shutdown (nothing to clean up yet)


# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------

app = FastAPI(
    title="E-Learn API",
    description="REST API for the e-learning platform — authentication, course management, enrollments, and more.",
    version="1.0.0",
    docs_url="/docs",       # Swagger UI
    redoc_url="/redoc",     # ReDoc UI
    lifespan=lifespan,
    redirect_slashes=False, # Prevent 307 redirects for POST without trailing slash
)


# ---------------------------------------------------------------------------
# CORS Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,         # Required for cookies / Auth headers
    allow_methods=["*"],            # Allow all HTTP methods
    allow_headers=["*"],            # Allow all headers including Authorization
)


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(api_router, prefix="/api/v1")
app.include_router(google_router, prefix="/api")

# Serve uploaded files (thumbnails, etc.) as static assets
# Access via: http://server/static/thumbnails/<filename>
app.mount("/static", StaticFiles(directory="static"), name="static")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Health"])
async def health_check():
    """
    Lightweight endpoint to verify the API is running.
    Used by load balancers, Docker HEALTHCHECK, and monitoring tools.
    """
    return {"status": "ok"}
