from __future__ import annotations

import hashlib
import math
import operator
import re

from app.errors import ApiProblem
from app.schemas import CourseRecord, CourseRequirementCheck, Database, Eligibility, EligibilityResponse, EligibilityStatus, EnrollmentRequirement, Grade, RequirementConfirmation, RequirementRule, StudentContext

LETTERS = ['F', 'D-', 'D', 'D+', 'C-', 'C', 'C+', 'B-', 'B', 'B+', 'A-', 'A', 'A+']
STANDINGS = ['freshman', 'sophomore', 'junior', 'senior']
OPS = {'gte': operator.ge, 'gt': operator.gt, 'lte': operator.le, 'lt': operator.lt, 'eq': operator.eq, 'ne': operator.ne}
MAJORS = {'computer engineering': 'CMPE', 'cmpe': 'CMPE', 'software engineering': 'SE', 'se': 'SE'}
COURSE_CODE = r'[A-Z][A-Z0-9]{1,5}[ -]+\d+[A-Z]*'
AP_CALCULUS_SCORE = r'(?:AP Calculus (?:AB score|BC/AB Subscore) of [1-5]|a score of [1-5] on the AP Calculus (?:AB|BC) Exam)'
CONDITIONAL_WORKSHOP = re.compile(
    rf'(?P<workshop>{COURSE_CODE}) for students with {AP_CALCULUS_SCORE}(?:, {AP_CALCULUS_SCORE})*[,;] '
    rf'or (?P<previous>{COURSE_CODE}) with a grade of (?P<cutoff>[A-DF][+-]?) or lower[,;] '
    rf'or students who are repeating (?P<target>{COURSE_CODE})', re.I,
)

GRADE = r'(?:[A-DF][+-]?|CR|NC)'
GRADE_DESCRIPTION = (
    rf'(?:(?:with\s+)?(?:a\s+)?(?:minimum\s+)?grades?\s+(?:of\s+)?|with\s+(?:a\s+)?)'
    rf'["\']?({GRADE})["\']?(?:\s+or\s+(?:better|higher))?'
)


def split_requirement_text(text: str, pattern: str) -> list[str]:
    """Split logical clauses while retaining parentheses and grade/score comparisons."""
    depth = 0
    start = 0
    parts = []
    for match in re.finditer(r'\(|\)|' + pattern, text, re.I):
        token = match.group()
        if token == '(':
            depth += 1
        elif token == ')':
            depth -= 1
        elif depth == 0:
            if token.lower() == 'or' and re.match(r'\s+(?:better|higher|lower|above|below)\b', text[match.end():], re.I):
                continue
            if (token.lower() == 'or' and 'enrollment category' in text[:match.start()].lower()
                    and re.match(r'\s+(?:[MW]-)?[IVX]+\b', text[match.end():], re.I)):
                continue
            parts.append(text[start:match.start()].strip(' ,;'))
            start = match.end()
    if not parts:
        return [text]
    parts.append(text[start:].strip(' ,;'))
    return parts


def unwrap_requirement(text: str) -> str:
    while text.startswith('(') and text.endswith(')'):
        depth = 0
        for index, character in enumerate(text):
            depth += (character == '(') - (character == ')')
            if depth == 0 and index != len(text) - 1:
                return text
        if depth:
            return text
        text = text[1:-1].strip()
    return text


def parse_course_expression(text: str, grade: str | None = None) -> RequirementRule | None:
    """Recognize expressions consisting entirely of course codes and logical operators."""
    src = unwrap_requirement(text.strip().strip(','))
    shorthand = re.fullmatch(r'([A-Z][A-Z0-9]{1,5})[ -]*0*(\d+[A-Z]*)((?:\s*/\s*\d+[A-Z]*)+)', src, re.I)
    if shorthand:
        numbers = [shorthand[2], *re.split(r'\s*/\s*', shorthand[3].lstrip(' /'))]
        numbers = [re.sub(r'^0+(?=\d)', '', number.upper()) for number in numbers]
        return RequirementRule(kind='any', text=text, children=[
            RequirementRule(kind='course', text=f'{shorthand[1].upper()} {number}',
                            course_id=f'{shorthand[1].upper()}-{number}',
                            minimum_grade=grade)
            for number in numbers
        ])
    for pattern, kind in ((r',\s*(?:and\s+)?', 'all'), (r'\bor\b|/', 'any'), (r'\band\b|\+', 'all')):
        parts = split_requirement_text(src, pattern)
        if len(parts) > 1:
            children = [parse_course_expression(part, grade) for part in parts]
            if any(child is None for child in children):
                return None
            return RequirementRule(kind=kind, text=text, children=children)
    course = re.fullmatch(r'([A-Z][A-Z0-9]{1,5})[ -]*0*(\d+[A-Z]*)', src, re.I)
    if course:
        return RequirementRule(kind='course', text=text, course_id=f'{course[1].upper()}-{course[2].upper()}',
                               minimum_grade=grade)
    return None


