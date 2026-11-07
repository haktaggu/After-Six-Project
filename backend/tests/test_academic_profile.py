from contextlib import closing
from pathlib import Path
import sqlite3

from fastapi.testclient import TestClient
import pytest

from app.db.connection import connect, init_db
from app.features.auth import register_user
from app.features.prerequisites import build_student_context
from app.features.profiles import get_profile, list_course_records, put_course_record
from app.main import create_app
from app.schemas import CourseRecordInput, SignupRequest


@pytest.mark.parametrize('stored_default', [3, 4])
def test_new_profiles_default_to_four_on_existing_databases_without_overwriting_preferences(tmp_path, stored_default):
    path = tmp_path / 'test.db'
    schema = (Path(__file__).parents[1] / 'app/db/schema.sql').read_text().replace(
        'recommendation_limit INTEGER NOT NULL DEFAULT 4',
        f'recommendation_limit INTEGER NOT NULL DEFAULT {stored_default}',
    )
    with closing(sqlite3.connect(path)) as db:
        db.executescript(schema)
    init_db(path)
    with closing(connect(path)) as db:
        user = register_user(db, SignupRequest(
            email='new@example.com', password='example-password', full_name='New Student',
        ))
        assert db.execute('SELECT recommendation_limit FROM student_profiles WHERE user_id=?', (user.id,)).fetchone()[0] == 4
        with db:
            db.execute('UPDATE student_profiles SET recommendation_limit=2 WHERE user_id=?', (user.id,))
        init_db(path)
        assert db.execute('SELECT recommendation_limit FROM student_profiles WHERE user_id=?', (user.id,)).fetchone()[0] == 2


def test_profile_and_eligibility_derive_academics_from_course_records(engineering_student):
    db, student = engineering_student
    with db:
        db.execute("UPDATE student_profiles SET standing='senior',gpa=4,earned_units=250 WHERE student_id=?", (student.student_id,))
        assert get_profile(db, student).profile.earned_units == 0

        for course_id, units, grade in [('TEST-1', 28, 'A'), ('TEST-2', 3.5, 'CR'), ('TEST-3', 4, 'F'), ('TEST-4', 3, None)]:
            db.execute('INSERT INTO courses (id,subject,catalog_number,title,units_min,units_max) VALUES (?,?,?,?,?,?)',
                       (course_id, 'TEST', course_id.split('-')[1], course_id, units, units))
            db.commit()
            put_course_record(db, student, course_id, CourseRecordInput(
                status='completed' if grade else 'in_progress', grade=grade, term=None,
            ))

        profile = get_profile(db, student).profile
        context = build_student_context(db, student.student_id)
        assert profile.gpa == context.gpa == pytest.approx(3.5)
        assert profile.earned_units == context.earned_units == 31.5
        assert profile.standing == context.standing == 'sophomore'
        assert [record.earned_units for record in list_course_records(db, student).items] == [28, 3.5, 0, 0]

        put_course_record(db, student, 'TEST-4', CourseRecordInput(status='completed', grade=None, term=None))
        profile = get_profile(db, student).profile
        assert profile.gpa is None
        assert profile.earned_units is None
        assert profile.standing == 'unspecified'


def test_profile_recommendation_limit_migrates_and_caps_the_roadmap(tmp_path):
    path = tmp_path / 'test.db'
    init_db(path)
    credentials = {'email': 'student@example.com', 'password': 'example-password'}
    with closing(connect(path)) as db:
        student = register_user(db, SignupRequest(**credentials, full_name='Test Student'))
        with db:
            db.execute("INSERT INTO major_roadmaps (major_code,title) VALUES ('TEST','Test Major')")
            db.execute("UPDATE student_profiles SET major='TEST' WHERE user_id=?", (student.id,))
            for number in range(1, 7):
                course_id = f'TEST-{number}'
                db.execute('INSERT INTO courses (id,subject,catalog_number,title,prerequisite_text) VALUES (?,?,?,?,?)',
                           (course_id, 'TEST', str(number), course_id, 'None'))
                db.execute('INSERT INTO roadmap_courses (major_code,course_id,term_order) VALUES (?,?,?)',
                           ('TEST', course_id, number))
            db.execute('ALTER TABLE student_profiles DROP COLUMN recommendation_limit')

    with TestClient(create_app(path)) as client:
        csrf = client.get('/api/auth/csrf').raise_for_status().json()['csrf_token']
        login = client.post('/api/auth/login', json=credentials, headers={'X-CSRF-Token': csrf}).raise_for_status()
        headers = {'X-CSRF-Token': login.json()['csrf_token']}

        assert client.get('/api/me').raise_for_status().json()['profile']['recommendation_limit'] == 4
        assert client.get('/api/me/roadmap').raise_for_status().json()['recommendations'] == ['TEST-1', 'TEST-2', 'TEST-3', 'TEST-4']

        saved = client.patch('/api/me', json={'recommendation_limit': 5}, headers=headers).raise_for_status().json()
        assert saved['profile']['major_code'] == 'TEST'
        assert saved['profile']['recommendation_limit'] == 5
        for invalid in (0, 6, '4', True, None):
            response = client.patch('/api/me', json={'recommendation_limit': invalid}, headers=headers)
            assert response.status_code == 422
        roadmap = client.get('/api/me/roadmap').raise_for_status().json()
        assert roadmap['recommendations'] == [f'TEST-{number}' for number in range(1, 6)]
        assert len(roadmap['courses']) == 6

        saved = client.patch('/api/me', json={'major_code': None}, headers=headers).raise_for_status().json()
        assert saved['profile']['recommendation_limit'] == 5
        assert saved['profile']['major_code'] is None

        client.patch('/api/me', json={'major_code': 'TEST', 'recommendation_limit': 1}, headers=headers).raise_for_status()
        assert client.get('/api/me/roadmap').raise_for_status().json()['recommendations'] == ['TEST-1']
