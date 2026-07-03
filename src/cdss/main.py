"""FastAPI application entry point."""

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from cdss.api.errors import register_error_handlers
from cdss.api.routes import evaluation, fhir, health, tree_graph

# The Vite dev server for the read-only tree-graph frontend. No patient data
# crosses this API, so a small static allow-list for GET is sufficient.
_FRONTEND_DEV_ORIGIN = "http://localhost:5173"


def create_app() -> FastAPI:
    app = FastAPI(title="Hypertension CDSS", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[_FRONTEND_DEV_ORIGIN],
        allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(evaluation.router)
    app.include_router(tree_graph.router)
    app.include_router(fhir.router)
    return app


app = create_app()
