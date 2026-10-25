from __future__ import annotations

import math
import operator
import re

from app.errors import ApiProblem
from app.schemas import CourseRecord, Database, Eligibility, EligibilityResponse, EligibilityStatus, Grade, RequirementRule, StudentContext

LETTERS = ['F', 'D-', 'D', 'D+', 'C-', 'C', 'C+', 'B-', 'B', 'B+', 'A-', 'A', 'A+']
STANDINGS = ['freshman', 'sophomore', 'junior', 'senior']
OPS = {'gte': operator.ge, 'gt': operator.gt, 'lte': operator.le, 'lt': operator.lt, 'eq': operator.eq, 'ne': operator.ne}
MAJORS = {'computer engineering': 'CMPE', 'cmpe': 'CMPE', 'software engineering': 'SE', 'se': 'SE'}


def parse_requirement_rule(text: str | None, confirmed_empty: bool = False) -> RequirementRule:
    if not text or not text.strip():
        return RequirementRule(kind='all' if confirmed_empty else 'unknown', text=text or ('No enrollment requirements listed in captured catalog' if confirmed_empty else 'Requirements not verified'))
    src = re.sub(r'\s+', ' ', text.replace('\u200b', '')).strip().rstrip('.; ')
    src = src.translate(str.maketrans({'“': '"', '”': '"', '‘': "'", '’': "'", '−': '-', '–': '-', '‑': '-'}))
    if src.lower() in ('none', 'no prerequisites', 'no prerequisites required'):
        return RequirementRule(kind='all', text=src)
    src = re.sub(r'^(?:prerequisites?|corequisites?|restrictions?)\s*:\s*', '', src, flags=re.I)
    sentences = re.split(r'\.(?:\s+|$)|;\s*', src)
    if len(sentences) > 1:
        return RequirementRule(kind='all', text=src, children=[parse_requirement_rule(p) for p in sentences if p.strip()])
    while src.startswith('(') and src.endswith(')'):
        depth = 0
        for i, ch in enumerate(src):
            depth += (ch == '(') - (ch == ')')
            if depth == 0 and i != len(src) - 1:
                break
        else:
            src = src[1:-1].strip()
            continue
        break
    low = src.lower()
    if 'major' in low and not re.search(r'\bgpa\b|grade point average|\bunits?\b|\bstanding\b', low) and not re.search(r'\b[A-Z][A-Z0-9]{1,5}[ -]+\d', src):
        excluded = bool(re.search(r'\bnot\b|excluding|except', low))
        name = re.sub(r'allowed declared majors?:|allowed majors?:|\b(?:open to|restricted to|majors?|only|students|in|not|excluding|except)\b', '', low).strip(' ,:')
        names = re.split(r'\s+or\s+|,', name)
        children = []
        for name in names:
            name = re.sub(r'\s+', ' ', name).strip()
            code = MAJORS.get(name)
            children.append(RequirementRule(kind='major', text=name, value=code, operator='ne' if excluded else 'eq') if code else RequirementRule(kind='unknown', text=f'Major restriction: {name}'))
        return children[0] if len(children) == 1 else RequirementRule(kind='all' if excluded else 'any', text=src, children=children)
    if 'standing' in low or re.search(r'upper.division', low):
        ranks = [s for s in [*STANDINGS, 'graduate'] if re.search(r'\b' + s + r'\b', low)]
        if not ranks and re.fullmatch(r'(?:at least )?upper.division(?: standing)?', low):
            ranks = ['junior']
        rest = re.sub(r'freshman|sophomore|junior|senior|graduate|upper.division|class standing|standing|only|or above|or higher|or|and|at least|at most|no more than|greater than|more than|above|less than|below|exactly|equal to|not|[<>=!,\s]', '', low)
        if ranks and not rest:
            exact = len(ranks) > 1 or 'only' in low or ranks[0] == 'graduate'
            op = 'eq' if exact else 'gte'
            for pattern, value in ((r'no more than|at most|<=', 'lte'), (r'less than|below|<', 'lt'), (r'greater than|more than|above|>', 'gt'), (r'not|!=', 'ne'), (r'exactly|equal to|(?<![<>!])=', 'eq')):
                if re.search(pattern, low):
                    op = value
                    break
            if 'or above' in low or 'or higher' in low or 'at least' in low or '>=' in low:
                op = 'gte'
            if '<=' in low:
                op = 'lte'
            children = [RequirementRule(kind='standing', text=src, value=r, operator=op) for r in ranks]
            return children[0] if len(children) == 1 else RequirementRule(kind='any', text=src, children=children)
    shared = re.fullmatch(r'(.+?)\s*\((?:(?:all|both) )?with (?:a )?grades? of ["\']?([A-DF][+-]?)["\']? or (?:better|higher)\)', src, re.I)
    if shared:
        tree = parse_requirement_rule(shared[1])
        def apply_grade(node: RequirementRule) -> None:
            if node.kind == 'course':
                node.minimum_grade = shared[2].upper()
            for child in node.children:
                apply_grade(child)
        apply_grade(tree)
        return tree
    either = re.fullmatch(r'(.+?),?\s+and either\s+(.+)', src, re.I)
    if either:
        return RequirementRule(kind='all', text=src, children=[parse_requirement_rule(either[1].rstrip(' ,')), parse_requirement_rule(either[2])])
    normalized = re.sub(r'\(?\s*(?:with (?:a )?)?(?:minimum )?grade (?:of )?["\']?([A-DF][+-]?)["\']?\s+or (?:better|higher)\s*\)?', r' grade >= \1', src, flags=re.I)
    normalized = re.sub(r'\(?["\']?([A-DF][+-]?)["\']?\s+or (?:better|higher)\)?', r' grade >= \1', normalized, flags=re.I)
    normalized = re.sub(r'\b(?:either|both)\s+', '', normalized, flags=re.I)
    for pattern, kind in ((r'\bor\b', 'any'), (r'\band\b|,(?=\s*[A-Z][A-Z0-9]{1,5}\s+\d)', 'all')):
        depth = 0
        start = 0
        parts = []
        for match in re.finditer(r'\(|\)|' + pattern, normalized, re.I):
            token = match.group()
            if token == '(':
                depth += 1
            elif token == ')':
                depth -= 1
            elif depth == 0:
                parts.append(normalized[start:match.start()].strip(' ,'))
                start = match.end()
        if parts:
            parts.append(normalized[start:].strip(' ,'))
            return RequirementRule(kind=kind, text=src, children=[parse_requirement_rule(p) for p in parts])
    low = normalized.lower()
    if any(word in low for word in ('permission', 'consent', 'placement', 'sjsu gpa', 'major gpa', 'residency')):
        return RequirementRule(kind='unknown', text=src)
    course = re.fullmatch(r'([A-Z][A-Z0-9]{1,5})[ -]*0*(\d+[A-Z]*)\s*(?:(?:\(?\s*(?:with (?:a )?)?(?:minimum )?grade\s*(?:of |>=\s*)?["\']?([A-DF][+-]?)["\']?\s*\)?)?)\s*(?:(may be taken concurrently|concurrent enrollment))?', normalized, re.I)
    if course:
        return RequirementRule(kind='course', text=src, course_id=f'{course[1].upper()}-{course[2].upper()}', minimum_grade=course[3].upper() if course[3] else None, concurrent=bool(course[4]))
    if re.search(r'\bgpa\b|grade point average', low):
        kind = 'gpa'
        if re.search(r'major|sjsu|department|subject', low):
            return RequirementRule(kind='unknown', text=src)
    elif re.search(r'\bunits?\b', low):
        kind = 'units'
        if re.search(r'\b(?:CMPE|CS|MATH|at SJSU|residen|upper.division|major|subject|transfer)', normalized, re.I):
            return RequirementRule(kind='unknown', text=src)
    else:
        return RequirementRule(kind='unknown', text=src)
    num = re.search(r'\d+(?:\.\d+)?', low)
    if not num:
        return RequirementRule(kind='unknown', text=src)
    op = 'gte'
    for pattern, value in ((r'no more than|at most|<=|maximum', 'lte'), (r'less than|below|<', 'lt'), (r'greater than|more than|above|>', 'gt'), (r'not equal|!=', 'ne'), (r'exactly|equal to|(?<![<>!])=', 'eq')):
        if re.search(pattern, low):
            op = value
            break
    if '>=' in low or 'at least' in low or 'minimum' in low:
        op = 'gte'
    if '<=' in low:
        op = 'lte'
    return RequirementRule(kind=kind, text=src, value=float(num.group()), operator=op)


