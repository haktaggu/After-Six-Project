import { apiRequest, queryString } from './client'
import type { CourseRecord, CourseRecordInput, CsrfResponse, LoginRequest, Page, PaginationQuery, ProfileResponse, ProfileUpdate, SessionResponse } from './types'

// - GET /api/auth/csrf.
// - Returns {csrf_token:string}; save via setCsrfToken before login.
// - CsrfResponse: {csrf_token: string}.
export function fetchCsrf(): Promise<CsrfResponse> {
  return apiRequest<CsrfResponse>('/auth/csrf')
}

// - POST /api/auth/login.
// - Response sets HttpOnly cookie; save response.csrf_token in memory. Never store session tokens.
// - LoginRequest: {email: string, password: string}.
// - SessionResponse: {user: User, csrf_token: string, expires_at: string}.
export function login(body: LoginRequest): Promise<SessionResponse> {
  return apiRequest<SessionResponse>('/auth/login', { method: 'POST', body })
}

// - GET /api/auth/session.
// - 401 is a missing/expired session, not a successful anonymous response.
export function getSession(): Promise<SessionResponse> {
  return apiRequest<SessionResponse>('/auth/session')
}

// - POST /api/auth/logout.
// - 204 with no JSON; backend clears session cookie. Clear private browser state/CSRF on success.
export function logout(): Promise<void> {
  return apiRequest<void>('/auth/logout', { method: 'POST' })
}

// - GET /api/me.
// - Profile has major_code:string|null, standing:freshman/sophomore/junior/senior/graduate/
//   unspecified, gpa:number|null (0..4), earned_units:integer|null (>=0). Name/email stay read-only.
// - ProfileResponse: {user: User, profile: Profile}.
export function getProfile(): Promise<ProfileResponse> {
  return apiRequest<ProfileResponse>('/me')
}

// - PATCH /api/me.
// - Send all fields: {major_code,standing,gpa,earned_units}. A non-null major must exist.
// - GPA is finite 0..4, units a nonnegative integer; null clears GPA/units/major. Unknown standing
//   is unspecified. These are cumulative academic facts, not totals calculated from course history.
export function updateProfile(body: ProfileUpdate): Promise<ProfileResponse> {
  return apiRequest<ProfileResponse>('/me', { method: 'PATCH', body })
}

// - GET /api/me/course-records.
// - Sorted by course_id; total is before pagination.
// - PaginationQuery: {limit?: number, offset?: number}.
// - CourseRecord: {course_id,status:completed/in_progress/planned,grade:Grade|null,term:string|null}.
export function listCourseRecords(query: PaginationQuery = {}): Promise<Page<CourseRecord>> {
  return apiRequest<Page<CourseRecord>>('/me/course-records' + queryString(query))
}

// - PUT /api/me/course-records/{courseId}.
// - 201 new or 200 updated. A non-null term must exist.
// - CourseRecordInput: {status,grade,term}, all required. Only completed records allow a non-null
//   uppercase Grade (A+,A,A-,B+,B,B-,C+,C,C-,D+,D,D-,F,CR,NC,WU,IC,W,I,RP,RD,AU).
export function putCourseRecord(courseId: string, body: CourseRecordInput): Promise<CourseRecord> {
  return apiRequest<CourseRecord>(`/me/course-records/${encodeURIComponent(courseId)}`, { method: 'PUT', body })
}

// - DELETE /api/me/course-records/{courseId}.
// - 204 even on repeat delete; no JSON body.
export function deleteCourseRecord(courseId: string): Promise<void> {
  return apiRequest<void>(`/me/course-records/${encodeURIComponent(courseId)}`, { method: 'DELETE' })
}
