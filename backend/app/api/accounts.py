from __future__ import annotations

import os
from typing import Annotated
from fastapi import APIRouter, Depends, Query, Request, Response
from app.api.common import DatabaseDep, StudentDep, require_csrf, SESSION_COOKIE, CSRF_COOKIE
from app.schemas import CourseRecord, CourseRecordInput, CsrfResponse, LoginRequest, Page, PaginationQuery, ProfileResponse, ProfileUpdate, SessionResponse
from app.features import auth, profiles

router = APIRouter(prefix="/api")

# - COOKIE_SECURE=true for HTTPS; false for local HTTP.
def cookie_secure() -> bool:
    return os.environ.get("COOKIE_SECURE", "false").lower() == "true"

# - Return {csrf_token: str}; set the same token in an HttpOnly cookie.
@router.get("/auth/csrf", response_model=CsrfResponse)
def csrf(response: Response) -> CsrfResponse:
    token = auth.issue_csrf_token()
    response.set_cookie(CSRF_COOKIE, token, httponly=True, secure=cookie_secure(), samesite="lax", max_age=28800, path="/")
    return CsrfResponse(csrf_token=token)

# - Authenticate the seeded student; return SessionResponse and an HttpOnly session cookie.
@router.post("/auth/login", response_model=SessionResponse, dependencies=[Depends(require_csrf)])
def login(body: LoginRequest, db: DatabaseDep, response: Response) -> SessionResponse:
    user = auth.authenticate_user(db, body)
    grant = auth.create_session(db, user.id)
    response.set_cookie(SESSION_COOKIE, grant.cookie_token, httponly=True, secure=cookie_secure(), samesite="lax", max_age=28800, path="/")
    return grant.identity.response

@router.get("/auth/session", response_model=SessionResponse)
def session(request: Request, db: DatabaseDep, student: StudentDep) -> SessionResponse:
    return auth.get_session(db, request.cookies[SESSION_COOKIE]).response

@router.post("/auth/logout", response_class=Response, status_code=204, dependencies=[Depends(require_csrf)])
def logout(request: Request, db: DatabaseDep, student: StudentDep) -> Response:
    auth.revoke_session(db, request.cookies[SESSION_COOKIE])
    response = Response(status_code=204)
    response.delete_cookie(SESSION_COOKIE, path="/", secure=cookie_secure(), httponly=True, samesite="lax")
    response.delete_cookie(CSRF_COOKIE, path="/", secure=cookie_secure(), httponly=True, samesite="lax")
    return response

# - ProfileResponse is {user: User, profile: {major_code,standing,gpa,earned_units}}.
@router.get("/me", response_model=ProfileResponse)
def profile(db: DatabaseDep, student: StudentDep) -> ProfileResponse:
    return profiles.get_profile(db, student)

# - Supply major_code,standing,gpa,earned_units together; nullable fields can be cleared.
# - A non-null major_code must name an existing major. Account name/email stay read-only.
@router.patch("/me", response_model=ProfileResponse, dependencies=[Depends(require_csrf)])
def patch_profile(body: ProfileUpdate, db: DatabaseDep, student: StudentDep) -> ProfileResponse:
    return profiles.update_profile(db, student, body)

# - Sort by course_id. Page contains items, total, limit and offset.
@router.get("/me/course-records", response_model=Page[CourseRecord])
def course_records(db: DatabaseDep, student: StudentDep, query: Annotated[PaginationQuery, Query()]) -> Page[CourseRecord]:
    return profiles.list_course_records(db, student, query.limit, query.offset)

# - Body is {status: completed/in_progress/planned, grade: Grade | None, term: str | None}.
# - Return 201 when created and 200 when updated.
@router.put("/me/course-records/{course_id}", response_model=CourseRecord, responses={201: {"description": "Created"}}, dependencies=[Depends(require_csrf)])
def put_record(course_id: str, body: CourseRecordInput, db: DatabaseDep, student: StudentDep, response: Response) -> CourseRecord:
    result = profiles.put_course_record(db, student, course_id, body)
    response.status_code = 201 if result.created else 200
    return result.record

@router.delete("/me/course-records/{course_id}", response_class=Response, status_code=204, dependencies=[Depends(require_csrf)])
def delete_record(course_id: str, db: DatabaseDep, student: StudentDep) -> Response:
    profiles.delete_course_record(db, student, course_id)
    return Response(status_code=204)
