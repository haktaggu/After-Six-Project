from __future__ import annotations

from app.errors import ApiProblem
from app.features.courses import get_course
from app.features.prerequisites import assess_course, build_student_context, evaluate_grade, get_course_requirement, parse_requirement_rule
from app.features.suggestions import can_suggest, suggest_courses
from app.schemas import AuthenticatedStudent, Database, Major, MajorRoadmap, Page, PrerequisiteLink, ProgressSummary, RequirementRule, RoadmapEntry, RoadmapRequirement, StudentRoadmap, StudentRoadmapEntry


def list_majors(db: Database, limit: int = 25, offset: int = 0) -> Page[Major]:
    total = db.execute('SELECT count(*) FROM major_roadmaps').fetchone()[0]
    rows = db.execute('SELECT major_code,title,degree_type,description FROM major_roadmaps ORDER BY major_code LIMIT ? OFFSET ?', (limit, offset))
    majors = [
        Major(major_code=code, title=title, degree_type=degree, description=description)
        for code, title, degree, description in rows
    ]
    return Page(items=majors, total=total, limit=limit, offset=offset)


def get_major_roadmap(db: Database, major_code: str) -> MajorRoadmap:
    row = db.execute('SELECT major_code,title,degree_type,description FROM major_roadmaps WHERE major_code=?', (major_code,)).fetchone()
    if row is None:
        raise ApiProblem(404, 'NOT_FOUND', 'Major not found')
    code, title, degree, description = row
    major = Major(major_code=code, title=title, degree_type=degree, description=description)
    rows = db.execute('SELECT course_id,term_order,is_required FROM roadmap_courses WHERE major_code=? ORDER BY term_order,course_id', (major_code,))
    requirements = db.execute(
        'SELECT term_order,label,units,flexible FROM roadmap_requirements WHERE major_code=? ORDER BY term_order,id',
        (major_code,),
    )
    courses = [
        RoadmapEntry(course=get_course(db, course_id), term_order=term_order, is_required=bool(is_required))
        for course_id, term_order, is_required in rows
    ]
    roadmap_requirements = [
        RoadmapRequirement(term_order=term, label=label, units=units, flexible=bool(flexible))
        for term, label, units, flexible in requirements
    ]
    return MajorRoadmap(major=major, courses=courses, requirements=roadmap_requirements)


def get_student_roadmap(db: Database, student: AuthenticatedStudent) -> StudentRoadmap:
    row = db.execute('SELECT major,recommendation_limit FROM student_profiles WHERE student_id=?', (student.student_id,)).fetchone()
    if not row or not row[0]:
        raise ApiProblem(409, 'PROFILE_INCOMPLETE', 'Choose your major in Profile')
    major, recommendation_limit = row
    template = get_major_roadmap(db, major)
    context = build_student_context(db, student.student_id)
    records = {record.course_id: record for record in context.course_records}
    rules = {}
    courses = []
    for entry in template.courses:
        course_id = entry.course.id
        record = records.get(course_id)
        rule = get_course_requirement(db, course_id)
        rules[course_id] = rule
        courses.append(StudentRoadmapEntry(
            **entry.model_dump(),
            student_status=record.status if record else 'not_started',
            grade=record.grade if record else None,
            eligibility=assess_course(course_id, rule, context),
            prerequisites=prerequisite_links(parse_requirement_rule(entry.course.prerequisite_text)),
        ))
    return StudentRoadmap(
        major=template.major,
        courses=courses,
        requirements=template.requirements,
        summary=calculate_progress(courses),
        recommendations=recommend_courses(courses)[:recommendation_limit],
        suggestions=suggest_courses(db, courses, rules, context, recommendation_limit),
        recommendation_limit=recommendation_limit,
    )


def prerequisite_links(rule: RequirementRule, alternative: bool = False) -> list[PrerequisiteLink]:
    if rule.kind == 'course' and rule.course_id:
        return [PrerequisiteLink(course_id=rule.course_id, alternative=alternative)]
    links = {}
    for child in rule.children:
        for link in prerequisite_links(child, alternative or rule.kind == 'any'):
            previous = links.get(link.course_id)
            if previous is None or not link.alternative:
                links[link.course_id] = link
    return list(links.values())


def calculate_progress(courses: list[StudentRoadmapEntry]) -> ProgressSummary:
    required = set()
    completed = set()
    for entry in courses:
        if not entry.is_required:
            continue
        required.add(entry.course.id)
        if entry.student_status == 'completed' and evaluate_grade(entry.grade, None) == 'eligible':
            completed.add(entry.course.id)

    return ProgressSummary(
        completed_courses=len(completed),
        total_required_courses=len(required),
        completion_percent=100 * len(completed) / len(required) if required else 0,
    )


def recommend_courses(courses: list[StudentRoadmapEntry]) -> list[str]:
    ordered_courses = sorted(courses, key=lambda entry: (entry.term_order, entry.course.id))
    recommendations = []
    seen = set()
    for entry in ordered_courses:
        if not entry.is_required or entry.eligibility.status != 'eligible':
            continue
        course_id = entry.course.id
        if course_id not in seen and can_suggest(entry.student_status, entry.grade):
            seen.add(course_id)
            recommendations.append(course_id)
    return recommendations
