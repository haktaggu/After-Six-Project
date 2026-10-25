from __future__ import annotations

from dataclasses import dataclass
import sqlite3
from typing import Generic, Literal, TypeVar
from pydantic import BaseModel, ConfigDict, Field, model_validator

T = TypeVar("T")

class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class Page(ApiModel, Generic[T]):
    items: list[T]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)

class PaginationQuery(ApiModel):
    limit: int = Field(default=25, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

class CourseQuery(PaginationQuery):
    q: str | None = None

class SectionQuery(CourseQuery):
    term: str
    course_id: str | None = None

class WatchlistQuery(PaginationQuery):
    term: str | None = None

CourseStatus = Literal['completed', 'in_progress', 'planned']
StudentCourseStatus = Literal['completed', 'in_progress', 'planned', 'not_started']
Standing = Literal['freshman', 'sophomore', 'junior', 'senior', 'graduate', 'unspecified']
Grade = Literal['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'F', 'CR', 'NC', 'WU', 'IC', 'W', 'I', 'RP', 'RD', 'AU']
EligibilityStatus = Literal['eligible', 'ineligible', 'unknown']
Availability = Literal['open', 'closed', 'unknown']
Weekday = Literal['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
DeliveryStatus = Literal['pending', 'sent', 'failed']

class FieldError(ApiModel):
    path: str
    message: str

class ApiError(ApiModel):
    code: str
    message: str
    fields: list[FieldError]

class ErrorResponse(ApiModel):
    error: ApiError

class User(ApiModel):
    id: str
    email: str
    full_name: str
    created_at: str

class Profile(ApiModel):
    major_code: str | None
    standing: Standing
    gpa: float | None = Field(ge=0, le=4, allow_inf_nan=False, strict=True)
    earned_units: int | None = Field(ge=0, strict=True)

class CsrfResponse(ApiModel):
    csrf_token: str

class SessionResponse(ApiModel):
    user: User
    csrf_token: str
    expires_at: str

class ProfileResponse(ApiModel):
    user: User
    profile: Profile

class LoginRequest(ApiModel):
    email: str
    password: str

class ProfileUpdate(Profile):
    pass

class Term(ApiModel):
    id: str
    name: str

class Course(ApiModel):
    id: str
    subject: str
    catalog_number: str
    title: str
    description: str | None
    units_min: float | None = Field(ge=0, allow_inf_nan=False)
    units_max: float | None = Field(ge=0, allow_inf_nan=False)
    prerequisite_text: str | None
    corequisite_text: str | None
    restrictions_text: str | None
    catalog_url: str | None

class Meeting(ApiModel):
    days: list[Weekday]
    start_time: str | None = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    end_time: str | None = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    location: str | None
    is_tba: bool

class Instructor(ApiModel):
    name: str

class Section(ApiModel):
    id: str
    term: str
    class_number: str
    section_number: str
    course: Course
    title: str
    mode: str
    units: float | None = Field(ge=0, allow_inf_nan=False)
    open_seats: int | None = Field(ge=0, strict=True)
    availability: Availability
    meetings: list[Meeting]
    instructors: list[Instructor]
    notes: str | None
    source_url: str
    last_checked_at: str | None
    is_stale: bool

class CompareRequest(ApiModel):
    section_ids: list[str] = Field(min_length=2, max_length=2)

    @model_validator(mode="after")
    def unique_ids(self):
        if len(set(self.section_ids)) != len(self.section_ids):
            raise ValueError("IDs must be different")
        return self

class ComparisonResponse(ApiModel):
    sections: list[Section]

class Major(ApiModel):
    major_code: str
    title: str
    degree_type: str
    description: str | None

class CourseRecord(ApiModel):
    course_id: str
    status: CourseStatus
    grade: Grade | None
    term: str | None

class CourseRecordInput(ApiModel):
    status: CourseStatus
    grade: Grade | None
    term: str | None

    @model_validator(mode="after")
    def grade_requires_completed_status(self):
        if self.status != 'completed' and self.grade is not None:
            raise ValueError('Only completed course records can have a grade')
        return self

class EligibilityRequest(ApiModel):
    course_ids: list[str] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def unique_ids(self):
        if len(set(self.course_ids)) != len(self.course_ids):
            raise ValueError("IDs must be different")
        return self

class Eligibility(ApiModel):
    course_id: str
    status: EligibilityStatus
    reasons: list[str]
    missing_course_ids: list[str]

class EligibilityResponse(ApiModel):
    results: list[Eligibility]

class RoadmapEntry(ApiModel):
    course: Course
    term_order: int
    is_required: bool

class StudentRoadmapEntry(ApiModel):
    course: Course
    term_order: int
    is_required: bool
    student_status: StudentCourseStatus
    grade: Grade | None
    eligibility: Eligibility

class ProgressSummary(ApiModel):
    completed_courses: int
    total_required_courses: int
    completion_percent: float

class MajorRoadmap(ApiModel):
    major: Major
    courses: list[RoadmapEntry]

class StudentRoadmap(ApiModel):
    major: Major
    courses: list[StudentRoadmapEntry]
    summary: ProgressSummary
    recommendations: list[str]

class WatchlistEntry(ApiModel):
    section: Section
    added_at: str
    eligibility: Eligibility

class NotificationPreferences(ApiModel):
    enabled: bool
    available: bool

class PreferencesUpdate(ApiModel):
    enabled: bool = Field(strict=True)

class Notification(ApiModel):
    id: str
    section_id: str
    event_type: Literal['section_opened']
    status: DeliveryStatus
    created_at: str
    sent_at: str | None

@dataclass(frozen=True)
class AuthenticatedStudent:
    user_id: str
    student_id: str

@dataclass(frozen=True)
class SessionIdentity:
    student: AuthenticatedStudent
    response: SessionResponse

@dataclass(frozen=True)
class SessionGrant:
    cookie_token: str
    identity: SessionIdentity

@dataclass(frozen=True)
class WatchMutationResult:
    entry: WatchlistEntry
    created: bool

@dataclass(frozen=True)
class RecordMutationResult:
    record: CourseRecord
    created: bool

class RequirementRule(ApiModel):
    kind: Literal["all", "any", "course", "gpa", "units", "standing", "major", "unknown"]
    text: str
    children: list[RequirementRule] = Field(default_factory=list)
    course_id: str | None = None
    minimum_grade: str | None = None
    concurrent: bool = False
    value: str | float | None = None
    operator: Literal['gte', 'gt', 'lte', 'lt', 'eq', 'ne'] = 'gte'

class StudentContext(ApiModel):
    student_id: str
    major_code: str | None
    standing: Standing
    gpa: float | None = Field(ge=0, le=4, allow_inf_nan=False, strict=True)
    earned_units: int | None = Field(ge=0, strict=True)
    course_records: list[CourseRecord]

class ImportedCourse(ApiModel):
    course: Course
    prerequisite_rule: RequirementRule

class SeatOpeningEvent(ApiModel):
    id: str
    section_id: str
    previous_seats: Literal[0]
    new_seats: int = Field(gt=0)
    detected_at: str

class IngestionDocument(ApiModel):
    terms: list[Term]
    courses: list[ImportedCourse]
    sections: list[Section]

class RefreshResult(ApiModel):
    updated_records: int
    event_ids: list[str]
    checked_at: str

class DeliveryTarget(ApiModel):
    delivery_id: str
    event_id: str
    student_id: str
    section_id: str
    message: str

class DeliveryResult(ApiModel):
    accepted: bool
    error_code: str | None

Database = sqlite3.Connection
