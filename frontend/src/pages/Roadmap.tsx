import { useEffect, useId, useMemo, useRef, useState } from 'react'
import { subscribeToAcademicPlanChanges } from '../shared/api/accounts'
import { getStudentRoadmap } from '../shared/api/planning'
import { ApiClientError } from '../shared/api/client'
import { useLoad } from '../shared/hooks/useLoad'
import type { CourseSuggestion, PageProps, RoadmapRequirement, StudentRoadmapEntry } from '../shared/api/types'
import { ErrorNotice } from '../components/Feedback'
import CourseSuggestionStatus from '../components/CourseSuggestionStatus'
import CourseSuggestions from '../components/CourseSuggestions'
import RoadmapGraph from '../components/RoadmapGraph'
import './Roadmap.css'

export default function Roadmap({ onNavigate, target }: PageProps) {
  const { data, error, loading, reload } = useLoad(getStudentRoadmap)
  const requirements = data?.requirements ?? []
  const terms = useMemo(() => [...new Set(data?.courses.map(c => c.term_order))].sort((a, b) => a - b), [data])
  const suggestions = useMemo(() => new Map(data?.suggestions.map(suggestion => [suggestion.course_id, suggestion])), [data])
  const outsideSuggestions = data?.suggestions.filter(suggestion =>
    !data.courses.some(entry => entry.course.id === suggestion.course_id),
  ) ?? []
  const [view, setView] = useState<'graph' | 'list'>(() =>
    window.matchMedia?.('(max-width: 700px)').matches ? 'list' : 'graph',
  )
  const [showAll, setShowAll] = useState(false)
  const [selectedId, setSelectedId] = useState<string | null>(target ?? null)
  const [detailsOpen, setDetailsOpen] = useState(true)
  const selected = data?.courses.find(entry => entry.course.id === selectedId)
  const detailsId = useId()
  const selectionRef = useRef<HTMLElement>(null)
  const pendingFocus = useRef<'course' | 'details' | null>(target ? 'course' : null)

  useEffect(() => subscribeToAcademicPlanChanges(reload), [reload])

  useEffect(() => {
    if (!data || !selectedId || !pendingFocus.current) return
    const course = document.getElementById(`${view}-course-${selectedId}`)
    if (pendingFocus.current === 'details') {
      const scroll = course?.closest<HTMLElement>('.roadmap-scroll')
      if (course && scroll) {
        const card = course.getBoundingClientRect()
        const viewport = scroll.getBoundingClientRect()
        if (card.left < viewport.left || card.right > viewport.right) {
          scroll.scrollLeft += (card.left + card.right - viewport.left - viewport.right) / 2
        }
      }
      selectionRef.current?.focus({ preventScroll: true })
    } else {
      course?.focus()
    }
    pendingFocus.current = null
  }, [data, selectedId, view])

  function jumpToCourse(id: string) {
    if (id === selectedId) {
      document.getElementById(`${view}-course-${id}`)?.focus()
      return
    }
    pendingFocus.current = 'course'
    setDetailsOpen(true)
    setSelectedId(id)
  }

  function closeDetails() {
    document.getElementById(`${view}-course-${selectedId}`)?.focus()
    setSelectedId(null)
  }

  function selectGraphCourse(id: string) {
    if (id === selectedId) {
      closeDetails()
      return
    }
    pendingFocus.current = 'details'
    setDetailsOpen(true)
    setSelectedId(id)
  }

  return <section className="roadmap-page">
    <div className="page-heading"><h1>Your degree roadmap</h1><button disabled={loading} onClick={reload}>Refresh roadmap</button></div>
    <ErrorNotice error={error} />{error instanceof ApiClientError && error.code === 'PROFILE_INCOMPLETE' && <button className="primary" onClick={() => onNavigate?.('Profile')}>Complete profile</button>}
    {loading && <p role="status">Loading your roadmap…</p>}
    {data && <>
      <div className="roadmap-progress">
        <strong>{data.major.title} {data.major.degree_type}</strong>
        <span>{data.summary.completed_courses} of {data.summary.total_required_courses} required courses completed</span>
        <progress aria-label="Required courses completed" max="100" value={data.summary.completion_percent} />
      </div>
      {!data.courses.length && <p className="empty">No catalog courses loaded.</p>}
      {data.courses.length > 0 && <section className="roadmap-explorer">
        <div className="roadmap-toolbar">
          <div className="roadmap-view-buttons" role="group" aria-label="Roadmap view">
            <button type="button" aria-pressed={view === 'graph'} onClick={() => setView('graph')}>Dependency graph</button>
            <button type="button" aria-pressed={view === 'list'} onClick={() => setView('list')}>Semester list</button>
          </div>
          {view === 'graph' && (
            <label className="roadmap-connection-toggle">
              <input type="checkbox" checked={showAll} onChange={event => setShowAll(event.target.checked)} />
              Show all connections
            </label>
          )}
        </div>
        <p className="help roadmap-suggestion-summary" aria-live="polite">
          {suggestions.size === 0
            ? 'No remaining courses to suggest for your degree plan.'
            : suggestions.size < data.recommendation_limit
              ? `Showing ${suggestions.size} of ${data.recommendation_limit} requested course suggestions.`
              : `${suggestions.size} suggested ${suggestions.size === 1 ? 'course' : 'courses'} marked below.`}
        </p>
        {outsideSuggestions.length > 0 && (
          <section className="roadmap-external-suggestions" aria-label="Suggested courses outside the roadmap">
            <h3>Suggested courses outside the roadmap</h3>
            <CourseSuggestions
              suggestions={outsideSuggestions}
              target={outsideSuggestions.length}
              onSelect={id => onNavigate?.('Search', id)}
            />
          </section>
        )}
        {view === 'graph' && (
          <>
            <div className="roadmap-graph-guide">
              <p className="help">Select a course to see what it requires and which courses depend on it.</p>
              <ul className="roadmap-legend">
                <li><span aria-hidden="true" /> Prerequisite</li>
                <li><span className="is-alternative" aria-hidden="true" /> Alternative</li>
              </ul>
            </div>
            <div className="roadmap-graph-workspace">
              <RoadmapGraph
                courses={data.courses}
                terms={terms}
                suggestions={suggestions}
                selectedId={selected?.course.id ?? null}
                showAll={showAll}
                onSelect={selectGraphCourse}
              />
              {selected && (
                <section
                  className="roadmap-selection"
                  key={selected.course.id}
                  aria-label={`Selected course ${selected.course.id}`}
                  ref={selectionRef}
                  tabIndex={-1}
                  onKeyDown={event => { if (event.key === 'Escape') closeDetails() }}
                >
                  <div className="roadmap-selection-heading">
                    <div>
                      <CourseHeading entry={selected} />
                      {detailsOpen && <p>{selected.course.title}</p>}
                    </div>
                    <div className="roadmap-selection-actions">
                      <CourseRecordButton entry={selected} onNavigate={onNavigate} />
                      <button
                        type="button"
                        aria-controls={detailsId}
                        aria-expanded={detailsOpen}
                        onClick={() => setDetailsOpen(open => !open)}
                      >
                        {detailsOpen ? 'Hide details' : 'Show details'}
                      </button>
                      <button type="button" onClick={closeDetails}>Clear selection</button>
                    </div>
                  </div>
                  <div id={detailsId} className="roadmap-selection-body" hidden={!detailsOpen}>
                    <CourseSuggestionNote suggestion={suggestions.get(selected.course.id)} />
                    <CourseConnections entry={selected} courses={data.courses} onSelect={jumpToCourse} onNavigate={onNavigate} />
                    <CourseFacts entry={selected} onNavigate={onNavigate} />
                  </div>
                </section>
              )}
            </div>
          </>
        )}
        {view === 'list' && (
          <div className="semester-list">
            {terms.map(term => (
              <section className="semester" key={term}>
                <h2>Semester {term}</h2>
                <div>
                  {data.courses.filter(entry => entry.term_order === term).map(entry => (
                    <article className="roadmap-course" key={entry.course.id}>
                      <CourseHeading entry={entry} />
                      <p>{entry.course.title}</p>
                      <CourseSuggestionNote suggestion={suggestions.get(entry.course.id)} />
                      <CourseFacts entry={entry} onNavigate={onNavigate} />
                      <div className="actions roadmap-course-actions">
                        <CourseRecordButton entry={entry} onNavigate={onNavigate} />
                        <button
                          type="button"
                          className="roadmap-list-connections"
                          id={`list-course-${entry.course.id}`}
                          aria-label={`Course connections for ${entry.course.id}`}
                          aria-expanded={selectedId === entry.course.id}
                          onClick={() => selectedId === entry.course.id ? closeDetails() : setSelectedId(entry.course.id)}
                        >
                          Course connections
                        </button>
                      </div>
                      {selectedId === entry.course.id && (
                        <CourseConnections entry={entry} courses={data.courses} onSelect={jumpToCourse} onNavigate={onNavigate} />
                      )}
                    </article>
                  ))}
                  <SemesterRequirements items={requirements.filter(requirement => requirement.term_order === term)} />
                </div>
              </section>
            ))}
          </div>
        )}
      </section>}
      {view === 'graph' && requirements.length > 0 && (
        <section className="roadmap-requirements">
          <h2>GE, electives, and milestones</h2>
          {terms.map(term => {
            const items = requirements.filter(requirement => requirement.term_order === term)
            if (items.length === 0) return null
            return (
              <div key={term}>
                <h3>Semester {term}</h3>
                <SemesterRequirements items={items} />
              </div>
            )
          })}
        </section>
      )}
    </>}
  </section>
}