def build_student_context(db: Database, student_id: str) -> StudentContext:
    row = db.execute('SELECT major,standing,gpa,earned_units FROM student_profiles WHERE student_id=?', (student_id,)).fetchone()
    if row is None:
        raise ApiProblem(404, 'NOT_FOUND', 'Profile not found')
    rows = db.execute('SELECT course_id,status,grade,term FROM student_course_attempts WHERE student_id=?', (student_id,))
    records = [CourseRecord(**dict(zip(('course_id', 'status', 'grade', 'term'), r))) for r in rows]
    return StudentContext(student_id=student_id, major_code=row[0], standing=row[1], gpa=row[2], earned_units=row[3], course_records=records)


def evaluate_grade(grade: Grade | None, minimum_grade: str | None) -> EligibilityStatus:
    if grade in ('F', 'NC', 'WU', 'IC'):
        return 'ineligible'
    if grade is None or grade in ('W', 'I', 'RP', 'RD', 'AU'):
        return 'unknown'
    if minimum_grade is not None and minimum_grade not in LETTERS:
        return 'unknown'
    if grade == 'CR':
        return 'unknown' if minimum_grade else 'eligible'
    return 'eligible' if LETTERS.index(grade) >= LETTERS.index(minimum_grade or 'D-') else 'ineligible'


