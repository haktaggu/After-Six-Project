from __future__ import annotations

from typing import Annotated
from fastapi import APIRouter, Depends, Query
from app.api.common import DatabaseDep, StudentDep, require_csrf
from app.schemas import (
    EligibilityRequest,
    EligibilityResponse,
    Major,
    MajorRoadmap,
    Page,
    PaginationQuery,
    StudentRoadmap,
)
from app.features import roadmap, prerequisites

router = APIRouter(prefix="/api")

@router.get("/majors", response_model=Page[Major], status_code=200)
def majors(db: DatabaseDep, student: StudentDep, query: Annotated[PaginationQuery, Query()]) -> Page[Major]:
    return roadmap.list_majors(db,query.limit,query.offset)

@router.get("/majors/{major_code}/roadmap", response_model=MajorRoadmap, status_code=200)
def major_roadmap(major_code: str, db: DatabaseDep, student: StudentDep) -> MajorRoadmap:
    return roadmap.get_major_roadmap(db,major_code)

@router.post("/me/eligibility", response_model=EligibilityResponse, status_code=200, dependencies=[Depends(require_csrf)])
def eligibility(body: EligibilityRequest, db: DatabaseDep, student: StudentDep) -> EligibilityResponse:
    return prerequisites.check_eligibility(db,student.student_id,body.course_ids)

@router.get("/me/roadmap", response_model=StudentRoadmap, status_code=200)
def student_roadmap(db: DatabaseDep, student: StudentDep) -> StudentRoadmap:
    return roadmap.get_student_roadmap(db,student)
