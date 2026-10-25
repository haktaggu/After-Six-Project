from __future__ import annotations

from datetime import datetime, timezone

from app.features.courses import get_section
from app.features.prerequisites import check_eligibility
from app.schemas import AuthenticatedStudent, Database, Page, WatchMutationResult, WatchlistEntry


def list_watchlist(db: Database, student: AuthenticatedStudent, term: str | None = None, limit: int = 25, offset: int = 0) -> Page[WatchlistEntry]:
    where = 'student_id=? AND active=1'
    args = [student.student_id]
    if term is not None:
        where += ' AND term=?'
        args.append(term)
    total = db.execute('SELECT count(*) FROM watchlists WHERE ' + where, args).fetchone()[0]
    rows = db.execute('SELECT section_id,added_at FROM watchlists WHERE ' + where + ' ORDER BY added_at DESC,section_id LIMIT ? OFFSET ?', [*args, limit, offset]).fetchall()
    sections = [get_section(db, r[0]) for r in rows]
    ids = list(dict.fromkeys(s.course.id for s in sections))
    eligibility = {r.course_id: r for r in check_eligibility(db, student.student_id, ids).results} if ids else {}
    return Page(items=[WatchlistEntry(section=s, added_at=r[1], eligibility=eligibility[s.course.id]) for s, r in zip(sections, rows)], total=total, limit=limit, offset=offset)


def add_watch(db: Database, student: AuthenticatedStudent, section_id: str) -> WatchMutationResult:
    section = get_section(db, section_id)
    eligibility = check_eligibility(db, student.student_id, [section.course.id]).results[0]
    now = datetime.now(timezone.utc).isoformat()
    with db:
        db.execute('BEGIN IMMEDIATE')
        exists = db.execute('SELECT 1 FROM watchlists WHERE student_id=? AND section_id=?', (student.student_id, section_id)).fetchone()
        db.execute('INSERT INTO watchlists (student_id,section_id,term,added_at,active) VALUES (?,?,?,?,1) '
                   'ON CONFLICT(student_id,section_id) DO UPDATE SET active=1,added_at=excluded.added_at',
                   (student.student_id, section_id, section.term, now))
    return WatchMutationResult(WatchlistEntry(section=section, added_at=now, eligibility=eligibility), not bool(exists))


def remove_watch(db: Database, student: AuthenticatedStudent, section_id: str) -> None:
    with db:
        db.execute('UPDATE watchlists SET active=0 WHERE student_id=? AND section_id=?', (student.student_id, section_id))
