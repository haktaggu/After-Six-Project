import { useCallback } from 'react'
import { listSections } from '../shared/api/courses'
import { allPages } from '../shared/api/lookups'
import { useLoad } from '../shared/hooks/useLoad'
import { meetingTimeLabel } from '../shared/meetingTime'
import { ErrorNotice } from './Feedback'

export default function RecordSectionChoices({ courseId, term, sectionIds, onChange, disabled }: {
  courseId: string
  term: string
  sectionIds: string[]
  onChange: (ids: string[]) => void
  disabled: boolean
}) {
  const load = useCallback((signal: AbortSignal) =>
    allPages(query => listSections({ ...query, term, course_id: courseId }, signal)), [courseId, term])
  const { data, loading, error, reload } = useLoad(load)

  return (
    <div className="record-sections-body">
      <ErrorNotice error={error} />
      {Boolean(error) && <button type="button" onClick={reload}>Retry sections</button>}
      {loading && <p role="status">Loading sections…</p>}
      {data?.length === 0 && <p className="help">No sections have been imported for this course and term.</p>}
      {data && data.length > 0 && (
        <fieldset disabled={disabled}>
          <legend>Sections to show on your calendar</legend>
          <p className="help">Select your lecture and any labs or other meetings that apply.</p>
          {data.map(section => (
            <label className="record-section-choice" key={section.id}>
              <input
                type="checkbox"
                checked={sectionIds.includes(section.id)}
                onChange={event => onChange(event.target.checked
                  ? [...sectionIds, section.id] : sectionIds.filter(id => id !== section.id))}
              />
              <span>
                <strong>{section.title} · Section {section.section_number}</strong>
                <span className="help">Class {section.class_number} · {section.mode}</span>
                {section.meetings.map((meeting, index) => (
                  <span className="help" key={index}>
                    {meeting.days.map(day => day[0].toUpperCase() + day.slice(1)).join(', ') || 'Days TBA'}
                    {' · '}{meetingTimeLabel(meeting)}{meeting.location ? ` · ${meeting.location}` : ''}
                  </span>
                ))}
              </span>
            </label>
          ))}
        </fieldset>
      )}
    </div>
  )
}
