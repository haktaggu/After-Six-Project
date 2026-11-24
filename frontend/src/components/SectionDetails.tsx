import type { Eligibility, PageProps, Section } from '../shared/api/types'
import { meetingTimeLabel } from '../shared/meetingTime'

const statusNotes: Record<string, string> = {
  eligible: 'You meet the prerequisite requirements for this course.',
  ineligible: 'You currently do not meet one or more prerequisite requirements.',
  unknown: 'Some requirements need confirmation in the course record.',
}

export function EligibilityDetails({ value, onNavigate }: { value: Eligibility; onNavigate?: PageProps['onNavigate'] }) {
  const note = statusNotes[value.status]
  return <details className="eligibility">
    <summary>Enrollment requirements</summary>
    <p className="eligibility-status-note">{note}</p>
    {value.reasons.length ? <ul>{value.reasons.map((reason, index) => <li key={index}>{reason}</li>)}</ul> : <p>No prerequisite conditions apply.</p>}
    {value.missing_course_ids.length > 0 && <p className="missing-credit">Missing credit: {value.missing_course_ids.join(', ')}</p>}
    {onNavigate && <button type="button" onClick={() => onNavigate('Add Course', value.course_id)}>Edit course requirements</button>}
  </details>
}

export default function SectionDetails({ section: s, showNotes = true }: { section: Section; showNotes?: boolean }) {
  return <dl className="section-facts">
    <div><dt>Class number</dt><dd>{s.class_number} · {s.mode}</dd></div>
    <div><dt>Instructor</dt><dd>{s.instructors.map(i => i.name).join(', ') || 'Not listed'}</dd></div>
    <div><dt>Meetings</dt><dd>{s.meetings.length ? s.meetings.map((m, i) => <span className="meeting" key={i}>
      {m.days.map(d => d[0].toUpperCase() + d.slice(1)).join(', ') || 'Days TBA'} · {meetingTimeLabel(m)} · {m.location || 'Location TBA'}
    </span>) : 'Not listed'}</dd></div>
    <div><dt>Units</dt><dd>{s.units ?? 'Unknown'}</dd></div>
    <div><dt>Availability</dt><dd><span className={`status ${s.availability}`}>{s.availability}</span> {s.open_seats === null ? 'Seat count unknown' : `${s.open_seats} open seat${s.open_seats === 1 ? '' : 's'}`}</dd></div>
    {showNotes && s.notes && <div><dt>Notes</dt><dd>{s.notes}</dd></div>}
  </dl>
}
