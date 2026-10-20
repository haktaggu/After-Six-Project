import { useState } from 'react'
import type { EligibilityResponse, PageProps, StudentRoadmap } from '../shared/api/types'
import './Roadmap.css'

// - shared/api/planning.getStudentRoadmap()->StudentRoadmap; 409 PROFILE_INCOMPLETE sends the
//   student to Dashboard to pick a major.
// - Group courses by term_order; render student_status, grade, progress and backend recommendations.
//   Refresh when profile/history changes, not only on initial mount.
// - Keep eligible/ineligible/unknown distinct; show reasons and missing_course_ids. Use backend
//   decisions rather than calculating another prerequisite engine.
// - Each entry has grade:Grade|null. Completed attempts with failing/unknown grades do not mean
//   earned course credit. Show backend reasons for grade, GPA, units, standing and major decisions.
// - StudentRoadmap: {major: Major, courses: StudentRoadmapEntry[], summary: ProgressSummary,
//   recommendations: string[]}.
async function loadRoadmap(): Promise<StudentRoadmap> {
  throw new Error('loadRoadmap is not implemented')
}

// - shared/api/planning.checkEligibility({course_ids:courseIds})->EligibilityResponse. 1–100
//   distinct IDs; batch larger roadmaps.
// - Results follow input order. Backend evaluates course grades and profile restrictions;
//   refresh when either changes. Show unknown only for missing/unsupported conditions and keep
//   its reasons visible. Group the roadmap by semester, not a graph.
// - EligibilityResponse: {results: Eligibility[]}.
async function refreshEligibility(courseIds: string[]): Promise<EligibilityResponse> {
  void [courseIds]
  throw new Error('refreshEligibility is not implemented')
}

const actions = { loadRoadmap, refreshEligibility }

// - Keep loading, empty and error states separate.
export default function Roadmap(props: PageProps = {}) {
  const [notice, setNotice] = useState('')
  void props
  return (
    <section className="roadmap-page">
      <h1>Roadmap</h1>
      <p>Degree planning will be built here.</p>
      <button type="button" disabled onClick={() => {
        void actions.loadRoadmap().catch((error: unknown) => setNotice(error instanceof Error ? error.message : 'Request failed'))
      }}>Refresh</button>
      {notice && <p role="alert">{notice}</p>}
    </section>
  )
}
