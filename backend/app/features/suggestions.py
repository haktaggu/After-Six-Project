from collections import deque

from app.features.courses import get_course
from app.features.prerequisites import assess_course, evaluate_grade, evaluate_rule, get_course_requirement
from app.schemas import CourseSuggestion, CourseSuggestionStatus, Database, Eligibility, Grade, RequirementRule, StudentContext, StudentRoadmapEntry


SUGGESTION_PRIORITY = {
    'ready': (0, 3),
    'after_current': (1, 4),
    'needs_review': (2, 5),
    'requirements_remaining': (6, 7),
}


def can_suggest(status: str, grade: Grade | None) -> bool:
    return status != 'in_progress' and not (status == 'completed' and evaluate_grade(grade, None) == 'eligible')


def outstanding_credit_options(rule: RequirementRule, student: StudentContext, confirmed: set[str]) -> list[str]:
    if evaluate_rule(rule, student, confirmed) == 'eligible':
        return []
    if rule.kind == 'course':
        return [rule.course_id] if rule.course_id else []
    return list(dict.fromkeys(
        course_id for child in rule.children for course_id in outstanding_credit_options(child, student, confirmed)
    ))


def courses_to_finish(rule: RequirementRule, student: StudentContext, credit_options: list[str], confirmed: set[str]) -> list[str]:
    current = {record.course_id for record in student.course_records if record.status == 'in_progress'}
    candidates = current.intersection(credit_options)
    if not candidates:
        return []

    def qualifies(course_ids: set[str]) -> bool:
        # Project the best possible course grades to establish whether the path is feasible.
        # The suggestion asks for the required grades and does not project GPA or standing.
        records = [
            record.model_copy(update={'status': 'completed', 'grade': 'A+'}) if record.course_id in course_ids else record
            for record in student.course_records
        ]
        return evaluate_rule(rule, student.model_copy(update={'course_records': records}), confirmed) == 'eligible'

    if not qualifies(candidates):
        return []
    # Drop courses that are unnecessary, including options in an OR branch already satisfied.
    for course_id in sorted(candidates, reverse=True):
        reduced = candidates - {course_id}
        if reduced and qualifies(reduced):
            candidates = reduced
    return sorted(candidates)


def classify_suggestion(
    eligibility: Eligibility, rule: RequirementRule, student: StudentContext,
    credit_options: list[str], unlocks: str | None,
) -> tuple[CourseSuggestionStatus, str]:
    if eligibility.status == 'eligible':
        return 'ready', f'Can help unlock {unlocks}.' if unlocks else 'Your saved history meets the requirements.'
    confirmed = set(student.confirmed_requirements.get(eligibility.course_id, []))
    finish = courses_to_finish(rule, student, credit_options, confirmed)
    if finish:
        courses = ', '.join(finish)
        grade_label = 'grade' if len(finish) == 1 else 'grades'
        return 'after_current', f'Complete {courses} with the required {grade_label}.'
    if eligibility.status == 'unknown':
        workshop = next((reason for reason in eligibility.reasons if reason.startswith('Concurrent enrollment: ')), None)
        if workshop:
            return 'needs_review', workshop.removeprefix('Concurrent enrollment: ')
        detail = next((reason for reason in eligibility.reasons if reason.startswith('Needs confirmation: ')), None)
        if detail:
            detail = ' '.join(detail.removeprefix('Needs confirmation: ').split())
            if len(detail) > 120:
                detail = detail[:117].rsplit(' ', 1)[0] + '…'
            return 'needs_review', f'Check the catalog condition “{detail}”.'
        return 'needs_review', 'Confirm the required grades or enrollment conditions in the catalog.'
    if eligibility.missing_course_ids:
        return 'requirements_remaining', f'Check the required credit or grade for {", ".join(eligibility.missing_course_ids)}.'
    if credit_options:
        return 'requirements_remaining', f'Review prerequisite options such as {", ".join(credit_options[:2])}.'
    return 'requirements_remaining', 'Review the remaining enrollment requirements in the catalog.'


def suggest_courses(
    db: Database, courses: list[StudentRoadmapEntry], rules: dict[str, RequirementRule],
    student: StudentContext, target: int,
) -> list[CourseSuggestion]:
    ranked: list[tuple[int, int, str, CourseSuggestion]] = []
    linked = deque()
    seen = set(rules)
    records = {record.course_id: record for record in student.course_records}

    def add(course_id: str, title: str, term: int, required: bool, eligibility: Eligibility,
            rule: RequirementRule, unlocks: str | None = None) -> list[str]:
        confirmed = set(student.confirmed_requirements.get(course_id, []))
        options = outstanding_credit_options(rule, student, confirmed) if eligibility.status != 'eligible' else []
        status, reason = classify_suggestion(eligibility, rule, student, options, unlocks)
        suggestion = CourseSuggestion(course_id=course_id, title=title, status=status, reason=reason)
        ranked.append((SUGGESTION_PRIORITY[status][0 if required else 1], term, course_id, suggestion))
        return options

    for entry in courses:
        if not can_suggest(entry.student_status, entry.grade):
            continue
        options = add(entry.course.id, entry.course.title, entry.term_order, entry.is_required,
                      entry.eligibility, rules[entry.course.id])
        if entry.is_required:
            linked.extend((course_id, entry.term_order, entry.course.id) for course_id in options)

    if sum(rank < 3 for rank, *_ in ranked) < target:
        while linked:
            course_id, term, unlocks = linked.popleft()
            if course_id in seen:
                continue
            seen.add(course_id)
            record = records.get(course_id)
            if record and not can_suggest(record.status, record.grade):
                continue
            if not db.execute('SELECT 1 FROM courses WHERE id=? AND catalog_url IS NOT NULL', (course_id,)).fetchone():
                continue
            course = get_course(db, course_id)
            rule = get_course_requirement(db, course_id)
            options = add(course_id, course.title, term, False, assess_course(course_id, rule, student), rule, unlocks)
            linked.extend((option, term, course_id) for option in options)

    ranked.sort(key=lambda item: (item[0], item[1], item[2]))
    return [suggestion for _, _, _, suggestion in ranked[:target]]
