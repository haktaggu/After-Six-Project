from __future__ import annotations

from app.errors import ApiProblem
from app.schemas import Database, EligibilityResponse, EligibilityStatus, Grade, RequirementRule, StudentContext

# - Parse course codes, minimum letter grades, cumulative GPA, total earned units, class standing
#   and major restrictions into one tree. Include prerequisite, corequisite and restriction clauses.
# - RequirementRule: kind all/any/course/gpa/units/standing/major/unknown, text, children[],
#   course_id|null, minimum_grade|null, concurrent:bool, value:str|float|null,
#   operator:gte/gt/lte/lt/eq/ne (default gte). Course IDs use SUBJECT-number, e.g. CMPE-130.
# - AND binds before OR; preserve parentheses. Numeric thresholds use their stated operator.
#   "junior standing" is standing/value='junior'/gte; "upper division" means junior or above.
#   Exact standing lists use any with eq children. Major allow/exclude rules use eq/ne and
#   canonical major codes; group allowed alternatives with any. Verify name-to-code mappings.
# - Only confirmed_empty=True with blank text means an all-rule with no children. Missing text
#   is unknown. Preserve ambiguous clauses, permissions and placement requirements as unknown.
# - Major/SJSU-only GPA and subject/residency-specific units need data we do not collect; keep
#   those clauses unknown rather than substituting cumulative GPA or total units.
def parse_requirement_rule(text: str | None, confirmed_empty: bool = False) -> RequirementRule:
    raise NotImplementedError


# - student_id comes from the authenticated caller. Missing profile raises 404 NOT_FOUND.
# - Read student_profiles(student_id,user_id,major,standing,gpa,earned_units), mapping major to
#   major_code. GPA and earned units are user-entered cumulative values, not totals of this
#   partial course history. Missing GPA/units/major stay None; standing='unspecified' is unknown.
# - Read student_course_attempts(student_id,course_id,status,grade,term) with parameters.
# - Return StudentContext(student_id,major_code,standing,gpa,earned_units,course_records).
#   CourseRecord is {course_id,status,grade,term}; status completed/in_progress/planned,
#   grade is an uppercase Grade or None, term is an imported ID or None. No writes/commits.
def build_student_context(db: Database, student_id: str) -> StudentContext:
    raise NotImplementedError


# - Compare completed-course grades using F < D- < D < D+ < C- < C < C+ < B- < B < B+ < A- < A < A+.
#   Never compare grade strings alphabetically. An unsupported minimum grade returns unknown.
# - F/NC/WU/IC are failures. Missing grade and W/I/RP/RD/AU are unknown, never a pass.
# - With no stated minimum, a passing letter grade or CR is eligible. With a letter minimum,
#   compare the letter rank. CR stays unknown because it does not establish a specific letter
#   grade or whether a major accepts credit/no credit for that requirement.
def evaluate_grade(grade: Grade | None, minimum_grade: str | None) -> EligibilityStatus:
    raise NotImplementedError


# - all: any ineligible child -> ineligible; otherwise any unknown -> unknown; else eligible.
#   any: any eligible child -> eligible; otherwise any unknown -> unknown; else ineligible.
#   An empty all is eligible; empty any or malformed/unknown rule is unknown.
# - Course nodes require a completed record, then call evaluate_grade for its minimum_grade.
#   Missing course/non-completed status is ineligible. Planned courses never satisfy a rule.
#   concurrent=True remains unknown; concurrency is not inferred from in_progress status.
# - GPA/units compare student.gpa/student.earned_units to numeric rule.value using operator.
#   Zero is known; only None is missing. Require finite GPA threshold 0..4 and units >=0.
# - Standing uses freshman < sophomore < junior < senior and the stated operator. unspecified
#   is unknown. Graduate standing supports exact eq/ne; cross-level ordering is unknown.
# - Major compares canonical student.major_code to rule.value with eq/ne only. A missing major
#   is unknown, a known disallowed major is ineligible. Never match names by substring.
# - Missing student facts, invalid values/operators or unsupported clauses return unknown with
#   their condition preserved. Recognized grade/GPA/units/standing/major rules must be evaluated.
def evaluate_rule(rule: RequirementRule, student: StudentContext) -> EligibilityStatus:
    raise NotImplementedError


# - Validate 1..100 unique course IDs; load build_student_context once and preserve input order.
# - Read courses(id,prerequisite_rule_json,prerequisite_text,corequisite_text,restrictions_text).
#   Missing course raises 404 NOT_FOUND. Decode stored rules or parse the full source text.
# - Evaluate every condition through evaluate_rule. Walk the same tree for reasons that name
#   the required and actual grade/GPA/units/standing/major; never label unknown data as passing.
# - missing_course_ids includes absent, unfinished or insufficient-grade prerequisite courses.
#   Deduplicate IDs. Do not list a course missing because of a failed OR alternative when another
#   alternative passes; GPA/standing/unit/major failures belong in reasons, not invented IDs.
# - Return EligibilityResponse(results=[{course_id,status,reasons,missing_course_ids}]).
#   Roadmap and watchlist reuse this result. This function does not write or commit.
def check_eligibility(db: Database, student_id: str, course_ids: list[str]) -> EligibilityResponse:
    raise NotImplementedError
