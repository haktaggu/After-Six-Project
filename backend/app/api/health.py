import sqlite3

from fastapi import APIRouter, HTTPException, Request

from app.db.connection import check_connection

router = APIRouter(prefix="/api")


@router.get("/health")
def health(request: Request) -> dict[str, str]:
    try:
        check_connection(request.app.state.database_path)
    except (sqlite3.Error, OSError) as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return {"status": "ok"}
