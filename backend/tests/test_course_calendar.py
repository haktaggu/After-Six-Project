from contextlib import closing

from fastapi.testclient import TestClient

from app.db.connection import connect
from app.main import create_app


def test_calendar_shows_saved_sections_and_untimed_courses_for_the_signed_in_student(tmp_path):
    path = tmp_path / 'test.db'
    with TestClient(create_app(path)) as client:
        assert client.get('/api/me/course-calendar').status_code == 401
        csrf = client.get('/api/auth/csrf').raise_for_status().json()['csrf_token']
        signup = client.post('/api/auth/signup', headers={'X-CSRF-Token': csrf},
                             json={'email': 'student@example.com', 'password': 'example-password', 'full_name': 'Test Student'})
        headers = {'X-CSRF-Token': signup.raise_for_status().json()['csrf_token']}
        with closing(connect(path)) as db, db:
            db.executemany("INSERT INTO terms (id,name) VALUES (?,?)",
                           [('fall-2026', 'Fall 2026'), ('spring-2027', 'Spring 2027')])
            for course_id, subject, number in [('CHEM-10', 'CHEM', '10'), ('MATH-20', 'MATH', '20'), ('ART-30', 'ART', '30')]:
                db.execute('INSERT INTO courses (id,subject,catalog_number,title) VALUES (?,?,?,?)',
                           (course_id, subject, number, f'Course {course_id}'))
            for section_id, term, course_id, type_title in [
                ('lecture', 'fall-2026', 'CHEM-10', 'Chemistry Lecture'),
                ('lab', 'fall-2026', 'CHEM-10', 'Chemistry Lab'),
                ('next-lecture', 'spring-2027', 'CHEM-10', 'Spring Chemistry'),
                ('math', 'spring-2027', 'MATH-20', 'Mathematics'),
            ]:
                db.execute(
                    'INSERT INTO sections (id,term,class_number,section_number,course_id,title,mode,source_url) VALUES (?,?,?,1,?,?,?,?)',
                    (section_id, term, section_id, course_id, type_title, 'In Person', 'https://www.sjsu.edu/'),
                )
            db.executemany('INSERT INTO meetings (section_id,days_json,start_time,end_time,location) VALUES (?,?,?,?,?)',
                           [('lecture', '["mon","wed"]', '09:00', '10:15', 'Room A'), ('lab', '["fri"]', '14:00', '16:00', 'Lab B')])

        def save(course, **body):
            return client.put(f'/api/me/course-records/{course}', headers=headers, json={'grade': None, **body})

        current = {'status': 'in_progress', 'term': 'fall-2026'}
        saved = save('CHEM-10', **current, section_ids=['lecture', 'lab']).raise_for_status().json()
        assert saved['section_ids'] == ['lab', 'lecture']
        save('MATH-20', status='planned', term='spring-2027', section_ids=['math']).raise_for_status()
        save('ART-30', status='planned', term=None).raise_for_status()

        for invalid in (['math'], ['next-lecture'], ['lecture', 'lecture']):
            assert save('CHEM-10', **current, section_ids=invalid).status_code == 422
        assert save('CHEM-10', **current).raise_for_status().json()['section_ids'] == ['lab', 'lecture']
        records = {item['course_id']: item for item in client.get('/api/me/course-records').raise_for_status().json()['items']}
        assert records['CHEM-10']['section_ids'] == ['lab', 'lecture']
        calendar = {item['course_id']: item for item in client.get('/api/me/course-calendar').raise_for_status().json()}
        assert calendar['CHEM-10']['status'] == 'in_progress'
        assert calendar['CHEM-10']['term']['name'] == 'Fall 2026'
        assert [(row['title'], row['meetings'][0]['location']) for row in calendar['CHEM-10']['sections']] == [
            ('Chemistry Lab', 'Lab B'), ('Chemistry Lecture', 'Room A'),
        ]
        assert calendar['MATH-20']['status'] == 'planned'
        assert calendar['MATH-20']['sections'][0]['meetings'] == []
        assert calendar['ART-30']['sections'] == []

        save('CHEM-10', status='completed', grade='B', term='fall-2026').raise_for_status()
        assert 'CHEM-10' not in {item['course_id'] for item in client.get('/api/me/course-calendar').json()}
        save('CHEM-10', status='planned', term='spring-2027').raise_for_status()
        calendar = {item['course_id']: item for item in client.get('/api/me/course-calendar').raise_for_status().json()}
        assert calendar['CHEM-10']['sections'] == []
        client.delete('/api/me/course-records/MATH-20', headers=headers).raise_for_status()
        assert 'MATH-20' not in {item['course_id'] for item in client.get('/api/me/course-calendar').json()}
