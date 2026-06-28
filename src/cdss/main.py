"""FastAPI application entry point."""

from fastapi import FastAPI

from cdss.api.routes import health


def create_app() -> FastAPI:
    app = FastAPI(title="Hypertension CDSS", version="0.1.0")
    app.include_router(health.router)
    return app


app = create_app()
