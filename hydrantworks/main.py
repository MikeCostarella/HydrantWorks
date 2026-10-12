"""FastAPI application.

    uvicorn hydrantworks.main:app --reload

On first start the database is built from data/hydrants.csv (see seed.py).
Interactive API docs: http://127.0.0.1:8000/docs
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import __version__
from .chaos import ChaosMiddleware
from .config import Settings, load_settings
from .db import connect
from .routers import audit, hydrants, inspections, work_orders
from .seed import build_database
from .tracing import TracingMiddleware


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if not settings.db_path.exists():
            counts = build_database(settings.db_path, settings.hydrants_csv, settings.seed_work_data)
            logging.getLogger("hydrantworks").info("Built %s: %s", settings.db_path, counts)
        app.state.conn = connect(settings.db_path)
        try:
            yield
        finally:
            app.state.conn.close()

    app = FastAPI(
        title="HydrantWorks",
        version=__version__,
        description=(
            "Hydrant maintenance service for Trumbull County, Ohio. The hydrant inventory is the "
            "county's real export; inspections, work orders, and status notices are synthetic sample data."
        ),
        lifespan=lifespan,
    )
    app.state.settings = settings

    if settings.chaos:
        app.add_middleware(ChaosMiddleware, spec=settings.chaos, seed=settings.chaos_seed)
    app.add_middleware(TracingMiddleware, log_path=settings.request_log)  # outermost: wraps chaos too

    @app.get("/health", tags=["health"])
    def health():
        return {"status": "ok", "version": __version__, "chaos": settings.chaos or None}

    app.include_router(hydrants.router)
    app.include_router(inspections.router)
    app.include_router(work_orders.router)
    app.include_router(audit.router)
    return app


logging.basicConfig(level=logging.INFO, format="%(message)s")
app = create_app()
