"""FastAPI application entry point."""

from fastapi import FastAPI
from scalar_fastapi import get_scalar_api_reference
from starlette.middleware.cors import CORSMiddleware

from cdss.api.errors import register_error_handlers
from cdss.api.routes import dashboard, evaluation, fhir, health, tree_graph, tree_layout


def create_app() -> FastAPI:
    app = FastAPI(title="Hypertension CDSS", version="0.1.0", docs_url=None, redoc_url=None)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(evaluation.router)
    app.include_router(tree_graph.router)
    app.include_router(tree_layout.router)
    app.include_router(fhir.router)
    app.include_router(dashboard.router)

    @app.get("/docs", include_in_schema=False)
    def scalar_docs():
        return get_scalar_api_reference(openapi_url=app.openapi_url, title=app.title)

    return app


app = create_app()
