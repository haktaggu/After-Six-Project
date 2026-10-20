import { apiRequest, queryString } from './client'
import type { EligibilityRequest, EligibilityResponse, Major, MajorRoadmap, Page, PaginationQuery, StudentRoadmap } from './types'

// - GET /api/majors.
// - Sort by major_code. Dashboard reuses this function.
// - PaginationQuery: {limit?: number, offset?: number}.
// - Major: {major_code: string, title: string, degree_type: string, description: string | null}.
export function listMajors(query: PaginationQuery = {}): Promise<Page<Major>> {
  return apiRequest<Page<Major>>('/majors' + queryString(query))
}

// - GET /api/majors/{majorCode}/roadmap.
// - Sort courses by term_order then course ID.
// - MajorRoadmap: {major: Major, courses: RoadmapEntry[]}.
export function getMajorRoadmap(majorCode: string): Promise<MajorRoadmap> {
  return apiRequest<MajorRoadmap>(`/majors/${encodeURIComponent(majorCode)}/roadmap`)
}

// - POST /api/me/eligibility.
// - 1–100 unique IDs; preserve order. Backend checks completed-course grades, cumulative GPA,
//   earned units, class standing and major restrictions. unknown includes missing facts/reasons.
// - EligibilityRequest: {course_ids: string[]}.
// - EligibilityResponse: {results: Eligibility[]}.
export function checkEligibility(body: EligibilityRequest): Promise<EligibilityResponse> {
  return apiRequest<EligibilityResponse>('/me/eligibility', { method: 'POST', body })
}

// - GET /api/me/roadmap.
// - 409 PROFILE_INCOMPLETE needs profile editing; never guess a major.
// - StudentRoadmap: {major: Major, courses: StudentRoadmapEntry[], summary: ProgressSummary,
//   recommendations: string[]}.
export function getStudentRoadmap(): Promise<StudentRoadmap> {
  return apiRequest<StudentRoadmap>('/me/roadmap')
}