function CourseRecordButton({ entry, onNavigate }: { entry: StudentRoadmapEntry; onNavigate: PageProps['onNavigate'] }) {
  if (!onNavigate) return null
  return <button type="button" onClick={() => onNavigate('Add Course', entry.course.id)}>
    {entry.student_status === 'not_started' ? 'Add course' : 'Edit course record'}
  </button>
}

function CourseSuggestionNote({ suggestion }: { suggestion: CourseSuggestion | undefined }) {
  if (!suggestion) return null
  return <div className="course-suggestion-detail roadmap-suggestion-note">
    <CourseSuggestionStatus status={suggestion.status} />
    <p className="help">{suggestion.reason}</p>
  </div>
}

function CourseHeading({ entry }: { entry: StudentRoadmapEntry }) {
  return (
    <div className="section-heading">
      <h3>{entry.course.id}</h3>
      <span className={`status ${entry.student_status}`}>
        {entry.student_status.replaceAll('_', ' ')}{entry.grade ? ` · ${entry.grade}` : ''}
      </span>
    </div>
  )
}

function CourseFacts({ entry, onNavigate }: { entry: StudentRoadmapEntry; onNavigate: PageProps['onNavigate'] }) {
  const status = entry.eligibility.status
  return (
    <>
      <p className="help">{entry.is_required ? 'Required' : 'Optional'} · {entry.course.units_min ?? 'Unknown'} units</p>
      <div className="roadmap-requirements-summary">
        <p className="help">{status === 'eligible' ? 'Enrollment requirements met.' :
          status === 'ineligible' ? 'Course prerequisites remaining.' : 'Additional requirements to confirm.'}</p>
        {status !== 'eligible' && onNavigate && <button
          type="button"
          className="roadmap-course-link"
          onClick={() => onNavigate('Add Course', entry.course.id)}
        >Edit requirements</button>}
      </div>
    </>
  )
}

