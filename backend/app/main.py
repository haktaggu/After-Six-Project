"""FastAPI application factory, lifespan, and route registration."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app.api.health import router as health_router
from app.db.connection import database_path, init_db


def create_app(db_path: Path | None = None) -> FastAPI:
    path = db_path if db_path is not None else database_path()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_db(path)
        yield

    app = FastAPI(title="OurSJSU API", lifespan=lifespan)
    app.state.database_path = path
    app.include_router(health_router)
    return app


app = create_app()
