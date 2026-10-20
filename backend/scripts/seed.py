from __future__ import annotations

import argparse
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from app.db.connection import connect, database_path, init_db
from app.features.auth import hash_password
from app.schemas import CourseRecordInput, Profile

DEMO_EMAIL = 'demo@oursjsu.test'
DEMO_PASSWORD = 'oursjsu-demo-password'
DEMO_USER_ID = str(uuid5(NAMESPACE_URL, 'oursjsu:demo-student'))
DEMO_STUDENT_ID = 'demo-student'
PLAN_PATH = Path(__file__).resolve().parents[1] / 'demo' / 'computer-engineering.json'


@dataclass(frozen=True)
class DemoSeedResult:
    missing_course_ids: tuple[str, ...] = ()
    history_created: bool = False


def seed_demo_account(path: Path) -> str:
    plan = json.loads(PLAN_PATH.read_text())
    academic = Profile(major_code=plan['major_code'], **plan['profile'])
    with closing(connect(path)) as db, db:
        db.execute('BEGIN IMMEDIATE')
        db.execute(
            'INSERT INTO major_roadmaps (major_code,title,degree_type,description) VALUES (?,?,?,?) '
            'ON CONFLICT(major_code) DO NOTHING',
            (plan['major_code'], plan['title'], plan['degree_type'], plan['description']),
        )
        user = db.execute('SELECT id FROM users WHERE email = ?', (DEMO_EMAIL,)).fetchone()
        user_id = user[0] if user else DEMO_USER_ID
        if user is None:
            db.execute(
                'INSERT INTO users (id,username,email,full_name,password_hash,created_at) VALUES (?,?,?,?,?,?)',
                (user_id, 'demo', DEMO_EMAIL, 'Demo Student', hash_password(DEMO_PASSWORD), datetime.now(timezone.utc).isoformat()),
            )
        profile = db.execute('SELECT student_id FROM student_profiles WHERE user_id = ?', (user_id,)).fetchone()
        student_id = profile[0] if profile else DEMO_STUDENT_ID
        if profile is None:
            db.execute('INSERT INTO student_profiles (student_id,user_id,major,standing,gpa,earned_units) VALUES (?,?,?,?,?,?)',
                       (student_id, user_id, academic.major_code, academic.standing, academic.gpa, academic.earned_units))
        db.execute('INSERT INTO notification_preferences (student_id,enabled) VALUES (?,0) '
                   'ON CONFLICT(student_id) DO NOTHING', (student_id,))
    return student_id


def seed_demo_courses(path: Path) -> DemoSeedResult:
    plan = json.loads(PLAN_PATH.read_text())
    with closing(connect(path)) as db, db:
        db.execute('BEGIN IMMEDIATE')
        profile = db.execute(
            'SELECT p.student_id FROM student_profiles p JOIN users u ON u.id = p.user_id WHERE u.email = ?',
            (DEMO_EMAIL,),
        ).fetchone()
        if profile is None:
            raise ValueError('Create the demo account before its course history.')
        courses = plan['courses']
        missing = tuple(entry['course_id'] for entry in courses if db.execute(
            'SELECT 1 FROM courses WHERE id = ?', (entry['course_id'],),
        ).fetchone() is None)
        if missing:
            return DemoSeedResult(missing_course_ids=missing)
        db.executemany(
            'INSERT INTO roadmap_courses (major_code,course_id,term_order,is_required) VALUES (?,?,?,1) '
            'ON CONFLICT(major_code,course_id) DO NOTHING',
            [(plan['major_code'], entry['course_id'], entry['term_order']) for entry in courses],
        )
        student_id = profile[0]
        seed_name = f'computer-engineering-history:{student_id}'
        if db.execute('SELECT 1 FROM demo_seed_state WHERE name = ?', (seed_name,)).fetchone():
            return DemoSeedResult()
        has_history = db.execute('SELECT 1 FROM student_course_attempts WHERE student_id = ? LIMIT 1', (student_id,)).fetchone()
        if has_history is None:
            records = [
                (entry['course_id'], CourseRecordInput(status=entry['initial_status'], grade=entry['initial_grade'], term=None))
                for entry in courses if entry['initial_status']
            ]
            db.executemany(
                'INSERT INTO student_course_attempts (student_id,course_id,status,grade,term) VALUES (?,?,?,?,?)',
                [(student_id, course_id, record.status, record.grade, record.term) for course_id, record in records],
            )
        db.execute('INSERT INTO demo_seed_state (name,completed_at) VALUES (?,?)',
                   (seed_name, datetime.now(timezone.utc).isoformat()))
    return DemoSeedResult(history_created=has_history is None)


def main() -> None:
    parser = argparse.ArgumentParser(description='Ensure the demo account and link its Computer Engineering courses when imported.')
    parser.parse_args()
    path = database_path()
    init_db(path)
    seed_demo_account(path)
    result = seed_demo_courses(path)
    if result.missing_course_ids:
        print(f'Demo account ready. Waiting for imported courses: {", ".join(result.missing_course_ids)}.')
    else:
        print('Demo account and Computer Engineering roadmap ready; existing student edits preserved.')


if __name__ == '__main__':
    main()