function CourseConnections({ entry, courses, onSelect, onNavigate }: {
  entry: StudentRoadmapEntry
  courses: StudentRoadmapEntry[]
  onSelect: (id: string) => void
  onNavigate: PageProps['onNavigate']
}) {
  const labelId = useId()
  const { id, prerequisite_text, corequisite_text } = entry.course
  const coursesById = new Map(courses.map(item => [item.course.id, item.course]))
  const prerequisites = (entry.prerequisites ?? []).filter(link => link.course_id !== id)
  const dependents = courses.flatMap(item => {
    const link = item.prerequisites?.find(link => link.course_id === id)
    return link && item.course.id !== id ? [{ course_id: item.course.id, alternative: link.alternative }] : []
  })
  const groups = [
    { key: 'prerequisites', title: 'Prerequisites', items: prerequisites, empty: 'No course prerequisites listed.' },
    { key: 'dependents', title: 'Courses that depend on this', items: dependents, empty: 'No dependent courses on this roadmap.' },
  ]

  return (
    <div className="roadmap-course-connections">
      <div className="roadmap-connection-groups">
        {groups.map(({ key, title, items, empty }) => (
          <div key={key}>
            <h4>{title}</h4>
            {items.length ? (
              <ul>
                {items.map(({ course_id, alternative }) => {
                  const course = coursesById.get(course_id)
                  const alternativeId = alternative ? `${labelId}-${key}-${course_id}` : undefined
                  return (
                    <li key={course_id}>
                      {course ? (
                        <button
                          type="button"
                          className="roadmap-course-link"
                          aria-describedby={alternativeId}
                          onClick={() => onSelect(course_id)}
                        >
                          <strong>{course_id}</strong> {course.title}
                        </button>
                      ) : <span><strong>{course_id}</strong> · Outside this roadmap</span>}
                      {alternative && <span id={alternativeId} className="roadmap-alternative">Alternative</span>}
                    </li>
                  )
                })}
              </ul>
            ) : <p className="help">{empty}</p>}
          </div>
        ))}
      </div>
      <details className="roadmap-catalog-rules">
        <summary>Catalog requirements</summary>
        <p>Prerequisites: {prerequisite_text ?? 'No prerequisite text in the catalog.'}</p>
        {corequisite_text && <p>Corequisites: {corequisite_text}</p>}
      </details>
      {onNavigate && (
        <button type="button" onClick={() => onNavigate('Search', id)}>Search for {id} sections</button>
      )}
    </div>
  )
}

function SemesterRequirements({ items }: { items: RoadmapRequirement[] }) {
  if (!items.length) return null
  return (
    <ul>{items.map(requirement => (
      <li key={requirement.label}>
        {requirement.label}
        {requirement.units !== null && ` · ${requirement.units} units`}
        {requirement.flexible && ' · Flexible semester'}
      </li>
    ))}</ul>
  )
}