def parse_graded_courses(text: str) -> RequirementRule | None:
    leading = re.fullmatch(rf'["\']?({GRADE})["\']?\s+or\s+(?:better|higher)\s+in\s+(.+)', text, re.I)
    if leading:
        return parse_course_expression(leading[2], leading[1].upper())
    trailing = re.fullmatch(
        rf'(.+?)\s*,?\s*(?:\(\s*)?(?:(?:all|both)\s+)?{GRADE_DESCRIPTION}'
        r'\s*(?:in each)?\s*\)?(?:\s+to waive the exam)?', text, re.I,
    )
    if trailing:
        return parse_course_expression(trailing[1], trailing[2].upper())
    parenthesized = re.fullmatch(rf'(.+?)\s*\(["\']?({GRADE})["\']?\s+or\s+(?:better|higher)\)', text, re.I)
    if parenthesized:
        return parse_course_expression(parenthesized[1], parenthesized[2].upper())
    return None


def parse_major_restriction(text: str) -> RequirementRule | None:
    if re.search(COURSE_CODE, text, re.I):
        return None
    match = re.fullmatch(
        r'(?:allowed (?:declared )?majors?\s*:\s*|(?:and\s+)?a major of\s+)(.+)|'
        r'(.+?)\s+majors? only', text, re.I,
    )
    if not match:
        return None
    names = re.split(r',\s*(?:or\s+)?|\s+or\s+|\s+and\s+', match[1] or match[2], flags=re.I)
    codes = [MAJORS.get(name.strip().lower()) for name in names]
    if not all(codes):
        # College membership and unrecognized major names need one complete confirmation.
        return RequirementRule(kind='unknown', text=text)
    children = [RequirementRule(kind='major', text=name.strip(), value=code, operator='eq')
                for name, code in zip(names, codes)]
    return children[0] if len(children) == 1 else RequirementRule(kind='any', text=text, children=children)


