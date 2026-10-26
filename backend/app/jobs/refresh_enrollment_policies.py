from contextlib import closing
from pathlib import Path
import re

from bs4 import BeautifulSoup

from app.db.connection import connect
from app.features.ingest import check_source, fetch_source
from app.features.prerequisites import parse_course_expression
from app.schemas import Database, EnrollmentPolicy, RequirementRule

ENROLLMENT_SOURCE = 'https://www.sjsu.edu/math/calculus/'


def parse_department_condition(text: str) -> RequirementRule:
    text = ' '.join(text.split()).rstrip('. ')
    grade = re.match(r'A grade of ([A-DF][+-]?) or (?:higher|better) in (?:both )?(.+)', text, re.I)
    if not grade:
        return RequirementRule(kind='unknown', text=text)
    courses = re.match(r'Math\s+\d+[A-Z]*(?:\s+(?:and|or|&)\s+(?:Math\s+)?\d+[A-Z]*)*', grade[2], re.I)
    if not courses:
        return RequirementRule(kind='unknown', text=text)
    expression = courses.group().replace('&', 'and')
    expression = re.sub(r'\b(and|or)\s+(\d+[A-Z]*)\b', r'\1 Math \2', expression, flags=re.I)
    parsed = parse_course_expression(expression, grade[1].upper())
    if parsed is None:
        return RequirementRule(kind='unknown', text=text)
    # A or (A and a previous workshop) includes the first coursework route on its own.
    if parsed.kind == 'any':
        singles = {(child.course_id, child.minimum_grade) for child in parsed.children if child.kind == 'course'}
        parsed.children = [child for child in parsed.children if child.kind != 'all' or not any(
            (part.course_id, part.minimum_grade) in singles for part in child.children if part.kind == 'course'
        )]
        if len(parsed.children) == 1:
            parsed = parsed.children[0]
    return parsed


def parse_enrollment_policies(html: str, source_url: str = ENROLLMENT_SOURCE) -> list[EnrollmentPolicy]:
    check_source(source_url)
    soup = BeautifulSoup(html, 'html.parser')
    sections = {}
    for heading in soup.find_all('h2'):
        match = re.match(r'Math (\d+[A-Z]*)(?: with Math (\d+[A-Z]*))?(?:\s*:|\s+)', heading.get_text(' ', strip=True), re.I)
        if not match:
            continue
        course_id = f'MATH-{match[1].upper()}'
        workshop = f'MATH-{match[2].upper()}' if match[2] else None
        conditions = []
        for tag in heading.find_all_next():
            if tag.name == 'h2':
                break
            if tag.name == 'ol':
                for item in tag.find_all('li', recursive=False):
                    primary = item.find('strong')
                    conditions.append(parse_department_condition((primary or item).get_text(' ', strip=True)))
                break
        if conditions:
            sections.setdefault(course_id, {})[workshop] = RequirementRule(kind='any', text='Choose an enrollment path', children=conditions)
    policies = []
    for course_id, options in sections.items():
        if None not in options:
            continue
        regular = options[None]
        branches = []
        workshops = [workshop for workshop in options if workshop]
        if not workshops:
            raise ValueError(f'Department enrollment source is missing the workshop paths for {course_id}')
        for workshop in workshops:
            branches.append(RequirementRule(kind='all', text=f'Coursework or exam placement without {workshop}', children=[
                regular,
                RequirementRule(kind='first_attempt', text='First enrollment in this course', course_id=course_id),
            ]))
            branches.append(RequirementRule(kind='all', text=f'Coursework or exam placement with {workshop}', children=[
                options[workshop],
                RequirementRule(kind='course', text=f'Enroll in {workshop} in the same term as {course_id}',
                                course_id=workshop, concurrent=True, value=course_id),
            ]))
        policies.append(EnrollmentPolicy(course_id=course_id, source_url=source_url,
                                         rule=RequirementRule(kind='any', text='Choose one enrollment path', children=branches)))
    if not policies:
        raise ValueError('Department source contains no complete enrollment paths')
    return policies


def save_enrollment_policies(db: Database, policies: list[EnrollmentPolicy]) -> int:
    count = 0
    for policy in policies:
        if not db.execute('SELECT 1 FROM courses WHERE id=?', (policy.course_id,)).fetchone():
            continue
        db.execute('INSERT INTO course_enrollment_policies (course_id,source_url,rule_json) VALUES (?,?,?) '
                   'ON CONFLICT(course_id) DO UPDATE SET source_url=excluded.source_url,rule_json=excluded.rule_json',
                   (policy.course_id, policy.source_url, policy.rule.model_dump_json()))
        count += 1
    return count


def refresh_enrollment_policies(path: Path) -> int:
    policies = parse_enrollment_policies(fetch_source(ENROLLMENT_SOURCE))
    with closing(connect(path)) as db, db:
        db.execute('BEGIN IMMEDIATE')
        return save_enrollment_policies(db, policies)
