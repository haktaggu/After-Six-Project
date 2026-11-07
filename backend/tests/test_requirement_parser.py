import pytest

from app.features.ingest import parse_catalog, upsert_catalog
from app.features.prerequisites import (
    assess_course, check_eligibility, confirmable_requirements, course_requirement_checks, evaluate_rule,
    get_course_requirement, parse_requirement_rule, requirement_id,
)
from app.features.profiles import put_course_record
from app.features.roadmap import get_student_roadmap
from app.schemas import CourseRecord, CourseRecordInput, RequirementRule, StudentContext


PHYSICS_REQUIREMENTS = (
    'Writing Enrollment Category I / II / III or GE Area A2 completed (grade of C- or better) or '
    'ENGL 1AF (grade of CR); AND, 3 or better on AP Calculus Test, or C- or better in '
    'MATH 30 / 30X. Allowed declared majors: College of Science or Engineering.'
)
PHYSICS_HTML = f"""
<div class="block_content">
<h1 id="course_preview_title">PHYS 50 - General Physics I: Mechanics</h1>
<p>4 unit(s)</p><p><strong>Prerequisite(s):</strong> {PHYSICS_REQUIREMENTS}</p>
</div>
"""
ENGINEERING_MAJOR = 'Allowed declared majors: College of Science or Engineering'
WRITING_PLACEMENT = 'Writing Enrollment Category I / II / III'
AP_CALCULUS = '3 or better on AP Calculus Test'


def context(records=(), confirmed=None):
    return StudentContext(
        student_id='test', major_code='CMPE', standing='junior', gpa=3.5, earned_units=75,
        course_records=[CourseRecord(course_id=course, status='completed', grade=grade, term=None)
                        for course, grade in records],
        confirmed_requirements={'PHYS-50': confirmed or []},
    )


def test_physics_catalog_preserves_score_conditions_and_extracts_course_alternatives():
    imported = parse_catalog(PHYSICS_HTML, 'https://catalog.sjsu.edu/preview_course.php?coid=123').courses[0]
    assert imported.course.prerequisite_text == PHYSICS_REQUIREMENTS
    requirements = assess_course('PHYS-50', imported.prerequisite_rule, context())
    assert [item.text for item in requirements.additional_requirements] == [
        WRITING_PLACEMENT,
        'GE Area A2 completed (grade of C- or better)',
        AP_CALCULUS,
        ENGINEERING_MAJOR,
    ]
    assert [(item.course_id, item.minimum_grade) for item in requirements.course_requirements] == [
        ('ENGL-1AF', 'CR'), ('MATH-30', 'C-'), ('MATH-30X', 'C-'),
    ]
    assert all(item.alternative for item in requirements.course_requirements)


@pytest.mark.parametrize(('records', 'confirmed_texts', 'expected'), [
    ([('ENGL-1AF', 'CR'), ('MATH-30X', 'C-')], [ENGINEERING_MAJOR], 'eligible'),
    ([('ENGL-1AF', 'CR'), ('MATH-30', 'D')], [ENGINEERING_MAJOR], 'unknown'),
    ([('ENGL-1AF', 'NC'), ('MATH-30', 'A')], [ENGINEERING_MAJOR], 'unknown'),
    ([('ENGL-1AF', 'CR'), ('MATH-30', 'A')], [], 'unknown'),
    ([], [WRITING_PLACEMENT, AP_CALCULUS, ENGINEERING_MAJOR], 'eligible'),
])
def test_physics_requires_writing_and_math_and_the_major_condition(records, confirmed_texts, expected):
    rule = parse_requirement_rule(PHYSICS_REQUIREMENTS)
    clauses = {clause.text: key for key, clause in confirmable_requirements(rule).items()}
    student = context(records, [clauses[text] for text in confirmed_texts])
    assert assess_course('PHYS-50', rule, student).status == expected


@pytest.mark.parametrize(('text', 'expected'), [
    ('CHEM 10 / 10H with a grade of B or better', [('CHEM-10', 'B'), ('CHEM-10H', 'B')]),
    ('ENGL 1A or ENGL 1AS with a C- or better', [('ENGL-1A', 'C-'), ('ENGL-1AS', 'C-')]),
    ('PHYS 50 and MATH 31, both with grades of “C-” or better', [('PHYS-50', 'C-'), ('MATH-31', 'C-')]),
    ('CMPE 70, CMPE 110 and CMPE 127 with grade of C- or better',
     [('CMPE-70', 'C-'), ('CMPE-110', 'C-'), ('CMPE-127', 'C-')]),
    ('MATH 19 with a grade of “C-” or better to waive the exam', [('MATH-19', 'C-')]),
])
def test_shared_grades_and_course_shorthand_are_not_manual_confirmations(text, expected):
    rule = parse_requirement_rule(text)
    assert not confirmable_requirements(rule)
    assert [(check.course_id, check.minimum_grade) for check in course_requirement_checks(rule, context())] == expected