def parse_requirement_rule(text: str | None, confirmed_empty: bool = False) -> RequirementRule:
    if not text or not text.strip():
        return RequirementRule(kind='all' if confirmed_empty else 'unknown', text=text or ('No enrollment requirements listed in captured catalog' if confirmed_empty else 'Requirements not verified'))
    src = re.sub(r'\s+', ' ', text.replace('\u200b', '')).strip().rstrip('.; ')
    src = src.translate(str.maketrans({'“': '"', '”': '"', '‘': "'", '’': "'", '−': '-', '–': '-', '‑': '-'}))
    if src.lower() in ('none', 'no prerequisites', 'no prerequisites required'):
        return RequirementRule(kind='all', text=src)
    src = re.sub(r'^(?:prerequisites?|corequisites?|restrictions?)\s*:\s*', '', src, flags=re.I)
    src = unwrap_requirement(src)
    if re.match(r'^\(?if\b', src, re.I):
        return RequirementRule(kind='unknown', text=src)
    major = parse_major_restriction(src)
    if major:
        return major
    # Placement categories and exam score alternatives form complete manual conditions.
    if (re.match(r'^(?:Math|Writing) Enrollment Category\b', src, re.I)
            and not re.search(COURSE_CODE, src) and ';' not in src and not re.search(r'\.\s+', src)):
        return RequirementRule(kind='unknown', text=src)
    if re.search(r'\bAP\b', src) and not re.search(COURSE_CODE, src) and ';' not in src:
        return RequirementRule(kind='unknown', text=src)
    explicit_and = split_requirement_text(src, r';\s*and\b\s*,?\s*|\band\s*,\s*')
    if len(explicit_and) > 1:
        return RequirementRule(kind='all', text=src, children=[parse_requirement_rule(part) for part in explicit_and])
    suffix = re.fullmatch(
        r'(.+?)[.;,]\s*((?:Allowed (?:Declared )?Majors?\s*:|(?:Computer|Software|Any|All)?\s*Engineering Majors? Only).+)',
        src, re.I,
    )
    if suffix:
        return RequirementRule(kind='all', text=src, children=[
            parse_requirement_rule(suffix[1]), parse_requirement_rule(suffix[2]),
        ])
    graded = parse_graded_courses(src)
    if graded:
        return graded
    course_expression = parse_course_expression(src)
    if course_expression:
        return course_expression
    # In catalog prose a trailing major restriction applies to the entire prerequisite.
    major_clause = re.fullmatch(r'(.+?)[,;]\s*((?:computer|software) engineering(?: or (?:computer|software) engineering)? majors? only)', src, re.I)
    if major_clause:
        return RequirementRule(kind='all', text=src, children=[
            parse_requirement_rule(major_clause[1]),
            parse_requirement_rule(major_clause[2]),
        ])
    alternatives = split_requirement_text(src, r';\s*')
    if len(alternatives) > 1 and alternatives[-1].lower().startswith('or '):
        return RequirementRule(kind='any', text=src, children=[
            parse_requirement_rule(re.sub(r'^or\s+', '', part.strip(), flags=re.I))
            for part in alternatives if part.strip()
        ])
    sentences = [part for part in split_requirement_text(src, r'\.(?=\s+|$)|;\s*') if part.strip()]
    if len(sentences) > 1:
        return RequirementRule(kind='all', text=src, children=[parse_requirement_rule(p) for p in sentences if p.strip()])
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
        if any(child.kind == 'unknown' for child in children):
            return RequirementRule(kind='unknown', text=src)
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
        parts = split_requirement_text(src, pattern)
        if len(parts) > 1:
            children = [parse_requirement_rule(part) for part in parts]
            if all(child.kind == 'unknown' for child in children):
                return RequirementRule(kind='unknown', text=src)
            if any(child.kind == 'unknown' and re.fullmatch(r'\d+(?:\.\d+)?', child.text) for child in children):
                return RequirementRule(kind='unknown', text=src)
            return RequirementRule(kind=kind, text=src, children=children)
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


GRADE_POINTS = {
    'A+': 4.0, 'A': 4.0, 'A-': 3.7,
    'B+': 3.3, 'B': 3.0, 'B-': 2.7,
    'C+': 2.3, 'C': 2.0, 'C-': 1.7,
    'D+': 1.3, 'D': 1.0, 'D-': 0.7,
    'F': 0.0, 'WU': 0.0, 'IC': 0.0,
}


def build_student_context(db: Database, student_id: str) -> StudentContext:
    row = db.execute('SELECT major FROM student_profiles WHERE student_id=?', (student_id,)).fetchone()
    if row is None:
        raise ApiProblem(404, 'NOT_FOUND', 'Profile not found')
    rows = db.execute(
        'SELECT r.course_id,r.status,r.grade,r.term,c.units_min,c.units_max '
        'FROM student_course_attempts r JOIN courses c ON c.id=r.course_id WHERE r.student_id=?',
        (student_id,),
    )
    records = []
    earned_units = 0.0
    graded_units = 0.0
    quality_points = 0.0
    earned_units_known = True
    gpa_known = True

    for course_id, status, grade, term, min_units, max_units in rows:
        records.append(CourseRecord(course_id=course_id, status=status, grade=grade, term=term))
        if status != 'completed':
            continue
        units = min_units if min_units == max_units else None
        if grade is None:
            gpa_known = False
        contribution = course_earned_units(status, grade, min_units, max_units)
        if contribution is None:
            earned_units_known = False
        else:
            earned_units += contribution
        if grade in GRADE_POINTS:
            if units is None:
                gpa_known = False
            else:
                graded_units += units
                quality_points += units * GRADE_POINTS[grade]

    standing = 'unspecified'
    if earned_units_known:
        standing = 'freshman'
        for threshold, level in ((30, 'sophomore'), (60, 'junior'), (90, 'senior')):
            if earned_units >= threshold:
                standing = level
    confirmed_requirements: dict[str, list[str]] = {}
    for course_id, requirement_id in db.execute(
        'SELECT course_id,requirement_id FROM student_requirement_confirmations WHERE student_id=?',
        (student_id,),
    ):
        confirmed_requirements.setdefault(course_id, []).append(requirement_id)
    return StudentContext(
        student_id=student_id,
        major_code=row[0],
        standing=standing,
        gpa=quality_points / graded_units if gpa_known and graded_units else None,
        earned_units=earned_units if earned_units_known else None,
        course_records=records,
        confirmed_requirements=confirmed_requirements,
    )


