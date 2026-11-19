from contextlib import closing

from fastapi.testclient import TestClient
import pytest

from app.db.connection import connect, init_db
from app.features.ingest import normalize_course, upsert_catalog
from app.features.prerequisites import check_eligibility, parse_requirement_rule, update_requirement_confirmation
from app.features.profiles import list_course_records, put_course_record
from app.errors import ApiProblem
from app.features.roadmap import get_student_roadmap
from app.main import create_app
from app.schemas import CourseRecordInput, IngestionDocument


@pytest.mark.parametrize(('subject', 'number'), [('MATH', 31), ('MATH', 32), ('CHEM', 21)])
def test_confirmation_respects_grades_and_projects_current_courses(engineering_student, subject, number):
    db, student = engineering_student
    prerequisite_id = f'{subject}-{number - 1}'
    course_id = f'{subject}-{number}'
    with db:
        upsert_catalog(db, IngestionDocument(terms=[], sections=[], courses=[
            normalize_course({'subject': subject, 'catalog_number': str(number - 1), 'title': 'First course'}),
            normalize_course({
                'subject': subject, 'catalog_number': str(number), 'title': 'Next course',
                'prerequisite_text': f'{subject} {number - 1} with a grade of B or better',
                'corequisite_text': 'Instructor consent',
            }),
        ]))
        db.execute('INSERT INTO roadmap_courses (major_code,course_id,term_order) VALUES (?,?,2)', ('CMPE', course_id))

    eligibility = check_eligibility(db, student.student_id, [course_id]).results[0]
    key = eligibility.additional_requirements[0].id
    confirmed = update_requirement_confirmation(db, student.student_id, course_id, key, True)
    assert confirmed.status == 'ineligible'
    assert confirmed.missing_course_ids == [prerequisite_id]
    assert confirmed.additional_requirements[0].confirmed

    put_course_record(db, student, prerequisite_id, CourseRecordInput(status='in_progress', grade=None, term=None))
    assert get_student_roadmap(db, student).suggestions[0].status == 'after_current'
    for grade, expected in [('C+', 'ineligible'), (None, 'unknown'), ('B', 'eligible')]:
        put_course_record(db, student, prerequisite_id, CourseRecordInput(status='completed', grade=grade, term=None))
        assert check_eligibility(db, student.student_id, [course_id]).results[0].status == expected
    assert get_student_roadmap(db, student).recommendations == [course_id]
    assert update_requirement_confirmation(db, student.student_id, course_id, key, False).status == 'unknown'
    assert get_student_roadmap(db, student).recommendations == []


def test_confirmations_api_is_scoped_reversible_and_invalidated_by_catalog_changes(tmp_path):
    path = tmp_path / 'test.db'
    with TestClient(create_app(path)) as first, TestClient(create_app(path)) as second:
        def signup(client, email):
            csrf = client.get('/api/auth/csrf').json()['csrf_token']
            result = client.post('/api/auth/signup', headers={'X-CSRF-Token': csrf}, json={
                'email': email, 'full_name': 'Test Student', 'password': 'example-password',
            }).raise_for_status().json()
            return {'X-CSRF-Token': result['csrf_token']}

        first_headers = signup(first, 'first@example.com')
        second_headers = signup(second, 'second@example.com')
        with closing(connect(path)) as db, db:
            upsert_catalog(db, IngestionDocument(terms=[], sections=[], courses=[normalize_course({
                'subject': 'MATH', 'catalog_number': '31', 'title': 'Calculus II',
                'prerequisite_text': 'AP Calculus AB score 3 to 5 or MATH 30 with a grade of C- or better',
            })]))
        body = {'course_ids': ['MATH-31']}
        initial = first.post('/api/me/eligibility', headers=first_headers, json=body).json()['results'][0]
        key = initial['additional_requirements'][0]['id']
        endpoint = f'/api/me/requirement-confirmations/MATH-31/{key}'
        assert first.put(endpoint, json={'confirmed': True}).status_code == 403
        assert first.put(endpoint, headers=first_headers, json={'confirmed': 'yes'}).status_code == 422
        result = first.put(endpoint, headers=first_headers, json={'confirmed': True}).raise_for_status().json()
        assert result['status'] == 'eligible'
        assert any(reason.startswith('Confirmed by you:') for reason in result['reasons'])
        assert first.put(endpoint, headers=first_headers, json={'confirmed': True}).status_code == 200
        other = second.post('/api/me/eligibility', headers=second_headers, json=body).json()['results'][0]
        assert other['status'] == 'unknown'
        assert other['additional_requirements'][0]['confirmed'] is False

        # The same confirmation survives app initialization but only matches unchanged catalog rules.
        init_db(path)
        persisted = first.post('/api/me/eligibility', headers=first_headers, json=body).json()['results'][0]
        assert persisted['additional_requirements'][0]['confirmed'] is True
        assert first.put(endpoint, headers=first_headers, json={'confirmed': False}).json()['status'] == 'unknown'
        first.put(endpoint, headers=first_headers, json={'confirmed': True}).raise_for_status()
        with closing(connect(path)) as db, db:
            upsert_catalog(db, IngestionDocument(terms=[], sections=[], courses=[normalize_course({
                'subject': 'MATH', 'catalog_number': '31', 'title': 'Calculus II',
                'prerequisite_text': 'AP Calculus AB score 4 to 5 or MATH 30 with a grade of C- or better',
            })]))
        changed = first.post('/api/me/eligibility', headers=first_headers, json=body).json()['results'][0]
        assert changed['status'] == 'unknown'
        assert not changed['additional_requirements'][0]['confirmed']
        assert first.put(endpoint, headers=first_headers, json={'confirmed': True}).status_code == 422


