import type { Page as Screen } from '../../app/navigation'

export type CourseStatus = 'completed' | 'in_progress' | 'planned'
export type StudentCourseStatus = 'completed' | 'in_progress' | 'planned' | 'not_started'
export type Standing = 'freshman' | 'sophomore' | 'junior' | 'senior' | 'graduate' | 'unspecified'
export type Grade = 'A+' | 'A' | 'A-' | 'B+' | 'B' | 'B-' | 'C+' | 'C' | 'C-' | 'D+' | 'D' | 'D-' | 'F' | 'CR' | 'NC' | 'WU' | 'IC' | 'W' | 'I' | 'RP' | 'RD' | 'AU'
export type EligibilityStatus = 'eligible' | 'ineligible' | 'unknown'
export type Availability = 'open' | 'closed' | 'unknown'
export type Weekday = 'mon' | 'tue' | 'wed' | 'thu' | 'fri' | 'sat' | 'sun'
export type DeliveryStatus = 'pending' | 'sent' | 'failed'

export interface Page<T> { items: T[]; total: number; limit: number; offset: number }

export interface FieldError {
  path: string
  message: string
}

export interface ApiError {
  code: string
  message: string
  fields: FieldError[]
}

export interface ErrorResponse {
  error: ApiError
}

export interface User {
  id: string
  email: string
  full_name: string
  created_at: string
}

export interface Profile {
  major_code: string | null
  standing: Standing
  gpa: number | null
  earned_units: number | null
}

export interface CsrfResponse {
  csrf_token: string
}

export interface SessionResponse {
  user: User
  csrf_token: string
  expires_at: string
}

export interface ProfileResponse {
  user: User
  profile: Profile
}

export interface LoginRequest {
  email: string
  password: string
}

export type ProfileUpdate = Profile

export interface Term {
  id: string
  name: string
}

export interface Course {
  id: string
  subject: string
  catalog_number: string
  title: string
  description: string | null
  units_min: number | null
  units_max: number | null
  prerequisite_text: string | null
  corequisite_text: string | null
  restrictions_text: string | null
  catalog_url: string | null
}

export interface Meeting {
  days: Weekday[]
  start_time: string | null
  end_time: string | null
  location: string | null
  is_tba: boolean
}

export interface Instructor {
  name: string
}

export interface Section {
  id: string
  term: string
  class_number: string
  section_number: string
  course: Course
  title: string
  mode: string
  units: number | null
  open_seats: number | null
  availability: Availability
  meetings: Meeting[]
  instructors: Instructor[]
  notes: string | null
  source_url: string
  last_checked_at: string | null
  is_stale: boolean
}

export interface CompareRequest {
  section_ids: string[]
}

export interface ComparisonResponse {
  sections: Section[]
}

export interface Major {
  major_code: string
  title: string
  degree_type: string
  description: string | null
}

export interface CourseRecord {
  course_id: string
  status: CourseStatus
  grade: Grade | null
  term: string | null
}

export interface CourseRecordInput {
  status: CourseStatus
  grade: Grade | null
  term: string | null
}

export interface EligibilityRequest {
  course_ids: string[]
}

export interface Eligibility {
  course_id: string
  status: EligibilityStatus
  reasons: string[]
  missing_course_ids: string[]
}

export interface EligibilityResponse {
  results: Eligibility[]
}

export interface RoadmapEntry {
  course: Course
  term_order: number
  is_required: boolean
}

export interface StudentRoadmapEntry {
  course: Course
  term_order: number
  is_required: boolean
  student_status: StudentCourseStatus
  grade: Grade | null
  eligibility: Eligibility
}

export interface ProgressSummary {
  completed_courses: number
  total_required_courses: number
  completion_percent: number
}

export interface MajorRoadmap {
  major: Major
  courses: RoadmapEntry[]
}

export interface StudentRoadmap {
  major: Major
  courses: StudentRoadmapEntry[]
  summary: ProgressSummary
  recommendations: string[]
}

export interface WatchlistEntry {
  section: Section
  added_at: string
  eligibility: Eligibility
}

export interface NotificationPreferences {
  enabled: boolean
  available: boolean
}

export interface PreferencesUpdate {
  enabled: boolean
}

export interface Notification {
  id: string
  section_id: string
  event_type: 'section_opened'
  status: DeliveryStatus
  created_at: string
  sent_at: string | null
}

export interface PaginationQuery {
  limit?: number
  offset?: number
}

export interface CourseQuery {
  limit?: number
  offset?: number
  q?: string
}

export interface SectionQuery {
  limit?: number
  offset?: number
  q?: string
  term: string
  course_id?: string
}

export interface WatchlistQuery {
  limit?: number
  offset?: number
  term?: string
}

export type SessionState =
  | { status: 'loading'; session: null; error: null }
  | { status: 'anonymous'; session: null; error: null }
  | { status: 'authenticated'; session: SessionResponse; error: null }
  | { status: 'unavailable'; session: null; error: string }

export interface PageProps {
  onNavigate?: (page: Screen) => void
  onSessionChanged?: () => void
  onSignIn?: (body: LoginRequest) => Promise<void>
}