def course_earned_units(status: str, grade: Grade | None, min_units: float | None, max_units: float | None) -> float | None:
    if status != 'completed':
        return 0
    if grade is None:
        return None
    if evaluate_grade(grade, None) != 'eligible':
        return 0
    return min_units if min_units == max_units else None


def evaluate_grade(grade: Grade | None, minimum_grade: str | None) -> EligibilityStatus:
    if grade in ('F', 'NC', 'WU', 'IC'):
        return 'ineligible'
    if grade is None or grade in ('W', 'I', 'RP', 'RD', 'AU'):
        return 'unknown'
    if minimum_grade == 'CR':
        return 'eligible' if grade == 'CR' else 'unknown'
    if minimum_grade is not None and minimum_grade not in LETTERS:
        return 'unknown'
    if grade == 'CR':
        return 'unknown' if minimum_grade else 'eligible'
    return 'eligible' if LETTERS.index(grade) >= LETTERS.index(minimum_grade or 'D-') else 'ineligible'


def requirement_id(rule: RequirementRule) -> str:
    # Include the full rule so a catalog change invalidates an older confirmation.
    return hashlib.sha256(rule.model_dump_json().encode()).hexdigest()


def confirmable_requirements(rule: RequirementRule) -> dict[str, RequirementRule]:
    if (rule.kind == 'conditional_workshop' or (rule.kind == 'course' and rule.concurrent and rule.minimum_grade is None)
            or (rule.kind == 'unknown' and rule.text not in (
        'Requirements not verified', 'Stored requirements could not be read', 'Stored enrollment paths could not be read',
    ) and rule.text.strip())):
        return {requirement_id(rule): rule}
    return {
        key: clause for child in rule.children
        for key, clause in confirmable_requirements(child).items()
    }


def assess_rule(
    rule: RequirementRule, student: StudentContext, confirmed: set[str] | None = None,
) -> tuple[EligibilityStatus, list[str], list[str]]:
    manual = rule.kind in ('unknown', 'conditional_workshop') or (rule.kind == 'course' and rule.concurrent and rule.minimum_grade is None)
    if manual and confirmed and requirement_id(rule) in confirmed:
        return 'eligible', [f'Confirmed by you: {rule.text}'], []
    if rule.kind == 'first_attempt':
        repeating = any(record.course_id == rule.course_id and record.status == 'completed'
                        for record in student.course_records)
        return ('ineligible' if repeating else 'eligible'), [rule.text], []
    if rule.kind in ('all', 'any'):
        if not rule.children:
            return ('eligible', [], []) if rule.kind == 'all' else ('unknown', [rule.text], [])
        parts = [assess_rule(child, student, confirmed) for child in rule.children]
        states = [p[0] for p in parts]
        if rule.kind == 'all':
            status = 'ineligible' if 'ineligible' in states else 'unknown' if 'unknown' in states else 'eligible'
        else:
            status = 'eligible' if 'eligible' in states else 'unknown' if 'unknown' in states else 'ineligible'
        relevant = [p for p in parts if p[0] == 'eligible'] if rule.kind == 'any' and status == 'eligible' else parts
        missing = list(dict.fromkeys(c for p in relevant for c in p[2]))
        if rule.kind == 'any':
            missing = [course for course in missing if all(course in p[2] for p in parts)]
        return status, [r for p in relevant for r in p[1]], missing
    if rule.kind == 'course':
        record = next((r for r in student.course_records if r.course_id == rule.course_id), None)
        if rule.concurrent and rule.value:
            target = next((r for r in student.course_records if r.course_id == rule.value), None)
            if (record and target and record.term and record.term == target.term
                    and (record.status in ('planned', 'in_progress') or evaluate_grade(record.grade, rule.minimum_grade) == 'eligible')):
                return 'eligible', [f'Concurrent enrollment: {rule.text}'], []
            return 'unknown', [f'Concurrent enrollment: {rule.text}'], []
        actual = f'{record.status}, grade {record.grade or "unknown"}' if record else 'no course record'
        reason = f'{rule.course_id}: requires completed credit' + (f' with grade {rule.minimum_grade} or higher' if rule.minimum_grade else '') + f'; actual: {actual}.'
        if rule.concurrent or not rule.course_id:
            return 'unknown', [reason + ' Concurrent enrollment requires confirmation.'], []
        status = evaluate_grade(record.grade, rule.minimum_grade) if record and record.status == 'completed' else 'ineligible'
        return status, [reason], [rule.course_id] if status == 'ineligible' else []
    if rule.kind == 'conditional_workshop' and len(rule.children) == 1:
        repeated = any(record.course_id == rule.course_id and record.status == 'completed'
                       for record in student.course_records)
        path = rule.children[0]
        if not repeated and assess_rule(path, student)[0] == 'eligible':
            prerequisite = str(path.course_id).replace('-', ' ')
            workshop = str(rule.value).replace('-', ' ')
            return 'eligible', [
                f'{prerequisite} with a grade of {path.minimum_grade} or higher meets the coursework path without {workshop}. '
                'Confirm workshop requirements if using AP placement or repeating the course.'
            ], []
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


