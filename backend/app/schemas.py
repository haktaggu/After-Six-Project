from __future__ import annotations

from dataclasses import dataclass
import sqlite3
from typing import Annotated, Generic, Literal, TypeVar
from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator

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
RecommendationLimit = Annotated[int, Field(strict=True, ge=1, le=5)]

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
    earned_units: float | None = Field(ge=0, allow_inf_nan=False)
    recommendation_limit: RecommendationLimit

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

class SignupRequest(ApiModel):
    full_name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)

class ProfileUpdate(ApiModel):
    major_code: str | None = None
    recommendation_limit: RecommendationLimit = 4

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
    earned_units: float | None = None
    course_id: str
    status: CourseStatus
    grade: Grade | None
    term: str | None
    section_ids: list[str] = Field(default_factory=list)

class CourseRecordInput(ApiModel):
    status: CourseStatus
    grade: Grade | None
    term: str | None
    section_ids: list[str] = Field(default_factory=list)
    requirement_confirmations: dict[str, StrictBool] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_record(self):
        if self.status != 'completed' and self.grade is not None:
            raise ValueError('Only completed course records can have a grade')
        if self.section_ids and self.term is None:
            raise ValueError('Choose a term for your selected sections')
        if len(set(self.section_ids)) != len(self.section_ids):
            raise ValueError('Choose each section once')
        return self

class CalendarSection(ApiModel):
    id: str
    section_number: str
    title: str
    meetings: list[Meeting]

class CalendarCourse(ApiModel):
    course_id: str
    title: str
    term: Term | None
    status: Literal['planned', 'in_progress']
    sections: list[CalendarSection]

class EligibilityRequest(ApiModel):
    course_ids: list[str] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def unique_ids(self):
        if len(set(self.course_ids)) != len(self.course_ids):
            raise ValueError("IDs must be different")
        return self

class RequirementConfirmation(ApiModel):
    id: str
    text: str
    confirmed: bool
    satisfied: bool = False

class CourseRequirementCheck(ApiModel):
    course_id: str
    minimum_grade: str | None
    status: EligibilityStatus
    recorded_status: CourseStatus | None
    grade: Grade | None
    alternative: bool = False
    concurrent: bool = False

class RequirementConfirmationUpdate(ApiModel):
    confirmed: bool = Field(strict=True)

class EnrollmentRequirement(ApiModel):
    kind: Literal['all', 'any', 'course', 'confirmation', 'check']
    text: str
    status: EligibilityStatus
    children: list[EnrollmentRequirement] = Field(default_factory=list)
    course: CourseRequirementCheck | None = None
    confirmation: RequirementConfirmation | None = None

class Eligibility(ApiModel):
    course_id: str
    status: EligibilityStatus
    reasons: list[str]
    missing_course_ids: list[str]
    additional_requirements: list[RequirementConfirmation] = Field(default_factory=list)
    course_requirements: list[CourseRequirementCheck] = Field(default_factory=list)
    requirements: EnrollmentRequirement | None = None
    source_url: str | None = None

class EligibilityResponse(ApiModel):
    results: list[Eligibility]

class RoadmapEntry(ApiModel):
    course: Course
    term_order: int
    is_required: bool

class PrerequisiteLink(ApiModel):
    course_id: str
    alternative: bool = False

class StudentRoadmapEntry(ApiModel):
    course: Course
    term_order: int
    is_required: bool
    student_status: StudentCourseStatus
    grade: Grade | None
    eligibility: Eligibility
    prerequisites: list[PrerequisiteLink] = Field(default_factory=list)

class ProgressSummary(ApiModel):
    completed_courses: int
    total_required_courses: int
    completion_percent: float

class RoadmapRequirement(ApiModel):
    term_order: int
    label: str
    units: int | None
    flexible: bool

class MajorRoadmap(ApiModel):
    major: Major
    courses: list[RoadmapEntry]
    requirements: list[RoadmapRequirement] = Field(default_factory=list)

CourseSuggestionStatus = Literal['ready', 'after_current', 'needs_review', 'requirements_remaining']

class CourseSuggestion(ApiModel):
    course_id: str
    title: str
    status: CourseSuggestionStatus
    reason: str

class StudentRoadmap(ApiModel):
    major: Major
    courses: list[StudentRoadmapEntry]
    requirements: list[RoadmapRequirement] = Field(default_factory=list)
    summary: ProgressSummary
    recommendations: list[str] = Field(description='Eligible required course IDs for clients that use the ready-only list.')
    suggestions: list[CourseSuggestion]
    recommendation_limit: RecommendationLimit

class WatchlistEntry(ApiModel):
    section: Section
    added_at: str
    eligibility: Eligibility

class NotificationPreferences(ApiModel):
    enabled: bool
    available: bool
    webhook_url: str | None = None

class PreferencesUpdate(ApiModel):
    enabled: bool = Field(strict=True)
    webhook_url: str | None = None

class Notification(ApiModel):
    id: str
    section_id: str
    event_type: Literal['section_opened']
    status: DeliveryStatus
    created_at: str
    sent_at: str | None
    is_read: bool

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
    kind: Literal["all", "any", "course", "gpa", "units", "standing", "major", "conditional_workshop", "first_attempt", "unknown"]
    text: str
    children: list[RequirementRule] = Field(default_factory=list)
    course_id: str | None = None
    minimum_grade: str | None = None
    concurrent: bool = False
    value: str | float | None = None
    operator: Literal['gte', 'gt', 'lte', 'lt', 'eq', 'ne'] = 'gte'

class EnrollmentPolicy(ApiModel):
    course_id: str
    source_url: str
    rule: RequirementRule

class StudentContext(ApiModel):
    student_id: str
    major_code: str | None
    standing: Standing
    gpa: float | None = Field(ge=0, le=4, allow_inf_nan=False, strict=True)
    earned_units: float | None = Field(ge=0, allow_inf_nan=False)
    course_records: list[CourseRecord]
    confirmed_requirements: dict[str, list[str]] = Field(default_factory=dict)

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
