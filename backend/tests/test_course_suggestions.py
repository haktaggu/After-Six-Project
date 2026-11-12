from app.features.ingest import normalize_course, upsert_catalog
from app.features.profiles import put_course_record
from app.features.roadmap import get_student_roadmap
from app.schemas import CourseRecordInput, IngestionDocument


def add_degree(db, student, major, requirements, required, optional=(), target=5):
    catalog = []
    for course_id, prerequisite in requirements.items():
        subject, number = course_id.split('-')
        catalog.append(normalize_course({
            'subject': subject, 'catalog_number': number, 'title': f'Course {course_id}',
            'prerequisite_text': prerequisite, 'confirmed_empty': prerequisite is None,
            'catalog_url': 'https://catalog.sjsu.edu/preview_course_nopop.php',
        }))
    with db:
        upsert_catalog(db, IngestionDocument(terms=[], courses=catalog, sections=[]))
        db.execute('INSERT INTO major_roadmaps (major_code,title) VALUES (?,?)', (major, major))
        db.execute('UPDATE student_profiles SET major=?,recommendation_limit=? WHERE student_id=?',
                   (major, target, student.student_id))
        db.executemany(
            'INSERT INTO roadmap_courses (major_code,course_id,term_order,is_required) VALUES (?,?,?,?)',
            [(major, course_id, index, int(course_id in required))
             for index, course_id in enumerate((*required, *optional), start=1)],
        )


def save(db, student, course_id, grade=None):
    status = 'completed' if grade else 'in_progress'
    put_course_record(db, student, course_id, CourseRecordInput(status=status, grade=grade, term=None))


def statuses(roadmap):
    return [(item.course_id, item.status) for item in roadmap.suggestions]


def test_early_degree_fills_the_target_with_linked_and_optional_courses(engineering_student):
    db, student = engineering_student
    add_degree(
        db, student, 'CHEM',
        {
            'CHEM-10': None, 'CHEM-20': 'CHEM 10', 'CHEM-30': 'Instructor consent',
            'CHEM-40': 'MATH 20 or PHYS 20', 'CHEM-50': 'CHEM 20 and CHEM 40',
            'CHEM-60': None, 'MATH-20': None, 'PHYS-20': 'PHYS 10', 'BIOL-70': None,
        },
        required=('CHEM-10', 'CHEM-20', 'CHEM-30', 'CHEM-40', 'CHEM-50'),
        optional=('CHEM-60',),
    )
    roadmap = get_student_roadmap(db, student)
    assert roadmap.recommendations == ['CHEM-10']
    assert roadmap.recommendation_limit == 5
    assert statuses(roadmap) == [
        ('CHEM-10', 'ready'), ('CHEM-30', 'needs_review'), ('MATH-20', 'ready'),
        ('CHEM-60', 'ready'), ('CHEM-20', 'requirements_remaining'),
    ]
    assert 'CHEM-40' in roadmap.suggestions[2].reason


def test_mid_degree_uses_live_grades_and_keeps_an_alternative_a_choice(engineering_student):
    db, student = engineering_student
    add_degree(
        db, student, 'HIST',
        {
            'HIST-11': None, 'HIST-21': 'HIST 11',
            'HIST-31': 'HIST 21 with a grade of B or better and either PHIL 10 or PSYC 10',
            'HIST-41': 'HIST 21 and ART 10', 'HIST-51': 'HIST 21 and instructor consent',
            'HIST-61': None, 'PHIL-10': None, 'PSYC-10': None,
        },
        required=('HIST-11', 'HIST-21', 'HIST-31', 'HIST-41', 'HIST-51', 'HIST-61'),
        target=4,
    )
    save(db, student, 'HIST-11', 'A')
    for course_id in ('HIST-21', 'PHIL-10', 'PSYC-10'):
        save(db, student, course_id)
    roadmap = get_student_roadmap(db, student)
    assert statuses(roadmap) == [
        ('HIST-61', 'ready'), ('HIST-31', 'after_current'),
        ('HIST-41', 'requirements_remaining'), ('HIST-51', 'requirements_remaining'),
    ]
    assert 'HIST-21' in roadmap.suggestions[1].reason
    assert 'PHIL-10' in roadmap.suggestions[1].reason
    assert 'PSYC-10' not in roadmap.suggestions[1].reason

    save(db, student, 'PHIL-10', 'A')
    save(db, student, 'HIST-21', 'C')
    assert dict(statuses(get_student_roadmap(db, student)))['HIST-31'] == 'requirements_remaining'
    save(db, student, 'HIST-21', 'B')
    roadmap = get_student_roadmap(db, student)
    assert statuses(roadmap) == [
        ('HIST-31', 'ready'), ('HIST-61', 'ready'),
        ('HIST-51', 'needs_review'), ('HIST-41', 'requirements_remaining'),
    ]
    assert 'PSYC-10' not in dict(statuses(roadmap))


def test_late_degree_reports_only_remaining_degree_related_options(engineering_student):
    db, student = engineering_student
    add_degree(
        db, student, 'ART',
        {
            'ART-10': None, 'ART-20': 'ART 10', 'ART-30': 'ART 20', 'ART-40': 'ART 30 and MUSC 15',
            'MUSC-15': None, 'MUSC-25': None,
        },
        required=('ART-10', 'ART-20', 'ART-30', 'ART-40'),
    )
    for course_id in ('ART-10', 'ART-20', 'ART-30'):
        save(db, student, course_id, 'A')
    assert statuses(get_student_roadmap(db, student)) == [
        ('MUSC-15', 'ready'), ('ART-40', 'requirements_remaining'),
    ]

    save(db, student, 'MUSC-15', 'B')
    assert statuses(get_student_roadmap(db, student)) == [('ART-40', 'ready')]
    save(db, student, 'ART-40', 'A')
    assert statuses(get_student_roadmap(db, student)) == []