def evaluate_rule(rule: RequirementRule, student: StudentContext, confirmed: set[str] | None = None) -> EligibilityStatus:
    return assess_rule(rule, student, confirmed)[0]


def parse_corequisite_rule(course_id: str, text: str) -> RequirementRule:
    normalized = ' '.join(text.split()).rstrip('.').translate(str.maketrans('−–‑', '---'))
    clause = CONDITIONAL_WORKSHOP.fullmatch(normalized)
    if clause:
        target = parse_requirement_rule(clause['target']).course_id
        workshop = parse_requirement_rule(clause['workshop']).course_id
        prerequisite = parse_requirement_rule(clause['previous'])
        cutoff = clause['cutoff'].upper()
        if (target == course_id and workshop == course_id + 'W' and prerequisite.kind == 'course'
                and prerequisite.course_id != course_id and cutoff in LETTERS[:-1]):
            prerequisite.minimum_grade = LETTERS[LETTERS.index(cutoff) + 1]
            return RequirementRule(kind='conditional_workshop', text=text, course_id=target,
                                   value=workshop, children=[prerequisite])
    return RequirementRule(kind='unknown', text=text)


def parse_course_requirements(course_id: str, prerequisite: str | None, corequisite: str | None,
                              restrictions: str | None, confirmed_empty: bool = False) -> RequirementRule:
    clauses = [parse_requirement_rule(prerequisite)] if prerequisite else []
    if corequisite:
        clauses.append(parse_corequisite_rule(course_id, corequisite))
    if restrictions:
        clauses.append(parse_requirement_rule(restrictions))
    if clauses:
        return RequirementRule(kind='all', text='Course requirements', children=clauses)
    return parse_requirement_rule(None, confirmed_empty=confirmed_empty)


def get_course_requirement(db: Database, course_id: str) -> RequirementRule:
    row = db.execute(
        'SELECT prerequisite_rule_json,prerequisite_text,corequisite_text,restrictions_text FROM courses WHERE id=?',
        (course_id,),
    ).fetchone()
    if row is None:
        raise ApiProblem(404, 'NOT_FOUND', f'Course not found: {course_id}')
    policy = db.execute('SELECT rule_json FROM course_enrollment_policies WHERE course_id=?', (course_id,)).fetchone()
    if policy:
        try:
            return RequirementRule.model_validate_json(policy[0])
        except ValueError:
            return RequirementRule(kind='unknown', text='Stored enrollment paths could not be read')
    stored_rule, prerequisite, corequisite, restrictions = row
    # Rebuild from the original prose so older imports benefit from parser corrections.
    if prerequisite or corequisite or restrictions or not stored_rule:
        return parse_course_requirements(course_id, prerequisite, corequisite, restrictions)
    try:
        rule = RequirementRule.model_validate_json(stored_rule)
    except ValueError:
        return RequirementRule(kind='unknown', text='Stored requirements could not be read')
    return rule


