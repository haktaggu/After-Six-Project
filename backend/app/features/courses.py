from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json

from app.errors import ApiProblem
from app.schemas import CompareRequest, ComparisonResponse, Course, Database, Page, Section, Term

COURSE_FIELDS = 'id,subject,catalog_number,title,description,units_min,units_max,prerequisite_text,corequisite_text,restrictions_text,catalog_url'


def search_filter(q: str | None) -> tuple[str, list[str]]:
    if not q:
        return '', []
    q = q.strip().lower().replace(' ', '').replace('-', '')
    q = q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
    return " AND (replace(replace(lower(c.id),' ',''),'-','') LIKE ? ESCAPE '\\' OR replace(replace(lower(c.title),' ',''),'-','') LIKE ? ESCAPE '\\')", [f'%{q}%', f'%{q}%']


def list_terms(db: Database, limit: int = 25, offset: int = 0) -> Page[Term]:
    total = db.execute('SELECT count(*) FROM terms').fetchone()[0]
    rows = db.execute('SELECT id,name FROM terms ORDER BY id LIMIT ? OFFSET ?', (limit, offset))
    return Page(items=[Term(id=r[0], name=r[1]) for r in rows], total=total, limit=limit, offset=offset)


def search_courses(db: Database, q: str | None = None, limit: int = 25, offset: int = 0) -> Page[Course]:
    where, args = search_filter(q)
    total = db.execute('SELECT count(*) FROM courses c WHERE 1=1' + where, args).fetchone()[0]
    rows = db.execute('SELECT c.id FROM courses c WHERE 1=1' + where + ' ORDER BY c.id LIMIT ? OFFSET ?', [*args, limit, offset])
    return Page(items=[get_course(db, r[0]) for r in rows], total=total, limit=limit, offset=offset)


def get_course(db: Database, course_id: str) -> Course:
    row = db.execute('SELECT ' + COURSE_FIELDS + ' FROM courses WHERE id=?', (course_id,)).fetchone()
    if row is None:
        raise ApiProblem(404, 'NOT_FOUND', 'Course not found')
    return Course(**dict(zip(COURSE_FIELDS.split(','), row)))


def search_sections(db: Database, term: str, q: str | None = None, course_id: str | None = None,
                    limit: int = 25, offset: int = 0) -> Page[Section]:
    where, args = search_filter(q)
    where = 's.term=?' + where
    args = [term, *args]
    if course_id is not None:
        where += ' AND s.course_id=?'
        args.append(course_id)
    sql = ' FROM sections s JOIN courses c ON c.id=s.course_id WHERE ' + where
    total = db.execute('SELECT count(*)' + sql, args).fetchone()[0]
    rows = db.execute('SELECT s.id' + sql + ' ORDER BY s.id LIMIT ? OFFSET ?', [*args, limit, offset])
    return Page(items=[get_section(db, r[0]) for r in rows], total=total, limit=limit, offset=offset)


def get_section(db: Database, section_id: str) -> Section:
    cur = db.execute('SELECT * FROM sections WHERE id=?', (section_id,))
    row = cur.fetchone()
    if row is None:
        raise ApiProblem(404, 'NOT_FOUND', 'Section not found')
    return serialize_section(db, dict(zip([c[0] for c in cur.description], row)))


def compare_sections(db: Database, body: CompareRequest) -> ComparisonResponse:
    sections = [get_section(db, idx) for idx in body.section_ids]
    if sections[0].term != sections[1].term:
        raise ApiProblem(422, 'VALIDATION_ERROR', 'Choose two sections from the same term')
    return ComparisonResponse(sections=sections)


def serialize_section(db: Database, row: dict[str, object]) -> Section:
    data = dict(row)
    course = get_course(db, data.pop('course_id'))
    meetings = [dict(days=json.loads(r[0]), start_time=r[1], end_time=r[2], location=r[3], is_tba=bool(r[4]))
                for r in db.execute('SELECT days_json,start_time,end_time,location,is_tba FROM meetings WHERE section_id=? ORDER BY id', (row['id'],))]
    instructors = [dict(name=r[0]) for r in db.execute('SELECT name FROM instructors WHERE section_id=? ORDER BY id', (row['id'],))]
    seats = data['open_seats']
    checked = data['last_checked_at']
    stale = checked is None or datetime.now(timezone.utc) - datetime.fromisoformat(checked) > timedelta(minutes=5)
    return Section(**data, course=course, meetings=meetings, instructors=instructors,
                   availability='unknown' if seats is None else 'open' if seats > 0 else 'closed', is_stale=stale)
