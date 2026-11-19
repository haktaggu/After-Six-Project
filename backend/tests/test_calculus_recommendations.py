import pytest

from app.features.ingest import normalize_course, upsert_catalog
from app.features.profiles import put_course_record
from app.features.roadmap import get_student_roadmap
from app.schemas import CourseRecordInput, IngestionDocument


@pytest.mark.parametrize(('number', 'prerequisite_text', 'corequisite_text', 'cutoff', 'qualifying_grade'), [
    (31, 'AP Calculus AB score 3 to 5, AP Calculus BC/AB Subscore 3-5, or MATH 30 with a grade of C- or better.',
     'MATH 31W for students with AP Calculus AB score of 3, AP Calculus BC/AB Subscore of 3, or '
     'MATH 30 with a grade of B- or lower, or students who are repeating MATH 31.', 'B-', 'B'),
    (32, 'Score of 4 to 5 on the AP Calculus BC Exam; or MATH 31 with a grade of B or better.',
     'MATH 32W for students with a score of 3 on the AP Calculus BC Exam; or '
     'MATH 31 with a grade of B- or lower; or students who are repeating MATH 32.', 'B-', 'B'),
    (31, 'MATH 30 with a grade of C- or better.',
     'MATH 31W for students with AP Calculus AB score of 3, or MATH 30 with a grade of C+ or lower, '
     'or students who are repeating MATH 31.', 'C+', 'B-'),
])
def test_roadmap_uses_recorded_grade_to_evaluate_calculus_workshop(
    engineering_student, number, prerequisite_text, corequisite_text, cutoff, qualifying_grade,
):
    db, student = engineering_student
    course = normalize_course({
        'subject': 'MATH', 'catalog_number': str(number), 'title': 'Calculus',
        'prerequisite_text': prerequisite_text, 'corequisite_text': corequisite_text,
    })
    prerequisite = normalize_course({
        'subject': 'MATH', 'catalog_number': str(number - 1), 'title': 'Prerequisite',
    })
    with db:
        upsert_catalog(db, IngestionDocument(terms=[], courses=[course, prerequisite], sections=[]))
        db.execute('INSERT INTO roadmap_courses (major_code, course_id, term_order, is_required) VALUES (?, ?, ?, ?)',
                   ('CMPE', course.course.id, 2, 1))

    for grade, expected in [(None, []), (cutoff, []), (qualifying_grade, [course.course.id])]:
        put_course_record(db, student, prerequisite.course.id, CourseRecordInput(status='completed', grade=grade, term=None))
        roadmap = get_student_roadmap(db, student)
        assert roadmap.recommendations == expected

    put_course_record(db, student, course.course.id, CourseRecordInput(status='completed', grade='F', term=None))
    roadmap = get_student_roadmap(db, student)
    assert roadmap.recommendations == []
    assert roadmap.courses[0].eligibility.status == 'unknown'
