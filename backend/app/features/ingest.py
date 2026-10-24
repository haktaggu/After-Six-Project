# - SQL uses parameters. Refresh jobs own import transactions; these helpers never commit.
from __future__ import annotations

from app.errors import ApiProblem
from app.schemas import (
    Course,
    Database,
    ImportedCourse,
    IngestionDocument,
    RefreshResult,
    SeatOpeningEvent,
    Section,
)
from app.features.prerequisites import parse_requirement_rule

# - Allow only configured official source hosts; use timeout 10s and response cap 5MiB.
# - Fetch outside DB transactions; reject non-success/invalid encoding and preserve last good data
#   on failure.
# - CATALOG_SOURCE_URL defaults https://catalog.sjsu.edu/; SCHEDULE_SOURCE_URL defaults
#   https://www.sjsu.edu/classes/schedules/fall-2026.php. Landing pages may link to the actual
#   data. Verify source fixtures before writing selectors; timeout 10s, cap 5MiB.
def fetch_source(url: str) -> str:
    raise NotImplementedError


# - Use verified catalog fixture structure, not guessed selectors. Extract courses and raw
#   requirement text.
# - Normalize each course and parse requirements conservatively, including grade/GPA/earned-unit/
#   standing/major clauses and their operators. Keep prerequisite/corequisite/restriction text;
#   only unrecognized or ambiguous clauses become unknown, not whole categories of restrictions.
# - Return validated document; parse failure raises rather than returning an empty successful
#   import.
# - Use good/broken samples in demo/sources/catalog/. ImportedCourse contains course:Course and
#   prerequisite_rule:RequirementRule; IngestionDocument has terms[],courses[],sections[]. Catalog
#   parsing normally leaves sections=[].
def parse_catalog(html: str, source_url: str) -> IngestionDocument:
    raise NotImplementedError


# - Use verified schedule samples; extract class numbers as strings, meetings, instructors and
#   known seats.
# - Normalize sections and term; preserve null seats/TBA times. Validate required fields before
#   database writes.
# - Use verified samples in demo/sources/schedules/. Normalize course IDs as
#   SUBJECT-catalog_number and section IDs as term:class_number. Preserve unknown seats/TBA. Never
#   invent a catalog course to satisfy a section foreign key.
def parse_schedule(html: str, term: str, source_url: str) -> IngestionDocument:
    raise NotImplementedError


# - Validate subject/catalog_number/title, create SUBJECT-catalog_number ID.
# - Normalize nullable units/descriptions/source fields and conservative prerequisite rule; return
#   typed value.
def normalize_course(raw: dict[str, object]) -> ImportedCourse:
    raise NotImplementedError


# - Validate class number/term; form term:class_number ID. Decode weekdays to mon..sun and local
#   HH:MM.
# - Preserve unknown seats; derive availability, attach source URL and successful observation
#   timestamp.
# - Course: {id: string, subject: string, catalog_number: string, title: string, description:
#   string | null, units_min: number | null, units_max: number | null, prerequisite_text: string |
#   null, corequisite_text: string | null, restrictions_text: string | null, catalog_url: string |
#   null}.
# - Section: {id: string, term: string, class_number: string, section_number: string, course:
#   Course, title: string, mode: string, units: number | null, open_seats: number | null,
#   availability: Availability, meetings: Meeting[], instructors: Instructor[], notes: string |
#   null, source_url: string, last_checked_at: string | null, is_stale: boolean}.
def normalize_section(raw: dict[str, object], course: Course, term: str, source_url: str, checked_at: str) -> Section:
    raise NotImplementedError


# - Inside caller transaction, upsert term/course rows and serialized requirement trees without
#   changing stable IDs.
# - Preserve meaningful cached fields when an unverified/missing source field would overwrite them;
#   return updated row count.
# - Storage: courses(id TEXT PK, subject TEXT, catalog_number TEXT, title TEXT, description TEXT
#   nullable, units_min/max REAL nullable, prerequisite_text/corequisite_text/restrictions_text
#   TEXT nullable, prerequisite_rule_json TEXT nullable, catalog_url TEXT nullable).
# - Storage: terms(id TEXT PK, name TEXT).
def upsert_catalog(db: Database, document: IngestionDocument) -> int:
    raise NotImplementedError


# - Inside caller transaction, ensure foreign-key courses/terms exist and validate entire batch.
# - For each section read old seats, update section/meetings/instructors atomically, and call
#   record_opening_event.
# - Return updated count/new event IDs; no notifications or commit inside this helper.
# - RefreshResult: updated_records:int,event_ids:list[str],checked_at:UTC ISO 8601. The caller owns
#   BEGIN IMMEDIATE and commit/rollback. Preserve cached rows/freshness if fetching/parsing fails;
#   no automatic deletion of missing sections.
# - Storage: sections(id TEXT PK, term TEXT FK terms, class_number TEXT, section_number TEXT,
#   course_id FK courses, title TEXT, mode TEXT, units REAL nullable, open_seats INTEGER
#   nullable>=0, notes TEXT nullable, source_url TEXT, last_checked_at TEXT nullable).
# - Storage: meetings(id INTEGER PK, section_id FK sections, days_json TEXT (mon..sun array),
#   start_time/end_time/location TEXT nullable, is_tba INTEGER 0/1).
# - Storage: instructors(id INTEGER PK, section_id FK sections, name TEXT).
def upsert_sections(db: Database, document: IngestionDocument, checked_at: str) -> RefreshResult:
    raise NotImplementedError


# - Inside the same serialized write transaction as section update, detect exactly previous==0 and
#   new>0.
# - If no transition return None. Otherwise insert UUID event and return it; repeated unchanged
#   refresh has no transition.
# - Storage: availability_events(id TEXT UUID PK, section_id FK sections, previous_seats INTEGER=0,
#   new_seats INTEGER>0, detected_at TEXT, processed_at TEXT nullable).
def record_opening_event(db: Database, section_id: str, previous_seats: int | None, new_seats: int | None, detected_at: str) -> SeatOpeningEvent | None:
    raise NotImplementedError
