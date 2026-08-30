from fastapi import FastAPI

from argusfinance.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()
    app = FastAPI(title="ArgusFinance", version="0.1.0")
    app.state.settings = resolved

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"service": "argusfinance", "status": "ok", "mode": "local"}

    return app


app = create_app()
