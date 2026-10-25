from __future__ import annotations

from typing import Annotated
from fastapi import APIRouter, Depends, Query, Response
from app.api.common import DatabaseDep, StudentDep, require_csrf
from app.schemas import Page, WatchlistEntry, WatchlistQuery
from app.features import watchlist

router = APIRouter(prefix="/api")

@router.get("/me/watchlist", response_model=Page[WatchlistEntry])
def watchlist_page(db: DatabaseDep, student: StudentDep, query: Annotated[WatchlistQuery, Query()]) -> Page[WatchlistEntry]:
    return watchlist.list_watchlist(db, student, **query.model_dump())

@router.put("/me/watchlist/{section_id}", response_model=WatchlistEntry, responses={201: {"description": "Created"}}, dependencies=[Depends(require_csrf)])
def put_watch(section_id: str, db: DatabaseDep, student: StudentDep, response: Response) -> WatchlistEntry:
    result = watchlist.add_watch(db, student, section_id)
    response.status_code = 201 if result.created else 200
    return result.entry

@router.delete("/me/watchlist/{section_id}", response_class=Response, status_code=204, dependencies=[Depends(require_csrf)])
def delete_watch(section_id: str, db: DatabaseDep, student: StudentDep) -> Response:
    watchlist.remove_watch(db, student, section_id)
    return Response(status_code=204)
