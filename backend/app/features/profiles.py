from __future__ import annotations

from app.errors import ApiProblem
from app.schemas import AuthenticatedStudent, CourseRecord, CourseRecordInput, Database, Page, ProfileResponse, ProfileUpdate, RecordMutationResult

# - Read users through student.user_id and profiles through student.student_id, with parameters.
# - users has id,username,email,full_name,password_hash,created_at. student_profiles has
#   student_id,user_id,major,standing,gpa,earned_units; expose major as major_code.
# - Return {user:{id,email,full_name,created_at},profile:{major_code,standing,gpa,earned_units}}.
#   Missing linked profile raises ApiProblem(404,"NOT_FOUND","Profile not found").
def get_profile(db: Database, student: AuthenticatedStudent) -> ProfileResponse:
    raise NotImplementedError


# - PATCH /api/me supplies all four fields: major_code,standing,gpa,earned_units. All are required;
#   null clears major/GPA/units. Standing is freshman/sophomore/junior/senior/graduate/unspecified.
# - GPA is finite 0..4; earned_units is a nonnegative integer or None. A non-null major must
#   exist in major_roadmaps, otherwise raise 422 VALIDATION_ERROR. Zero is a real value, not missing.
# - Store the supplied cumulative facts; do not recalculate them from the partial demo history
#   or derive standing from units. An unavailable fact stays unknown to the prerequisite engine.
# - Update only this student's profile in one transaction; commit and return get_profile.
#   Account name/email stay read-only. Profile changes must refresh roadmap/watchlist eligibility.
def update_profile(db: Database, student: AuthenticatedStudent, body: ProfileUpdate) -> ProfileResponse:
    raise NotImplementedError


# - Read student_course_attempts for this student; count before LIMIT/OFFSET. No writes/commits.
# - Sort course_id ASC; limit 1..100 and offset >=0, defaults 25/0.
# - Return Page[CourseRecord]: {items:[{course_id,status,grade,term}],total,limit,offset}.
#   Grade/term are included even when null. Empty history has items=[] and total=0.
def list_course_records(db: Database, student: AuthenticatedStudent, limit: int = 25, offset: int = 0) -> Page[CourseRecord]:
    raise NotImplementedError


# - PUT /api/me/course-records/{course_id} supplies {status,grade,term}, all required.
# - status is completed/in_progress/planned. Only completed may have a grade; use uppercase
#   A+,A,A-,B+,B,B-,C+,C,C-,D+,D,D-,F,CR,NC,WU,IC,W,I,RP,RD,AU or null for an unknown grade.
#   A completed attempt can have a failing grade; it must not become a passed prerequisite.
# - Missing course ->404 NOT_FOUND; an unknown non-null term ->422 VALIDATION_ERROR.
# - Upsert student_course_attempts(student_id,course_id,status,grade,term) in one transaction,
#   with SQL parameters and UNIQUE(student_id,course_id). No change to cumulative GPA/units.
# - Commit and return RecordMutationResult(record=CourseRecord(...),created=bool). Only a new
#   row sets created=True; the router returns 201 for it and 200 for an existing row.
def put_course_record(db: Database, student: AuthenticatedStudent, course_id: str, body: CourseRecordInput) -> RecordMutationResult:
    raise NotImplementedError


# - Delete only this student's course record in one parameterized transaction. Missing still
#   succeeds with 204. Never delete a shared course or rewrite cumulative profile facts.
# - A course-history edit/deletion must refresh roadmap and watchlist eligibility.
def delete_course_record(db: Database, student: AuthenticatedStudent, course_id: str) -> None:
    raise NotImplementedError