def assess_rule(rule: RequirementRule, student: StudentContext) -> tuple[EligibilityStatus, list[str], list[str]]:
    if rule.kind in ('all', 'any'):
        if not rule.children:
            return ('eligible', [], []) if rule.kind == 'all' else ('unknown', [rule.text], [])
        parts = [assess_rule(child, student) for child in rule.children]
        states = [p[0] for p in parts]
        if rule.kind == 'all':
            status = 'ineligible' if 'ineligible' in states else 'unknown' if 'unknown' in states else 'eligible'
        else:
            status = 'eligible' if 'eligible' in states else 'unknown' if 'unknown' in states else 'ineligible'
        relevant = [p for p in parts if p[0] == 'eligible'] if rule.kind == 'any' and status == 'eligible' else parts
        return status, [r for p in relevant for r in p[1]], list(dict.fromkeys(c for p in relevant for c in p[2]))
    if rule.kind == 'course':
        record = next((r for r in student.course_records if r.course_id == rule.course_id), None)
        actual = f'{record.status}, grade {record.grade or "unknown"}' if record else 'no course record'
        reason = f'{rule.course_id}: requires completed credit' + (f' with grade {rule.minimum_grade} or higher' if rule.minimum_grade else '') + f'; actual: {actual}.'
        if rule.concurrent or not rule.course_id:
            return 'unknown', [reason + ' Concurrent enrollment requires confirmation.'], []
        status = evaluate_grade(record.grade, rule.minimum_grade) if record and record.status == 'completed' else 'ineligible'
        return status, [reason], [rule.course_id] if status == 'ineligible' else []
    if rule.kind in ('gpa', 'units', 'standing', 'major'):
        actual = {'gpa': student.gpa, 'units': student.earned_units, 'standing': student.standing, 'major': student.major_code}[rule.kind]
        reason = f'{rule.text}: requires {rule.kind} {rule.operator} {rule.value}; actual: {actual if actual is not None else "unknown"}.'
        if actual is None or actual == 'unspecified':
            return 'unknown', [reason], []
        required = rule.value
        if rule.kind in ('gpa', 'units'):
            if not isinstance(required, (int, float)) or not math.isfinite(required) or required < 0 or rule.kind == 'gpa' and required > 4:
                return 'unknown', [reason], []
        elif rule.kind == 'major':
            if rule.operator not in ('eq', 'ne') or not required:
                return 'unknown', [reason], []
        elif actual in STANDINGS and required in STANDINGS:
            actual, required = STANDINGS.index(actual), STANDINGS.index(required)
        elif rule.operator not in ('eq', 'ne') or required not in [*STANDINGS, 'graduate']:
            return 'unknown', [reason], []
        return ('eligible' if OPS[rule.operator](actual, required) else 'ineligible'), [reason], []
    return 'unknown', [f'Needs confirmation: {rule.text}'], []


def evaluate_rule(rule: RequirementRule, student: StudentContext) -> EligibilityStatus:
    return assess_rule(rule, student)[0]


def check_eligibility(db: Database, student_id: str, course_ids: list[str]) -> EligibilityResponse:
    if not 1 <= len(course_ids) <= 100 or len(set(course_ids)) != len(course_ids):
        raise ApiProblem(422, 'VALIDATION_ERROR', 'Choose 1–100 distinct courses')
    student = build_student_context(db, student_id)
    results = []
    for idx in course_ids:
        row = db.execute('SELECT prerequisite_rule_json,prerequisite_text,corequisite_text,restrictions_text FROM courses WHERE id=?', (idx,)).fetchone()
        if row is None:
            raise ApiProblem(404, 'NOT_FOUND', f'Course not found: {idx}')
        if row[0]:
            try:
                rule = RequirementRule.model_validate_json(row[0])
            except ValueError:
                rule = RequirementRule(kind='unknown', text='Stored requirements could not be read')
        else:
            clauses = [parse_requirement_rule(txt) for txt in row[1:] if txt]
            rule = RequirementRule(kind='all', text='Course requirements', children=clauses) if clauses else parse_requirement_rule(None)
        status, reasons, missing = assess_rule(rule, student)
        results.append(Eligibility(course_id=idx, status=status, reasons=reasons, missing_course_ids=missing))
    return EligibilityResponse(results=results)
