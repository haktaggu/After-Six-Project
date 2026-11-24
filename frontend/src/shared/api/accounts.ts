import { apiRequest, queryString } from './client'
import type { CalendarCourse, CourseRecord, CourseRecordInput, CsrfResponse, LoginRequest, Page, PaginationQuery, ProfileResponse, ProfileUpdate, SessionResponse, SignupRequest } from './types'

const academicPlanChanged = 'oursjsu:academic-plan-changed'

export function subscribeToAcademicPlanChanges(onChange: () => void): () => void {
  if (typeof BroadcastChannel === 'undefined') {
    window.addEventListener(academicPlanChanged, onChange)
    return () => window.removeEventListener(academicPlanChanged, onChange)
  }
  const channel = new BroadcastChannel(academicPlanChanged)
  channel.addEventListener('message', onChange)
  return () => channel.close()
}

function notifyAcademicPlanChanged(): void {
  if (typeof BroadcastChannel === 'undefined') {
    window.dispatchEvent(new Event(academicPlanChanged))
    return
  }
  const channel = new BroadcastChannel(academicPlanChanged)
  channel.postMessage(null)
  channel.close()
}

export function fetchCsrf(): Promise<CsrfResponse> {
  return apiRequest<CsrfResponse>('/auth/csrf')
}

export function login(body: LoginRequest): Promise<SessionResponse> {
  return apiRequest<SessionResponse>('/auth/login', { method: 'POST', body })
}

export function signup(body: SignupRequest): Promise<SessionResponse> {
  return apiRequest<SessionResponse>('/auth/signup', { method: 'POST', body })
}

export function getSession(): Promise<SessionResponse> {
  return apiRequest<SessionResponse>('/auth/session')
}

export function logout(): Promise<void> {
  return apiRequest<void>('/auth/logout', { method: 'POST' })
}

export function getProfile(signal?: AbortSignal): Promise<ProfileResponse> {
  return apiRequest<ProfileResponse>('/me', { signal, cache: 'no-store' })
}

export async function updateProfile(body: ProfileUpdate): Promise<ProfileResponse> {
  const profile = await apiRequest<ProfileResponse>('/me', { method: 'PATCH', body })
  notifyAcademicPlanChanged()
  return profile
}

export function listCourseRecords(query: PaginationQuery = {}): Promise<Page<CourseRecord>> {
  return apiRequest<Page<CourseRecord>>('/me/course-records' + queryString(query))
}

export function getCourseCalendar(signal?: AbortSignal): Promise<CalendarCourse[]> {
  return apiRequest<CalendarCourse[]>('/me/course-calendar', { signal, cache: 'no-store' })
}

export async function putCourseRecord(courseId: string, body: CourseRecordInput): Promise<CourseRecord> {
  const record = await apiRequest<CourseRecord>(`/me/course-records/${encodeURIComponent(courseId)}`, { method: 'PUT', body })
  notifyAcademicPlanChanged()
  return record
}

export async function deleteCourseRecord(courseId: string): Promise<void> {
  await apiRequest<void>(`/me/course-records/${encodeURIComponent(courseId)}`, { method: 'DELETE' })
  notifyAcademicPlanChanged()
}
