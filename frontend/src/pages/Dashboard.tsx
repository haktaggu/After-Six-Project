import { useCallback, useEffect } from 'react'
import { getProfile, subscribeToAcademicPlanChanges } from '../shared/api/accounts'
import { getStudentRoadmap } from '../shared/api/planning'
import { listWatchlist } from '../shared/api/watchlist'
import { ApiClientError } from '../shared/api/client'
import { useLoad } from '../shared/hooks/useLoad'
import type { PageProps } from '../shared/api/types'
import { ErrorNotice } from '../components/Feedback'
import CourseSuggestions from '../components/CourseSuggestions'
import ClassSchedule from '../components/ClassSchedule'
import './Dashboard.css'

export default function Dashboard({ onNavigate }: PageProps) {
  const { data: profile, error: profileError, loading: profileLoading, reload: reloadProfile } = useLoad(getProfile)
  const academics = profile?.profile
  const roadmap = useLoad(getStudentRoadmap)
  const { reload: reloadRoadmap } = roadmap
  const watchlist = useLoad(useCallback((signal: AbortSignal) => listWatchlist({ limit: 3 }, signal), []))
  const progress = roadmap.data?.summary
  const needsMajor = roadmap.error instanceof ApiClientError && roadmap.error.code === 'PROFILE_INCOMPLETE'

  useEffect(() => subscribeToAcademicPlanChanges(() => {
    reloadProfile()
    reloadRoadmap()
  }), [reloadProfile, reloadRoadmap])

  return (
    <section className="dashboard">
      <div className="page-heading">
        <h1>Dashboard</h1>
        <button onClick={() => onNavigate?.('Add Course')}>Add a course</button>
      </div>
      <div className="dashboard-overview">
      <section aria-labelledby="academic-summary">
        <h2 id="academic-summary">Academic summary</h2>
        <ErrorNotice error={profileError} />
        {profileLoading && <p role="status">Loading academic summary…</p>}
        {academics && (
          <dl className="academic-summary">
            <div><dt>Cumulative GPA</dt><dd>{academics.gpa?.toFixed(2) ?? 'Unknown'}</dd></div>
            <div><dt>Earned units</dt><dd>{academics.earned_units ?? 'Unknown'}</dd></div>
            <div><dt>Class standing</dt><dd className="class-standing">{academics.standing === 'unspecified' ? 'Unknown' : academics.standing}</dd></div>
          </dl>
        )}
        <button onClick={() => onNavigate?.('Course History')}>Course history</button>
      </section>
      <section aria-labelledby="degree-progress">
        <h2 id="degree-progress">Degree progress</h2>
        {roadmap.loading && <p role="status">Loading degree progress…</p>}
        {needsMajor ? <p>Choose your major to see your degree progress.</p> : <ErrorNotice error={roadmap.error} />}
        {progress && roadmap.data && (
          <div className="dashboard-progress-summary">
            <p>{roadmap.data.major.title} {roadmap.data.major.degree_type}</p>
            <p className="dashboard-progress-count">
              <span>{progress.completed_courses} of {progress.total_required_courses} required courses completed</span>
              <strong>{progress.completion_percent.toFixed(0)}%</strong>
            </p>
            <progress aria-label="Required courses completed" max={100} value={progress.completion_percent} />
          </div>
        )}
        <button onClick={() => onNavigate?.(needsMajor ? 'Profile' : 'Roadmap')}>
          {needsMajor ? 'Choose your major' : 'Open roadmap'}
        </button>
      </section>
      </div>
      <ClassSchedule onNavigate={onNavigate} />
      <div className="dashboard-activity">
        <section>
          <h2>Course suggestions</h2>
          {roadmap.loading && <p role="status">Loading suggested courses…</p>}
          {!roadmap.loading && !roadmap.data && <p>{needsMajor ? 'Choose your major to see suggested courses.' : 'Suggested courses are unavailable.'}</p>}
          {roadmap.data && <CourseSuggestions
            suggestions={roadmap.data.suggestions}
            target={roadmap.data.recommendation_limit}
            onSelect={id => onNavigate?.(roadmap.data?.courses.some(entry => entry.course.id === id) ? 'Roadmap' : 'Search', id)}
          />}
          <button onClick={() => onNavigate?.('Roadmap')}>See all on roadmap</button>
        </section>
        <section>
          <h2>Watched sections{watchlist.data && ` (${watchlist.data.total})`}</h2>
          <ErrorNotice error={watchlist.error} />
          {watchlist.loading && <p role="status">Loading watched sections…</p>}
          {watchlist.data && (watchlist.data.items.length > 0 ? (
            <ul>{watchlist.data.items.map(({ section }) => (
              <li key={section.id}>
                <button className="dashboard-item" onClick={() => onNavigate?.('Watchlist', section.id)}>
                  <strong>{section.course.id}</strong> · Section {section.section_number} · {section.open_seats === null ? 'Seats unknown' : `${section.open_seats} open`}
                </button>
              </li>
            ))}</ul>
          ) : <p>You’re currently watching zero sections.</p>)}
          <button onClick={() => onNavigate?.(watchlist.data?.total === 0 ? 'Search' : 'Watchlist')}>
            {watchlist.data?.total === 0 ? 'Find a section' : 'Open watchlist'}
          </button>
        </section>
      </div>
    </section>
  )
}
