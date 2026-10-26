import { apiRequest, queryString } from './client'
import type { EligibilityRequest, EligibilityResponse, Major, MajorRoadmap, Page, PaginationQuery, StudentRoadmap } from './types'

export function listMajors(query: PaginationQuery = {}): Promise<Page<Major>> {
  return apiRequest<Page<Major>>('/majors' + queryString(query))
}

export function getMajorRoadmap(majorCode: string): Promise<MajorRoadmap> {
  return apiRequest<MajorRoadmap>(`/majors/${encodeURIComponent(majorCode)}/roadmap`)
}

export function checkEligibility(body: EligibilityRequest): Promise<EligibilityResponse> {
  return apiRequest<EligibilityResponse>('/me/eligibility', { method: 'POST', body })
}

export function getStudentRoadmap(signal?: AbortSignal): Promise<StudentRoadmap> {
  return apiRequest<StudentRoadmap>('/me/roadmap', { signal })
}
