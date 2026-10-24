from contextlib import asynccontextmanager
from pathlib import Path
import sqlite3

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.api import accounts, courses, notifications, planning, watchlist
from app.api.health import router as health_router
from app.api.common import handle_problem, handle_scaffold, handle_validation, handle_database
from app.db.connection import database_path, init_db
from app.errors import ApiProblem
from scripts.seed import seed_demo_account


def create_app(db_path: Path | None = None) -> FastAPI:
    path = db_path if db_path is not None else database_path()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_db(path)
        seed_demo_account(path)
        yield

    app = FastAPI(title="OurSJSU API", lifespan=lifespan)
    app.state.database_path = path
    app.add_exception_handler(ApiProblem, handle_problem)
    app.add_exception_handler(NotImplementedError, handle_scaffold)
    app.add_exception_handler(RequestValidationError, handle_validation)
    app.add_exception_handler(sqlite3.Error, handle_database)
    app.include_router(health_router)
    for router in (accounts.router, courses.router, planning.router, watchlist.router, notifications.router):
        app.include_router(router)
    return app


app = create_app()
