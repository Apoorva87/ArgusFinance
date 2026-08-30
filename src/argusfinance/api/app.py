from fastapi import FastAPI

from argusfinance.api.routes.market import router as market_router
from argusfinance.bootstrap import Container, build_container
from argusfinance.config import Settings, get_settings


def create_app(settings: Settings | None = None, container: Container | None = None) -> FastAPI:
    resolved = settings or get_settings()
    app = FastAPI(title="ArgusFinance", version="0.1.0")
    app.state.settings = resolved
    app.state.container = container or build_container(resolved)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"service": "argusfinance", "status": "ok", "mode": "local"}

    app.include_router(market_router)
    return app


app = create_app()