def course_requirement_checks(
    rule: RequirementRule, student: StudentContext, alternative: bool = False,
) -> list[CourseRequirementCheck]:
    if rule.kind == 'course' and rule.course_id:
        record = next((record for record in student.course_records if record.course_id == rule.course_id), None)
        return [CourseRequirementCheck(
            course_id=rule.course_id, minimum_grade=rule.minimum_grade, alternative=alternative,
            status=assess_rule(rule, student)[0], recorded_status=record.status if record else None,
            grade=record.grade if record else None,
            concurrent=rule.concurrent,
        )]
    if rule.kind not in ('all', 'any'):
        return []
    return [
        check for child in rule.children
        for check in course_requirement_checks(child, student, alternative or rule.kind == 'any')
    ]


def enrollment_requirement(rule: RequirementRule, student: StudentContext, confirmed: set[str]) -> EnrollmentRequirement:
    status = assess_rule(rule, student, confirmed)[0]
    if rule.kind in ('all', 'any'):
        children = [enrollment_requirement(child, student, confirmed) for child in rule.children]
        if len(children) == 1:
            return children[0]
        return EnrollmentRequirement(kind=rule.kind, text=rule.text, status=status, children=children)
    manual = requirement_id(rule) in confirmable_requirements(rule)
    course = course_requirement_checks(rule, student)
    return EnrollmentRequirement(
        kind='course' if course else 'confirmation' if manual else 'check',
        text=rule.text, status=status, course=course[0] if course else None,
        confirmation=RequirementConfirmation(
            id=requirement_id(rule), text=rule.text, confirmed=requirement_id(rule) in confirmed,
            satisfied=status == 'eligible',
        ) if manual else None,
    )


def assess_course(course_id: str, rule: RequirementRule, student: StudentContext) -> Eligibility:
    confirmed = set(student.confirmed_requirements.get(course_id, []))
    status, reasons, missing = assess_rule(rule, student, confirmed)
    return Eligibility(
        course_id=course_id, status=status, reasons=reasons, missing_course_ids=missing,
        additional_requirements=[
            RequirementConfirmation(
                id=key, text=clause.text, confirmed=key in confirmed,
                satisfied=assess_rule(clause, student, confirmed)[0] == 'eligible',
            )
            for key, clause in confirmable_requirements(rule).items()
        ],
        course_requirements=course_requirement_checks(rule, student),
        requirements=enrollment_requirement(rule, student, confirmed),
    )


def save_requirement_confirmations(
    db: Database, student_id: str, course_id: str, updates: dict[str, bool],
) -> None:
    if not updates:
        return
    available = confirmable_requirements(get_course_requirement(db, course_id))
    if not available.keys() >= updates.keys():
        raise ApiProblem(422, 'VALIDATION_ERROR', 'A requirement has changed. Reload the course and review it again.')
    for key, confirmed in updates.items():
        if confirmed:
            db.execute(
                'INSERT OR IGNORE INTO student_requirement_confirmations (student_id,course_id,requirement_id) VALUES (?,?,?)',
                (student_id, course_id, key),
            )
        else:
            db.execute(
                'DELETE FROM student_requirement_confirmations WHERE student_id=? AND course_id=? AND requirement_id=?',
                (student_id, course_id, key),
            )


def update_requirement_confirmation(
    db: Database, student_id: str, course_id: str, key: str, confirmed: bool,
) -> Eligibility:
    with db:
        db.execute('BEGIN IMMEDIATE')
        save_requirement_confirmations(db, student_id, course_id, {key: confirmed})
    return check_eligibility(db, student_id, [course_id]).results[0]


def check_eligibility(db: Database, student_id: str, course_ids: list[str]) -> EligibilityResponse:
    if not 1 <= len(course_ids) <= 100 or len(set(course_ids)) != len(course_ids):
        raise ApiProblem(422, 'VALIDATION_ERROR', 'Choose 1–100 distinct courses')
    student = build_student_context(db, student_id)
    sources = dict(db.execute('SELECT course_id,source_url FROM course_enrollment_policies'))
    return EligibilityResponse(results=[
        assess_course(course_id, get_course_requirement(db, course_id), student).model_copy(
            update={'source_url': sources.get(course_id)},
        ) for course_id in course_ids
    ])
