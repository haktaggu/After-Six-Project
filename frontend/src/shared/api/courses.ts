import { apiRequest, queryString } from './client'
import type { CompareRequest, ComparisonResponse, Course, CourseQuery, Page, PaginationQuery, Section, SectionQuery, Term } from './types'

// - GET /api/terms.
// - Sorted by id.
// - PaginationQuery: {limit?: number, offset?: number}.
// - Term: {id: string, name: string}.
export function listTerms(query: PaginationQuery = {}): Promise<Page<Term>> {
  return apiRequest<Page<Term>>('/terms' + queryString(query))
}

// - GET /api/courses.
// - q searches code/title, ignoring case; retain pagination when changing pages.
// - CourseQuery: {limit?: number, offset?: number, q?: string}.
// - Course: {id: string, subject: string, catalog_number: string, title: string, description:
//   string | null, units_min: number | null, units_max: number | null, prerequisite_text: string |
//   null, corequisite_text: string | null, restrictions_text: string | null, catalog_url: string |
//   null}.
export function listCourses(query: CourseQuery = {}): Promise<Page<Course>> {
  return apiRequest<Page<Course>>('/courses' + queryString(query))
}

// - GET /api/courses/{courseId}.
// - 404 for missing course; retain all null fields.
export function getCourse(courseId: string): Promise<Course> {
  return apiRequest<Course>(`/courses/${encodeURIComponent(courseId)}`)
}

// - GET /api/sections.
// - term is required. q and course_id must both match when supplied. Sort by id.
// - SectionQuery: {limit?: number, offset?: number, q?: string, term: string, course_id?: string}.
// - Section: {id: string, term: string, class_number: string, section_number: string, course:
//   Course, title: string, mode: string, units: number | null, open_seats: number | null,
//   availability: Availability, meetings: Meeting[], instructors: Instructor[], notes: string |
//   null, source_url: string, last_checked_at: string | null, is_stale: boolean}.
export function listSections(query: SectionQuery): Promise<Page<Section>> {
  return apiRequest<Page<Section>>('/sections' + queryString(query))
}

// - GET /api/sections/{sectionId}.
// - Nested course/meetings/instructors; missing timestamps are stale.
export function getSection(sectionId: string): Promise<Section> {
  return apiRequest<Section>(`/sections/${encodeURIComponent(sectionId)}`)
}

// - POST /api/sections/compare.
// - Exactly two unique same-term sections, preserving requested order. Missing section 404, invalid
//   selection 422.
// - CompareRequest: {section_ids: string[]}.
// - ComparisonResponse: {sections: Section[]}.
export function compareSections(body: CompareRequest): Promise<ComparisonResponse> {
  return apiRequest<ComparisonResponse>('/sections/compare', { method: 'POST', body })
}
