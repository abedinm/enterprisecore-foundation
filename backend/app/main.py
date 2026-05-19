"""
FastAPI application factory + ASGI entrypoint.

Run with:  uvicorn app.main:app --reload --port 8000
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import init_db, SessionLocal
from app.api.routes import api_router
from app.api.routes.ws import router as ws_router
from app.services.bootstrap import seed
from app.core.ws_manager import manager as ws_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the DB, seed defaults, and capture the event loop for WS push."""
    init_db()
    with SessionLocal() as db:
        seed(db)
    # WebSocket fan-out needs the running event loop so sync handlers can dispatch.
    ws_manager.bind_loop(asyncio.get_running_loop())
    yield
    # No special shutdown work yet.


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="EnterpriseCore AI Suite — auth, RBAC, projects, tasks, notifications.",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # ── CORS ────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routes ──────────────────────────────────────────────────────────────
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    # WebSocket lives outside /api/v1 so paths stay short and headers minimal.
    app.include_router(ws_router, prefix="/ws", tags=["ws"])

    # ── Root + global error handler ─────────────────────────────────────────
    @app.get("/")
    def root():
        return {
            "name": settings.app_name,
            "status": "running",
            "docs": "/api/docs",
            "api": settings.api_v1_prefix,
        }

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        # Top-level guard so a crash never returns an HTML traceback to the client.
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "type": type(exc).__name__},
        )

    return app


app = create_app()
