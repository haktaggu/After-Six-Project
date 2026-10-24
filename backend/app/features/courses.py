# - Read saved SQLite data here. These functions don't scrape or commit changes.

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.schemas import (
        CompareRequest,
        ComparisonResponse,
        Course,
        Page,
        Section,
        Term,
    )


# - Used by GET /api/terms. Read terms(id TEXT, name TEXT).
# - Check limit is 1–100 and offset is at least 0. Defaults are 25 and 0.
# - Count all terms, then fetch the page ordered by id ascending.
# - Return Page[Term]: {items: [{id: str, name: str}], total: int,
#   limit: int, offset: int}. All IDs stay strings.
# - An empty database returns {items: [], total: 0, limit: 25, offset: 0}.
# - Check that moving between pages doesn't change total or repeat terms.
def list_terms(
    db: sqlite3.Connection,
    limit: int = 25,
    offset: int = 0,
) -> Page[Term]:
    raise NotImplementedError


# - Used by GET /api/courses. Read the courses table.
# - q searches the course code and title, ignoring capitalization.
#   Example: q="cmpe 130" should match the code "CMPE-130".
# - None skips the keyword filter; match spaces/hyphens consistently in course codes.
# - Use SQL parameters for every supplied value; don't build SQL from user text.
#   Escape %, _ and the escape character if using LIKE for a literal text search.
# - Count matching courses before LIMIT/OFFSET. Sort by id ascending.
# - Return Page[Course]: {items: Course[], total: int, limit: int, offset: int}.
#   Course fields are listed above get_course below; include them all.
# - Empty results return items=[] and total=0. Pagination rules match list_terms.
# - Check a keyword, no matches, and a second page.
def search_courses(
    db: sqlite3.Connection,
    q: str | None = None,
    limit: int = 25,
    offset: int = 0,
) -> Page[Course]:
    raise NotImplementedError


# - Used by GET /api/courses/{course_id}. Find the exact courses.id.
# - Example ID: "CMPE-130". Don't convert the catalog number to an integer.
# - Return Course with these fields from the row:
#   id, subject, catalog_number, title: str;
#   description, prerequisite_text, corequisite_text, restrictions_text,
#   catalog_url: str | None; units_min, units_max: float | None.
# - Keep missing optional values as None, which becomes JSON null.
#   Don't drop fields or replace unknown units with zero.
# - If the ID doesn't exist, raise the shared ApiProblem with
#   status=404, code="NOT_FOUND", message="Course not found", fields=[].
#   Use ApiProblem(status, code, message, fields=None).
# - Check an existing course, missing course, and course with null optional fields.
def get_course(db: sqlite3.Connection, course_id: str) -> Course:
    raise NotImplementedError


# - Used by GET /api/sections. term is required, e.g. "fall-2026".
# - Read sections joined to courses. q searches course code/title, ignoring capitalization.
# - course_id and term match exact IDs; None skips an optional filter. All supplied filters
#   must match. Keep one result per section and parameterize all input values.
# - Count matching sections before pagination, then sort by section id ascending.
# - Build each result with serialize_section(db, row). Its input fields and full
#   Section response are listed above that function below.
# - Return Page[Section]: {items: Section[], total: int, limit: int, offset: int}.
#   Use the same pagination bounds/defaults as list_terms. No matches means [].
# - Check q plus course_id, no matches, unknown seats and totals across pages.
def search_sections(
    db: sqlite3.Connection,
    term: str,
    q: str | None = None,
    course_id: str | None = None,
    limit: int = 25,
    offset: int = 0,
) -> Page[Section]:
    raise NotImplementedError


# - Used by GET /api/sections/{section_id}. Find the exact sections.id.
# - Example ID: "fall-2026:45123". Keep class numbers and IDs as strings.
# - Pass the row to serialize_section(db, row) and return its Section result.
# - Missing ID raises ApiProblem(404, "NOT_FOUND", "Section not found").
# - Check an existing section, a missing section, and a section with TBA meetings.
def get_section(db: sqlite3.Connection, section_id: str) -> Section:
    raise NotImplementedError


# - Used by POST /api/sections/compare.
# - CompareRequest contains section_ids: list[str], with exactly two different IDs.
#   Example: {"section_ids": ["fall-2026:45123", "fall-2026:45124"]}.
# - Reject a wrong count or duplicate IDs with ApiProblem(422,
#   "VALIDATION_ERROR", a readable message). The request model checks these too.
# - Call get_section(db, section_id) for each requested ID; propagate its 404
#   if any section is missing. Then reject mixed terms with the same 422 format.
# - Return ComparisonResponse: {sections: Section[]} in the requested order,
#   even if that order differs from the normal search sort order.
# - Check two valid sections, reversed order, duplicates, mixed terms,
#   and a missing section. This function doesn't calculate eligibility.
def compare_sections(
    db: sqlite3.Connection,
    body: CompareRequest,
) -> ComparisonResponse:
    raise NotImplementedError


# - Used by search_sections, get_section, and comparison through get_section.
# - row is a dict from a sections row with id, term, class_number, section_number,
#   course_id, title, mode, units, open_seats, notes, source_url, last_checked_at.
#   Leave freshness unknown if last_checked_at is unavailable; don't use a different timestamp.
# - The current connection returns tuples. Build a dict from cursor.description
#   and the row values, or use a cursor with sqlite3.Row; don't change a shared
#   connection's row format halfway through a request.
# - Call get_course(db, row["course_id"]) for the nested course object.
# - Read meetings and instructors by section_id using parameterized queries.
#   Order each by its id so the response stays consistent.
# - Meeting: {days: list[str], start_time: str | None, end_time: str | None,
#   location: str | None, is_tba: bool}. Decode days_json into mon/tue/wed/thu/
#   fri/sat/sun.
#   Times are HH:MM in America/Los_Angeles; leave missing/TBA times as None.
# - Instructor: {name: str}. No meetings or instructors returns an empty list.
# - Derive availability: None seats -> "unknown", 0 -> "closed", >0 -> "open".
#   Reject invalid negative seats during import; don't turn them into open seats.
# - last_checked_at is a UTC ISO 8601 string, e.g. "2026-10-23T18:00:00Z".
#   Compare it with timezone-aware UTC now. is_stale is True when the timestamp
#   is None or older than five minutes. Preserve the stored timestamp in output.
# - Return Section with every field:
#   id, term, class_number, section_number, title, mode, source_url: str;
#   course: Course; units: float | None; open_seats: int | None;
#   availability: "open" | "closed" | "unknown";
#   meetings: list[Meeting]; instructors: list[Instructor];
#   notes, last_checked_at: str | None; is_stale: bool.
# - Don't flatten course into extra fields like course_title, and don't expose
#   internal database IDs beyond the fields in the response above.
# - Check null/zero/positive seats, no meetings, multiple instructors, and both
#   a fresh timestamp and one older than five minutes. Null timestamp is stale.
def serialize_section(db: sqlite3.Connection, row: dict[str, object]) -> Section:
    raise NotImplementedError
