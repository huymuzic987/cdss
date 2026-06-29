"""FastAPI application entry point."""

from fastapi import FastAPI

from cdss.api.errors import register_error_handlers
from cdss.api.routes import evaluation, health


def create_app() -> FastAPI:
    app = FastAPI(title="Hypertension CDSS", version="0.1.0")
    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(evaluation.router)
    return app


app = create_app()
