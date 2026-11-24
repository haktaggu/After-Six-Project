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
  recommendation_limit: number
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

export interface SignupRequest extends LoginRequest {
  full_name: string
}

export type ProfileUpdate = Partial<Pick<Profile, 'major_code' | 'recommendation_limit'>>

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
  earned_units?: number | null
  course_id: string
  status: CourseStatus
  grade: Grade | null
  term: string | null
  section_ids?: string[]
}

export interface CourseRecordInput {
  status: CourseStatus
  grade: Grade | null
  term: string | null
  section_ids?: string[]
  requirement_confirmations?: Record<string, boolean>
}

export type CalendarSection = Pick<Section, 'id' | 'section_number' | 'title' | 'meetings'>

export interface CalendarCourse {
  course_id: string
  title: string
  term: Term | null
  status: 'planned' | 'in_progress'
  sections: CalendarSection[]
}

export interface EligibilityRequest {
  course_ids: string[]
}

export interface RequirementConfirmation {
  id: string
  text: string
  confirmed: boolean
  satisfied?: boolean
}

export interface CourseRequirementCheck {
  course_id: string
  minimum_grade: string | null
  status: EligibilityStatus
  recorded_status: CourseStatus | null
  grade: Grade | null
  alternative: boolean
  concurrent?: boolean
}

export interface EnrollmentRequirement {
  kind: 'all' | 'any' | 'course' | 'confirmation' | 'check'
  text: string
  status: EligibilityStatus
  children: EnrollmentRequirement[]
  course?: CourseRequirementCheck | null
  confirmation?: RequirementConfirmation | null
}

export interface Eligibility {
  course_id: string
  status: EligibilityStatus
  reasons: string[]
  missing_course_ids: string[]
  additional_requirements?: RequirementConfirmation[]
  course_requirements?: CourseRequirementCheck[]
  requirements?: EnrollmentRequirement | null
  source_url?: string | null
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
  prerequisites?: { course_id: string; alternative: boolean }[]
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

export interface RoadmapRequirement {
  term_order: number
  label: string
  units: number | null
  flexible: boolean
}

export interface CourseSuggestion {
  course_id: string
  title: string
  status: 'ready' | 'after_current' | 'needs_review' | 'requirements_remaining'
  reason: string
}

export interface StudentRoadmap {
  major: Major
  courses: StudentRoadmapEntry[]
  requirements?: RoadmapRequirement[]
  summary: ProgressSummary
  recommendations: string[]
  suggestions: CourseSuggestion[]
  recommendation_limit: number
}

export interface WatchlistEntry {
  section: Section
  added_at: string
  eligibility: Eligibility
}

export interface NotificationPreferences {
  enabled: boolean
  available: boolean
  webhook_url?: string | null
}

export interface PreferencesUpdate {
  enabled: boolean
  webhook_url?: string | null
}

export interface Notification {
  id: string
  section_id: string
  event_type: 'section_opened'
  status: DeliveryStatus
  created_at: string
  sent_at: string | null
  is_read?: boolean
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
  target?: string
  onNavigate?: (page: Screen, target?: string) => void
  onSessionChanged?: () => void
  onSignIn?: (body: LoginRequest) => Promise<void>
  onSignUp?: (body: SignupRequest) => Promise<void>
}
