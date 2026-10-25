from __future__ import annotations

from contextlib import closing
import sqlite3
from typing import Annotated, Iterator
from fastapi import Depends, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.db.connection import connect
from app.errors import ApiProblem
from app.features.auth import get_session, validate_csrf_token
from app.schemas import AuthenticatedStudent, Database, ErrorResponse, ApiError, FieldError

SESSION_COOKIE = "oursjsu_session"
CSRF_COOKIE = "oursjsu_csrf"

def get_db(request: Request) -> Iterator[Database]:
    try:
        connection = connect(request.app.state.database_path)
    except (OSError, sqlite3.Error) as exc:
        raise ApiProblem(503, "DATABASE_UNAVAILABLE", "Database unavailable") from exc
    with closing(connection):
        yield connection

DatabaseDep = Annotated[Database, Depends(get_db)]

def require_student(request: Request, db: DatabaseDep) -> AuthenticatedStudent:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise ApiProblem(401, "AUTH_REQUIRED", "Log in to continue")
    return get_session(db, token).student

StudentDep = Annotated[AuthenticatedStudent, Depends(require_student)]

def require_csrf(request: Request, db: DatabaseDep) -> None:
    submitted = request.headers.get("X-CSRF-Token")
    if not submitted:
        raise ApiProblem(403, "CSRF_FAILED", "CSRF token required")
    session_cookie = request.cookies.get(SESSION_COOKIE)
    expected = (get_session(db, session_cookie).response.csrf_token
                if session_cookie else request.cookies.get(CSRF_COOKIE))
    if not expected:
        raise ApiProblem(403, "CSRF_FAILED", "CSRF token required")
    validate_csrf_token(submitted, expected)

def problem_response(problem: ApiProblem) -> JSONResponse:
    body = ErrorResponse(error=ApiError(code=problem.code,message=problem.message,fields=problem.fields))
    return JSONResponse(status_code=problem.status,content=body.model_dump())

async def handle_problem(_request: Request, exc: ApiProblem) -> JSONResponse:
    return problem_response(exc)

async def handle_validation(_request: Request, exc: RequestValidationError) -> JSONResponse:
    fields = [FieldError(path=".".join(str(x) for x in error["loc"] if x not in {"body","query","path"}),
                         message="Invalid value") for error in exc.errors()]
    return problem_response(ApiProblem(422,"VALIDATION_ERROR","Check the request fields",fields))


async def handle_database(_request: Request, _exc: sqlite3.Error) -> JSONResponse:
    return problem_response(ApiProblem(503, "DATABASE_UNAVAILABLE", "Database unavailable"))
