"""
init_db.py — LOCAL DEVELOPMENT ONLY

In production, schema changes are handled exclusively by Alembic migrations.
Never call init_db() in production. Use: alembic upgrade head
"""
import os
import app.models  # noqa: F401 — ensures all models are registered with Base.metadata
from app.db.base import Base
from app.db.session import engine


async def init_db():
    """
    Drop and recreate all tables from scratch.
    FOR LOCAL DEV ONLY — do not call in production.
    Use Alembic for production schema management.
    """
    env = os.getenv("APP_ENV", "development")
    if env == "production":
        raise RuntimeError(
            "init_db() must not be called in production. Use 'alembic upgrade head' instead."
        )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
