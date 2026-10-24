# - Read with SQL parameters; these functions do not commit.
from __future__ import annotations

from app.errors import ApiProblem
from app.schemas import (
    AuthenticatedStudent,
    Database,
    Major,
    MajorRoadmap,
    Page,
    ProgressSummary,
    StudentRoadmap,
    StudentRoadmapEntry,
)
from app.features.prerequisites import check_eligibility
from app.features.courses import get_course

# - Count majors and return major_code-sorted page.
# - Major: {major_code: string, title: string, degree_type: string, description: string | null}.
def list_majors(db: Database, limit: int = 25, offset: int = 0) -> Page[Major]:
    raise NotImplementedError


# - Load major or 404; join roadmap entries with Course records.
# - Sort by term_order then course ID; do not include private student status in public major
#   template.
# - Storage: major_roadmaps(major_code TEXT PK, title TEXT, degree_type TEXT, description TEXT
#   nullable).
# - Storage: roadmap_courses(id INTEGER PK, major_code FK major_roadmaps, course_id FK courses,
#   term_order INTEGER>=1, is_required INTEGER 0/1; UNIQUE(major_code,course_id)).
# - MajorRoadmap: {major: Major, courses: RoadmapEntry[]}.
def get_major_roadmap(db: Database, major_code: str) -> MajorRoadmap:
    raise NotImplementedError


# - Read selected major; missing ->409 PROFILE_INCOMPLETE. Load template and current student
#   records.
# - Annotate each entry with not_started/completed/in_progress/planned, grade or None, and eligibility.
#   Call check_eligibility(db,student.student_id,course_ids) in batches of at most 100 IDs; only
#   completed-course grades and profile GPA/units/standing/major affect eligibility. Refresh the
#   result after profile/history changes; reuse the shared engine rather than a second evaluator.
# - Call calculate_progress and recommend_courses; return complete StudentRoadmap.
# - StudentRoadmap: {major: Major, courses: StudentRoadmapEntry[], summary: ProgressSummary,
#   recommendations: string[]}.
def get_student_roadmap(db: Database, student: AuthenticatedStudent) -> StudentRoadmap:
    raise NotImplementedError


# - Deduplicate required course IDs. Count completed attempts with a passing letter grade
#   (A+ through D-) or CR; do not count F/NC/WU/IC, missing grades, W/I/RP/RD/AU, or unfinished
#   attempts. This is course-credit progress for the demo subset, not a full degree audit.
# - Return 0 for empty denominator, else completed/total*100; no in-progress/planned credit.
# - StudentRoadmapEntry: {course: Course, term_order: number, is_required: boolean, student_status:
#   StudentCourseStatus, grade: Grade | None, eligibility: Eligibility}.
# - ProgressSummary: {completed_courses: number, total_required_courses: number,
#   completion_percent: number}.
def calculate_progress(courses: list[StudentRoadmapEntry]) -> ProgressSummary:
    raise NotImplementedError


# - Select required eligible courses with no earned credit: not_started/planned or a completed
#   attempt without a passing letter grade/CR. Leave in-progress courses out of recommendations.
# - Sort term_order then course ID, deduplicate IDs, return strings.
def recommend_courses(courses: list[StudentRoadmapEntry]) -> list[str]:
    raise NotImplementedError