def test_old_calculus_waiver_rules_preserve_course_and_grade_checks(engineering_student):
    db, student = engineering_student
    from app.schemas import RequirementRule

    text = 'MATH 18A and MATH 18B, with a grade of C- or better in each to waive the exam.'
    with db:
        for number in ('18A', '18B', '30'):
            db.execute('INSERT INTO courses (id,subject,catalog_number,title) VALUES (?,?,?,?)',
                       (f'MATH-{number}', 'MATH', number, number))
        db.execute('UPDATE courses SET prerequisite_text=?,prerequisite_rule_json=? WHERE id=?',
                   (text, RequirementRule(kind='unknown', text=text).model_dump_json(), 'MATH-30'))
    checks = check_eligibility(db, student.student_id, ['MATH-30']).results[0].course_requirements
    assert [check.course_id for check in checks] == ['MATH-18A', 'MATH-18B']
    assert all(check.minimum_grade == 'C-' for check in checks)
    assert check_eligibility(db, student.student_id, ['MATH-30']).results[0].additional_requirements == []
    for course_id, grade in [('MATH-18A', 'A'), ('MATH-18B', 'D')]:
        put_course_record(db, student, course_id, CourseRecordInput(status='completed', grade=grade, term=None))
    assert check_eligibility(db, student.student_id, ['MATH-30']).results[0].status == 'ineligible'
    put_course_record(db, student, 'MATH-18B', CourseRecordInput(status='completed', grade='C-', term=None))
    assert check_eligibility(db, student.student_id, ['MATH-30']).results[0].status == 'eligible'


def test_placement_category_and_assessment_stay_one_confirmation(engineering_student):
    db, student = engineering_student
    from app.schemas import RequirementRule

    placement = 'Math Enrollment Category M-I or M-II and satisfactory score on the Precalculus Proficiency Assessment'
    text = (
        f'{placement}; MATH 19 with a grade of C- or better to waive the exam; or '
        'MATH 18A and MATH 18B, with a grade of C- or better in each to waive the exam.'
    )
    # Match the tree written by the older parser, including its split placement condition.
    old = RequirementRule(kind='all', text='Course requirements', children=[
        RequirementRule(kind='any', text=text, children=[
            parse_requirement_rule('Math Enrollment Category M-I'),
            parse_requirement_rule('M-II and satisfactory score on the Precalculus Proficiency Assessment'),
            RequirementRule(kind='unknown', text='MATH 19 with a grade of C- or better to waive the exam'),
        ]),
    ])
    with db:
        db.execute('INSERT INTO courses (id,subject,catalog_number,title,prerequisite_text,prerequisite_rule_json) '
                   'VALUES (?,?,?,?,?,?)', ('MATH-30', 'MATH', '30', 'Calculus I', text, old.model_dump_json()))
    eligibility = check_eligibility(db, student.student_id, ['MATH-30']).results[0]
    assert [requirement.text for requirement in eligibility.additional_requirements] == [placement]
    confirmed = update_requirement_confirmation(
        db, student.student_id, 'MATH-30', eligibility.additional_requirements[0].id, True,
    )
    assert confirmed.status == 'eligible'


def test_course_and_requirement_edits_save_atomically_and_preserve_omitted_confirmations(engineering_student):
    db, student = engineering_student
    with db:
        upsert_catalog(db, IngestionDocument(terms=[], sections=[], courses=[normalize_course({
            'subject': 'CHEM', 'catalog_number': '20', 'title': 'Chemistry',
            'prerequisite_text': 'Instructor consent',
        })]))
    key = check_eligibility(db, student.student_id, ['CHEM-20']).results[0].additional_requirements[0].id
    put_course_record(db, student, 'CHEM-20', CourseRecordInput(
        status='planned', grade=None, term=None, requirement_confirmations={key: True},
    ))
    assert check_eligibility(db, student.student_id, ['CHEM-20']).results[0].status == 'eligible'
    with pytest.raises(ApiProblem, match='requirement has changed'):
        put_course_record(db, student, 'CHEM-20', CourseRecordInput(
            status='completed', grade='A', term=None,
            requirement_confirmations={key: False, 'outdated-catalog-key': True},
        ))
    records = list_course_records(db, student).items
    assert [(record.course_id, record.status, record.grade) for record in records] == [('CHEM-20', 'planned', None)]
    assert check_eligibility(db, student.student_id, ['CHEM-20']).results[0].status == 'eligible'
    put_course_record(db, student, 'CHEM-20', CourseRecordInput(status='in_progress', grade=None, term=None))
    assert check_eligibility(db, student.student_id, ['CHEM-20']).results[0].additional_requirements[0].confirmed
    put_course_record(db, student, 'CHEM-20', CourseRecordInput(
        status='in_progress', grade=None, term=None, requirement_confirmations={key: False},
    ))
    assert check_eligibility(db, student.student_id, ['CHEM-20']).results[0].status == 'unknown'
