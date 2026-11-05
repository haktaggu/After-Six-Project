from __future__ import annotations

from app.errors import ApiProblem
from app.features.courses import get_course, get_section
from app.features.prerequisites import build_student_context, course_earned_units, save_requirement_confirmations
from app.schemas import (
    AuthenticatedStudent, CalendarCourse, CalendarSection, CourseRecord, CourseRecordInput, Database,
    Page, ProfileResponse, ProfileUpdate, RecordMutationResult, Term,
)


def saved_section_ids(db: Database, attempt_id: int) -> list[str]:
    return [section_id for section_id, in db.execute(
        'SELECT section_id FROM course_attempt_sections WHERE attempt_id=? ORDER BY section_id',
        (attempt_id,),
    )]


def get_profile(db: Database, student: AuthenticatedStudent) -> ProfileResponse:
    row = db.execute('SELECT u.id,u.email,u.full_name,u.created_at,p.recommendation_limit '
                     'FROM users u JOIN student_profiles p ON p.user_id=u.id WHERE u.id=? AND p.student_id=?',
                     (student.user_id, student.student_id)).fetchone()
    if row is None:
        raise ApiProblem(404, 'NOT_FOUND', 'Profile not found')
    context = build_student_context(db, student.student_id)
    return ProfileResponse(
        user=dict(zip(('id', 'email', 'full_name', 'created_at'), row[:4])),
        profile={
            **context.model_dump(include={'major_code', 'standing', 'gpa', 'earned_units'}),
            'recommendation_limit': row[4],
        },
    )


def update_profile(db: Database, student: AuthenticatedStudent, body: ProfileUpdate) -> ProfileResponse:
    if body.major_code is not None and not db.execute('SELECT 1 FROM major_roadmaps WHERE major_code=?', (body.major_code,)).fetchone():
        raise ApiProblem(422, 'VALIDATION_ERROR', 'Choose an available major')
    with db:
        if 'major_code' in body.model_fields_set:
            db.execute('UPDATE student_profiles SET major=? WHERE student_id=?',
                       (body.major_code, student.student_id))
        if 'recommendation_limit' in body.model_fields_set:
            db.execute('UPDATE student_profiles SET recommendation_limit=? WHERE student_id=?',
                       (body.recommendation_limit, student.student_id))
    return get_profile(db, student)


def list_course_records(db: Database, student: AuthenticatedStudent, limit: int = 25, offset: int = 0) -> Page[CourseRecord]:
    total = db.execute('SELECT count(*) FROM student_course_attempts WHERE student_id=?', (student.student_id,)).fetchone()[0]
    rows = db.execute('SELECT r.id,r.course_id,r.status,r.grade,r.term,c.units_min,c.units_max '
                      'FROM student_course_attempts r JOIN courses c ON c.id=r.course_id '
                      'WHERE r.student_id=? ORDER BY r.course_id LIMIT ? OFFSET ?',
                      (student.student_id, limit, offset))
    return Page(items=[
        CourseRecord(course_id=course_id, status=status, grade=grade, term=term,
                     earned_units=course_earned_units(status, grade, min_units, max_units),
                     section_ids=saved_section_ids(db, attempt_id))
        for attempt_id, course_id, status, grade, term, min_units, max_units in rows
    ], total=total, limit=limit, offset=offset)


def get_calendar(db: Database, student: AuthenticatedStudent) -> list[CalendarCourse]:
    rows = db.execute(
        'SELECT r.id,r.course_id,c.title,r.status,r.term,t.name FROM student_course_attempts r '
        'JOIN courses c ON c.id=r.course_id LEFT JOIN terms t ON t.id=r.term '
        "WHERE r.student_id=? AND r.status IN ('in_progress','planned') ORDER BY r.course_id",
        (student.student_id,),
    )
    calendar = []
    for attempt_id, course_id, title, status, term_id, term_name in rows:
        sections = [get_section(db, section_id) for section_id in saved_section_ids(db, attempt_id)]
        calendar.append(CalendarCourse(
            course_id=course_id, title=title, status=status,
            term=Term(id=term_id, name=term_name) if term_id else None,
            sections=[CalendarSection(id=s.id, section_number=s.section_number, title=s.title, meetings=s.meetings)
                      for s in sections if s.course.id == course_id and s.term == term_id],
        ))
    return calendar


def put_course_record(db: Database, student: AuthenticatedStudent, course_id: str, body: CourseRecordInput) -> RecordMutationResult:
    get_course(db, course_id)
    if body.term is not None and not db.execute('SELECT 1 FROM terms WHERE id=?', (body.term,)).fetchone():
        raise ApiProblem(422, 'VALIDATION_ERROR', 'Choose an imported term')
    with db:
        db.execute('BEGIN IMMEDIATE')
        previous = db.execute('SELECT id,term FROM student_course_attempts WHERE student_id=? AND course_id=?',
                              (student.student_id, course_id)).fetchone()
        section_ids = body.section_ids
        if 'section_ids' not in body.model_fields_set and previous and previous[1] == body.term:
            section_ids = saved_section_ids(db, previous[0])
        if section_ids:
            available = {section_id for section_id, in db.execute(
                'SELECT id FROM sections WHERE course_id=? AND term=?', (course_id, body.term),
            )}
            if not available.issuperset(section_ids):
                raise ApiProblem(422, 'VALIDATION_ERROR', 'Choose sections from this course and term')
        attempt_id, = db.execute(
            'INSERT INTO student_course_attempts (student_id,course_id,status,grade,term) VALUES (?,?,?,?,?) '
            'ON CONFLICT(student_id,course_id) DO UPDATE SET status=excluded.status,grade=excluded.grade,term=excluded.term RETURNING id',
            (student.student_id, course_id, body.status, body.grade, body.term),
        ).fetchone()
        db.execute('DELETE FROM course_attempt_sections WHERE attempt_id=?', (attempt_id,))
        db.executemany('INSERT INTO course_attempt_sections (attempt_id,section_id) VALUES (?,?)',
                       [(attempt_id, section_id) for section_id in section_ids])
        save_requirement_confirmations(db, student.student_id, course_id, body.requirement_confirmations)
    record = CourseRecord(course_id=course_id, status=body.status, grade=body.grade, term=body.term,
                          section_ids=sorted(section_ids))
    return RecordMutationResult(record, previous is None)


def delete_course_record(db: Database, student: AuthenticatedStudent, course_id: str) -> None:
    with db:
        db.execute('DELETE FROM student_course_attempts WHERE student_id=? AND course_id=?', (student.student_id, course_id))