@pytest.mark.parametrize('text', [
    'Score of 4 to 5 on the AP Calculus BC Exam',
    'Math Enrollment Category M-I, M-II, or M-III',
    'Allowed Declared Majors: Computer Science, Data Science, or Software Engineering',
    'Completion of, or co-registration in, 100W is strongly recommended',
])
def test_unsupported_policy_is_preserved_as_one_complete_statement(text):
    rule = parse_requirement_rule(text)
    assert [clause.text for clause in confirmable_requirements(rule).values()] == [text]


@pytest.mark.parametrize(('records', 'expected'), [
    ([('MATH-39', 'A'), ('MATH-33A', 'A')], 'ineligible'),
    ([('EE-97', 'A'), ('EE-98', 'A'), ('MATH-33LA', 'C-')], 'eligible'),
    ([('EE-97', 'A'), ('EE-98', 'A'), ('MATH-39', 'A')], 'ineligible'),
    ([('EE-97', 'A'), ('EE-98', 'A'), ('MATH-39', 'B'), ('MATH-33A', 'D')], 'ineligible'),
    ([('EE-97', 'A'), ('EE-98', 'A'), ('MATH-39', 'B'), ('MATH-33A', 'C-')], 'eligible'),
])
def test_course_list_and_plus_alternative_keep_all_mandatory_courses(records, expected):
    rule = parse_requirement_rule('EE 97, EE 98, MATH 33LA or MATH 39 + MATH 33A, all with a grade of C- or better')
    assert evaluate_rule(rule, context(records)) == expected


def test_existing_imports_reparse_original_source_and_reject_old_fragment_confirmations(engineering_student):
    db, student = engineering_student
    document = parse_catalog(PHYSICS_HTML, 'https://catalog.sjsu.edu/preview_course.php?coid=123')
    fragment = RequirementRule(kind='unknown', text='3')
    old_rule = RequirementRule(kind='all', text='Course requirements', children=[fragment])
    with db:
        upsert_catalog(db, document)
        db.execute('UPDATE courses SET prerequisite_rule_json=? WHERE id=?', (old_rule.model_dump_json(), 'PHYS-50'))
        db.execute('INSERT INTO student_requirement_confirmations VALUES (?,?,?)',
                   (student.student_id, 'PHYS-50', requirement_id(fragment)))
    result = check_eligibility(db, student.student_id, ['PHYS-50']).results[0]
    assert len(result.additional_requirements) == 4
    assert all(not requirement.confirmed for requirement in result.additional_requirements)
    assert result.course_requirements
    assert result.status == 'unknown'
    assert get_course_requirement(db, 'PHYS-50') != old_rule


def test_physics_recommendation_updates_from_history_and_complete_conditions(engineering_student):
    db, student = engineering_student
    document = parse_catalog(PHYSICS_HTML, 'https://catalog.sjsu.edu/preview_course.php?coid=123')
    with db:
        upsert_catalog(db, document)
        db.execute("INSERT INTO courses (id,subject,catalog_number,title) VALUES ('MATH-30','MATH','30','Calculus')")
        db.execute("INSERT INTO roadmap_courses (major_code,course_id,term_order) VALUES ('CMPE','PHYS-50',2)")
    requirements = check_eligibility(db, student.student_id, ['PHYS-50']).results[0].additional_requirements
    confirmations = {item.id: True for item in requirements if item.text.startswith(('Writing Enrollment', 'Allowed declared'))}
    put_course_record(db, student, 'PHYS-50', CourseRecordInput(
        status='planned', grade=None, term=None, requirement_confirmations=confirmations,
    ))
    assert get_student_roadmap(db, student).recommendations == []
    put_course_record(db, student, 'MATH-30', CourseRecordInput(status='completed', grade='C-', term=None))
    assert get_student_roadmap(db, student).recommendations == ['PHYS-50']
    put_course_record(db, student, 'MATH-30', CourseRecordInput(status='completed', grade='D', term=None))
    assert get_student_roadmap(db, student).recommendations == []
