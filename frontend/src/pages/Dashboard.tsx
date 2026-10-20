import { useState } from 'react'
import type { CourseRecord, CourseRecordInput, Major, Page, PageProps, ProfileResponse, ProfileUpdate, Term } from '../shared/api/types'

interface DashboardData {
  profile: ProfileResponse
  majors: Page<Major>
  terms: Page<Term>
  records: Page<CourseRecord>
}

// - shared/api/accounts.getProfile()->{user:{id,email,full_name,created_at},
//   profile:{major_code,standing,gpa,earned_units}};
//   listCourseRecords(query)->Page<CourseRecord>. shared/api/planning.listMajors(query) and
//   shared/api/courses.listTerms(query) return paged lookup lists.
// - Page fields: items,total,limit,offset. Query {limit?:number,offset?:number} defaults 25/0.
// - Show account name/email read-only. Edit major, standing, GPA, earned units and course history;
//   GPA/units are cumulative student inputs, not totals calculated from the demo courses. Fetch lookup
//   pages when needed, and provide paging for history. Cancel obsolete requests and show errors.
async function loadDashboard(): Promise<DashboardData> {
  throw new Error('loadDashboard is not implemented')
}

// - shared/api/accounts.updateProfile({major_code,standing,gpa,earned_units}) -> ProfileResponse.
// - Send all four fields. major_code must exist or be null. Standing is freshman/sophomore/
//   junior/senior/graduate/unspecified; unspecified means unknown class standing.
// - GPA accepts finite numbers 0..4 or null; earned_units accepts nonnegative integers or null.
//   Blank GPA/units become null, not zero. Do not infer standing from units or calculate GPA.
// - Keep entered values on failure. On success refresh profile, roadmap and watchlist eligibility.
async function saveProfile(body: ProfileUpdate): Promise<ProfileResponse> {
  void body
  throw new Error('saveProfile is not implemented')
}

// - shared/api/accounts.putCourseRecord(courseId,{status,grade,term})->CourseRecord, 201 new/200 update.
// - status is completed/in_progress/planned; term is an imported ID or null. Grade is uppercase
//   A+,A,A-,B+,B,B-,C+,C,C-,D+,D,D-,F,CR,NC,WU,IC,W,I,RP,RD,AU or null when unknown.
//   Show the grade input only for completed attempts; changing to in_progress/planned clears it.
//   A completed attempt with a failing grade must not be shown as a satisfied prerequisite.
// - One row per course. After success refresh history and invalidate roadmap/eligibility data;
//   grade thresholds and profile restrictions affect eligibility. Keep values on failure.
async function saveCourseRecord(courseId: string, body: CourseRecordInput): Promise<CourseRecord> {
  void [courseId, body]
  throw new Error('saveCourseRecord is not implemented')
}

// - shared/api/accounts.deleteCourseRecord(courseId)->void; repeated delete still returns 204.
// - Reload history, step back if the last page emptied, and invalidate roadmap after success.
async function removeCourseRecord(courseId: string): Promise<void> {
  void courseId
  throw new Error('removeCourseRecord is not implemented')
}

const actions = { loadDashboard, saveProfile, saveCourseRecord, removeCourseRecord }

export default function Dashboard(props: PageProps = {}) {
  const [notice, setNotice] = useState('')
  void props
  return <section>
    <h1>Dashboard</h1>
    <p>Student overview will be built here.</p>
    <button type="button" disabled onClick={() => {
      void actions.loadDashboard().catch((error: unknown) => setNotice(error instanceof Error ? error.message : 'Request failed'))
    }}>Refresh</button>
    {notice && <p role="alert">{notice}</p>}
  </section>
}
