import { apiRequest, queryString } from './client'
import type { CourseRecord, CourseRecordInput, CsrfResponse, LoginRequest, Page, PaginationQuery, ProfileResponse, ProfileUpdate, SessionResponse } from './types'

export function fetchCsrf(): Promise<CsrfResponse> {
  return apiRequest<CsrfResponse>('/auth/csrf')
}

export function login(body: LoginRequest): Promise<SessionResponse> {
  return apiRequest<SessionResponse>('/auth/login', { method: 'POST', body })
}

export function getSession(): Promise<SessionResponse> {
  return apiRequest<SessionResponse>('/auth/session')
}

export function logout(): Promise<void> {
  return apiRequest<void>('/auth/logout', { method: 'POST' })
}

export function getProfile(signal?: AbortSignal): Promise<ProfileResponse> {
  return apiRequest<ProfileResponse>('/me', { signal })
}

export function updateProfile(body: ProfileUpdate): Promise<ProfileResponse> {
  return apiRequest<ProfileResponse>('/me', { method: 'PATCH', body })
}

export function listCourseRecords(query: PaginationQuery = {}): Promise<Page<CourseRecord>> {
  return apiRequest<Page<CourseRecord>>('/me/course-records' + queryString(query))
}

export function putCourseRecord(courseId: string, body: CourseRecordInput): Promise<CourseRecord> {
  return apiRequest<CourseRecord>(`/me/course-records/${encodeURIComponent(courseId)}`, { method: 'PUT', body })
}

export function deleteCourseRecord(courseId: string): Promise<void> {
  return apiRequest<void>(`/me/course-records/${encodeURIComponent(courseId)}`, { method: 'DELETE' })
}
