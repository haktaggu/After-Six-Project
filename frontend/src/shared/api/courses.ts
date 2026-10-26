import { apiRequest, queryString } from './client'
import type { CompareRequest, ComparisonResponse, Course, CourseQuery, Page, PaginationQuery, Section, SectionQuery, Term } from './types'

export function listTerms(query: PaginationQuery = {}): Promise<Page<Term>> {
  return apiRequest<Page<Term>>('/terms' + queryString(query))
}

export function listCourses(query: CourseQuery = {}): Promise<Page<Course>> {
  return apiRequest<Page<Course>>('/courses' + queryString(query))
}

export function getCourse(courseId: string): Promise<Course> {
  return apiRequest<Course>(`/courses/${encodeURIComponent(courseId)}`)
}

export function listSections(query: SectionQuery, signal?: AbortSignal): Promise<Page<Section>> {
  return apiRequest<Page<Section>>('/sections' + queryString(query), { signal })
}

export function getSection(sectionId: string): Promise<Section> {
  return apiRequest<Section>(`/sections/${encodeURIComponent(sectionId)}`)
}

export function compareSections(body: CompareRequest): Promise<ComparisonResponse> {
  return apiRequest<ComparisonResponse>('/sections/compare', { method: 'POST', body })
}
