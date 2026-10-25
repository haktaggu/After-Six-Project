from __future__ import annotations

from app.errors import ApiProblem
from app.features.courses import get_course
from app.features.prerequisites import check_eligibility, evaluate_grade
from app.schemas import AuthenticatedStudent, Database, Major, MajorRoadmap, Page, ProgressSummary, RoadmapEntry, StudentRoadmap, StudentRoadmapEntry


def list_majors(db: Database, limit: int = 25, offset: int = 0) -> Page[Major]:
    total = db.execute('SELECT count(*) FROM major_roadmaps').fetchone()[0]
    rows = db.execute('SELECT major_code,title,degree_type,description FROM major_roadmaps ORDER BY major_code LIMIT ? OFFSET ?', (limit, offset))
    return Page(items=[Major(**dict(zip(('major_code', 'title', 'degree_type', 'description'), r))) for r in rows], total=total, limit=limit, offset=offset)


def get_major_roadmap(db: Database, major_code: str) -> MajorRoadmap:
    row = db.execute('SELECT major_code,title,degree_type,description FROM major_roadmaps WHERE major_code=?', (major_code,)).fetchone()
    if row is None:
        raise ApiProblem(404, 'NOT_FOUND', 'Major not found')
    major = Major(**dict(zip(('major_code', 'title', 'degree_type', 'description'), row)))
    rows = db.execute('SELECT course_id,term_order,is_required FROM roadmap_courses WHERE major_code=? ORDER BY term_order,course_id', (major_code,))
    return MajorRoadmap(major=major, courses=[RoadmapEntry(course=get_course(db, r[0]), term_order=r[1], is_required=bool(r[2])) for r in rows])


def get_student_roadmap(db: Database, student: AuthenticatedStudent) -> StudentRoadmap:
    row = db.execute('SELECT major FROM student_profiles WHERE student_id=?', (student.student_id,)).fetchone()
    if not row or not row[0]:
        raise ApiProblem(409, 'PROFILE_INCOMPLETE', 'Choose your major on the Dashboard')
    template = get_major_roadmap(db, row[0])
    records = {r[0]: r[1:] for r in db.execute('SELECT course_id,status,grade FROM student_course_attempts WHERE student_id=?', (student.student_id,))}
    ids = [r.course.id for r in template.courses]
    eligibility = {}
    for i in range(0, len(ids), 100):
        eligibility.update({r.course_id: r for r in check_eligibility(db, student.student_id, ids[i:i + 100]).results})
    courses = [StudentRoadmapEntry(**r.model_dump(), student_status=records.get(r.course.id, ('not_started', None))[0],
                                   grade=records.get(r.course.id, ('not_started', None))[1], eligibility=eligibility[r.course.id]) for r in template.courses]
    return StudentRoadmap(major=template.major, courses=courses, summary=calculate_progress(courses), recommendations=recommend_courses(courses))


def calculate_progress(courses: list[StudentRoadmapEntry]) -> ProgressSummary:
    required = {c.course.id for c in courses if c.is_required}
    completed = {c.course.id for c in courses if c.is_required and c.student_status == 'completed' and evaluate_grade(c.grade, None) == 'eligible'}
    return ProgressSummary(completed_courses=len(completed), total_required_courses=len(required), completion_percent=100 * len(completed) / len(required) if required else 0)


def recommend_courses(courses: list[StudentRoadmapEntry]) -> list[str]:
    return list(dict.fromkeys(c.course.id for c in sorted(courses, key=lambda c: (c.term_order, c.course.id))
                              if c.is_required and c.eligibility.status == 'eligible' and c.student_status != 'in_progress'
                              and not (c.student_status == 'completed' and evaluate_grade(c.grade, None) == 'eligible')))
