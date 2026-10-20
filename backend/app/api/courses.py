from __future__ import annotations

from typing import Annotated
from fastapi import APIRouter, Depends, Query
from app.api.common import DatabaseDep, StudentDep, require_csrf
from app.schemas import CompareRequest, ComparisonResponse, Course, CourseQuery, Page, PaginationQuery, Section, SectionQuery, Term
from app.features import courses

router = APIRouter(prefix="/api")

@router.get("/terms", response_model=Page[Term])
def terms(db: DatabaseDep, student: StudentDep, query: Annotated[PaginationQuery, Query()]) -> Page[Term]:
    return courses.list_terms(db, query.limit, query.offset)

# - q searches code/title; page fields are items, total, limit and offset.
@router.get("/courses", response_model=Page[Course])
def search_courses(db: DatabaseDep, student: StudentDep, query: Annotated[CourseQuery, Query()]) -> Page[Course]:
    return courses.search_courses(db, **query.model_dump())

@router.get("/courses/{course_id}", response_model=Course)
def course(course_id: str, db: DatabaseDep, student: StudentDep) -> Course:
    return courses.get_course(db, course_id)

# - term is required; q and exact course_id are optional. All supplied filters must match.
@router.get("/sections", response_model=Page[Section])
def sections(db: DatabaseDep, student: StudentDep, query: Annotated[SectionQuery, Query()]) -> Page[Section]:
    return courses.search_sections(db, **query.model_dump())

# - Compare exactly two unique sections in one term, preserving selection order.
@router.post("/sections/compare", response_model=ComparisonResponse, dependencies=[Depends(require_csrf)])
def compare(body: CompareRequest, db: DatabaseDep, student: StudentDep) -> ComparisonResponse:
    return courses.compare_sections(db, body)

@router.get("/sections/{section_id}", response_model=Section)
def section(section_id: str, db: DatabaseDep, student: StudentDep) -> Section:
    return courses.get_section(db, section_id)
