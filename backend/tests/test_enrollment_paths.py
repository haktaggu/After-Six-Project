from contextlib import closing

import pytest

from app.db.connection import connect, init_db
from app.features.ingest import normalize_course, upsert_catalog
from app.features.prerequisites import check_eligibility, update_requirement_confirmation
from app.features.profiles import put_course_record
from app.features.roadmap import get_student_roadmap
from app.jobs.refresh_enrollment_policies import parse_enrollment_policies, save_enrollment_policies
from app.schemas import CourseRecordInput, IngestionDocument


def department_html(number=32, previous=31, regular='B', supported='C-'):
    return f"""
    <main>
      <div><h2>Math {number}: Calculus</h2></div>
      <p>Students repeating Math {number} must take the corresponding workshop.</p>
      <ol>
        <li><strong>A grade of {regular} or higher in Math {previous} or Math {previous} &amp; {previous}W</strong> or an approved equivalent college course.</li>
        <li><strong>A score of 4 or higher on the AP Calculus BC exam.</strong></li>
      </ol>
      <div><h2>Math {number} with Math {number}W: Calculus with Workshop</h2></div>
      <ol>
        <li><strong>A grade of {supported} or higher in Math {previous} or Math {previous} &amp; {previous}W</strong></li>
        <li><strong>A score of 3 or higher on the AP Calculus BC exam.</strong></li>
      </ol>
    </main>
    """


def import_paths(db, number=32, previous=31, regular='B', supported='C-'):
    policies = parse_enrollment_policies(department_html(number, previous, regular, supported))
    with db:
        upsert_catalog(db, IngestionDocument(terms=[], sections=[], courses=[
            normalize_course({'subject': 'MATH', 'catalog_number': value, 'title': 'Mathematics'})
            for value in (str(number), str(previous), f'{number}W')
        ]))
        assert save_enrollment_policies(db, policies) == 1
        db.execute("INSERT INTO roadmap_courses (major_code,course_id,term_order) VALUES ('CMPE',?,3)", (f'MATH-{number}',))


@pytest.mark.parametrize(('grade', 'confirmed', 'expected'), [
    ('B', False, 'eligible'), ('B-', False, 'unknown'), ('C+', False, 'unknown'),
    ('C-', True, 'eligible'), ('C+', True, 'eligible'), ('D+', True, 'unknown'),
    ('F', True, 'unknown'), (None, True, 'unknown'),
])
def test_lower_grade_path_requires_workshop_and_keeps_the_grade_minimum(engineering_student, grade, confirmed, expected):
    db, student = engineering_student
    import_paths(db)
    put_course_record(db, student, 'MATH-31', CourseRecordInput(status='completed', grade=grade, term=None))
    initial = check_eligibility(db, student.student_id, ['MATH-32']).results[0]
    workshop = next(item for item in initial.additional_requirements if item.text.startswith('Enroll in MATH-32W'))
    if confirmed:
        update_requirement_confirmation(db, student.student_id, 'MATH-32', workshop.id, True)
    result = check_eligibility(db, student.student_id, ['MATH-32']).results[0]
    assert result.status == expected
    assert result.requirements.kind == 'any'
    assert result.source_url == 'https://www.sjsu.edu/math/calculus/'
    assert all(not item.confirmed for item in result.additional_requirements if 'AP Calculus' in item.text)
    roadmap = get_student_roadmap(db, student)
    assert bool(roadmap.recommendations) == (expected == 'eligible')


def test_course_and_exam_paths_are_independent_and_repeat_requires_a_workshop(engineering_student):
    db, student = engineering_student
    import_paths(db)
    result = check_eligibility(db, student.student_id, ['MATH-32']).results[0]
    high = next(item for item in result.additional_requirements if item.text.startswith('A score of 4'))
    low = next(item for item in result.additional_requirements if item.text.startswith('A score of 3'))
    workshop = next(item for item in result.additional_requirements if item.text.startswith('Enroll in'))
    assert update_requirement_confirmation(db, student.student_id, 'MATH-32', high.id, True).status == 'eligible'
    update_requirement_confirmation(db, student.student_id, 'MATH-32', high.id, False)
    assert update_requirement_confirmation(db, student.student_id, 'MATH-32', low.id, True).status == 'unknown'
    assert update_requirement_confirmation(db, student.student_id, 'MATH-32', workshop.id, True).status == 'eligible'
    update_requirement_confirmation(db, student.student_id, 'MATH-32', workshop.id, False)
    update_requirement_confirmation(db, student.student_id, 'MATH-32', high.id, True)
    put_course_record(db, student, 'MATH-32', CourseRecordInput(status='completed', grade='F', term=None))
    assert check_eligibility(db, student.student_id, ['MATH-32']).results[0].status == 'unknown'
    assert update_requirement_confirmation(db, student.student_id, 'MATH-32', workshop.id, True).status == 'eligible'


def test_workshop_records_match_the_target_term(engineering_student):
    db, student = engineering_student
    import_paths(db)
    with db:
        db.executemany('INSERT INTO terms (id,name) VALUES (?,?)', [('fall-2026', 'Fall 2026'), ('spring-2027', 'Spring 2027')])
    put_course_record(db, student, 'MATH-31', CourseRecordInput(status='completed', grade='C+', term=None))
    put_course_record(db, student, 'MATH-32', CourseRecordInput(status='planned', grade=None, term='spring-2027'))
    for term, expected in [('fall-2026', 'unknown'), ('spring-2027', 'eligible'), (None, 'unknown')]:
        put_course_record(db, student, 'MATH-32W', CourseRecordInput(status='planned', grade=None, term=term))
        assert check_eligibility(db, student.student_id, ['MATH-32']).results[0].status == expected


def test_thresholds_and_course_numbers_come_from_department_content(engineering_student):
    db, student = engineering_student
    import_paths(db, number=83, previous=82, regular='A', supported='B-')
    put_course_record(db, student, 'MATH-82', CourseRecordInput(status='completed', grade='C+', term=None))
    result = check_eligibility(db, student.student_id, ['MATH-83']).results[0]
    workshop = next(item for item in result.additional_requirements if item.text.startswith('Enroll in MATH-83W'))
    assert update_requirement_confirmation(db, student.student_id, 'MATH-83', workshop.id, True).status == 'unknown'
    put_course_record(db, student, 'MATH-82', CourseRecordInput(status='completed', grade='B-', term=None))
    assert check_eligibility(db, student.student_id, ['MATH-83']).results[0].status == 'eligible'


def test_department_parser_rejects_incomplete_sources_before_writing():
    with pytest.raises(ValueError, match='no complete enrollment paths'):
        parse_enrollment_policies('<h2>Page unavailable</h2>')
    with pytest.raises(ValueError, match='missing the workshop paths'):
        parse_enrollment_policies(department_html().split('<div><h2>Math 32 with')[0])
