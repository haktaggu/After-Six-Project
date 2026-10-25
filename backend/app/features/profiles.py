from __future__ import annotations

from app.errors import ApiProblem
from app.features.courses import get_course
from app.schemas import AuthenticatedStudent, CourseRecord, CourseRecordInput, Database, Page, ProfileResponse, ProfileUpdate, RecordMutationResult


def get_profile(db: Database, student: AuthenticatedStudent) -> ProfileResponse:
    row = db.execute('SELECT u.id,u.email,u.full_name,u.created_at,p.major,p.standing,p.gpa,p.earned_units '
                     'FROM users u JOIN student_profiles p ON p.user_id=u.id WHERE u.id=? AND p.student_id=?',
                     (student.user_id, student.student_id)).fetchone()
    if row is None:
        raise ApiProblem(404, 'NOT_FOUND', 'Profile not found')
    return ProfileResponse(user=dict(zip(('id', 'email', 'full_name', 'created_at'), row[:4])),
                           profile=dict(zip(('major_code', 'standing', 'gpa', 'earned_units'), row[4:])))


def update_profile(db: Database, student: AuthenticatedStudent, body: ProfileUpdate) -> ProfileResponse:
    if body.major_code is not None and not db.execute('SELECT 1 FROM major_roadmaps WHERE major_code=?', (body.major_code,)).fetchone():
        raise ApiProblem(422, 'VALIDATION_ERROR', 'Choose an available major')
    with db:
        db.execute('UPDATE student_profiles SET major=?,standing=?,gpa=?,earned_units=? WHERE student_id=?',
                   (body.major_code, body.standing, body.gpa, body.earned_units, student.student_id))
    return get_profile(db, student)


def list_course_records(db: Database, student: AuthenticatedStudent, limit: int = 25, offset: int = 0) -> Page[CourseRecord]:
    total = db.execute('SELECT count(*) FROM student_course_attempts WHERE student_id=?', (student.student_id,)).fetchone()[0]
    rows = db.execute('SELECT course_id,status,grade,term FROM student_course_attempts WHERE student_id=? ORDER BY course_id LIMIT ? OFFSET ?',
                      (student.student_id, limit, offset))
    return Page(items=[CourseRecord(**dict(zip(('course_id', 'status', 'grade', 'term'), r))) for r in rows], total=total, limit=limit, offset=offset)


def put_course_record(db: Database, student: AuthenticatedStudent, course_id: str, body: CourseRecordInput) -> RecordMutationResult:
    get_course(db, course_id)
    if body.term is not None and not db.execute('SELECT 1 FROM terms WHERE id=?', (body.term,)).fetchone():
        raise ApiProblem(422, 'VALIDATION_ERROR', 'Choose an imported term')
    with db:
        db.execute('BEGIN IMMEDIATE')
        exists = db.execute('SELECT 1 FROM student_course_attempts WHERE student_id=? AND course_id=?', (student.student_id, course_id)).fetchone()
        db.execute('INSERT INTO student_course_attempts (student_id,course_id,status,grade,term) VALUES (?,?,?,?,?) '
                   'ON CONFLICT(student_id,course_id) DO UPDATE SET status=excluded.status,grade=excluded.grade,term=excluded.term',
                   (student.student_id, course_id, body.status, body.grade, body.term))
    return RecordMutationResult(CourseRecord(course_id=course_id, **body.model_dump()), not bool(exists))


def delete_course_record(db: Database, student: AuthenticatedStudent, course_id: str) -> None:
    with db:
        db.execute('DELETE FROM student_course_attempts WHERE student_id=? AND course_id=?', (student.student_id, course_id))
