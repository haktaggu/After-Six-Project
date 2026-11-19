import type { Eligibility, Section } from '../shared/api/types'

const statusNotes: Record<string, string> = {
  eligible: 'You meet the prerequisite requirements for this course.',
  ineligible: 'You currently do not meet one or more prerequisite requirements.',
  unknown: 'Prerequisite eligibility requires verification (department consent, placement exam, or concurrent enrollment).',
}

export function EligibilityDetails({ value }: { value: Eligibility }) {
  const note = statusNotes[value.status]
  return <details className="eligibility">
    <summary><span className={`status ${value.status}`}>{value.status}</span> Prerequisite details</summary>
    {note && <p className="eligibility-status-note">{note}</p>}
    {value.reasons.length ? <ul>{value.reasons.map((r, i) => <li key={i}>{r}</li>)}</ul> : <p>No prerequisite conditions apply.</p>}
    {value.missing_course_ids.length > 0 && <p className="missing-credit">Missing credit: {value.missing_course_ids.join(', ')}</p>}
  </details>
}

function formatTime(time: string): string {
  if (/[ap]m/i.test(time)) return time.trim()
  const [h, m] = time.split(':')
  const hour = parseInt(h, 10)
  if (isNaN(hour)) return time
  const minute = m ?? '00'
  const ampm = hour >= 12 ? 'PM' : 'AM'
  const hour12 = hour % 12 === 0 ? 12 : hour % 12
  return `${hour12}:${minute} ${ampm}`
}

export default function SectionDetails({ section: s, showNotes = true }: { section: Section; showNotes?: boolean }) {
  return <dl className="section-facts">
    <div><dt>Class number</dt><dd>{s.class_number} · {s.mode}</dd></div>
    <div><dt>Instructor</dt><dd>{s.instructors.map(i => i.name).join(', ') || 'Not listed'}</dd></div>
    <div><dt>Meetings</dt><dd>{s.meetings.length ? s.meetings.map((m, i) => <span className="meeting" key={i}>
      {m.days.map(d => d[0].toUpperCase() + d.slice(1)).join(', ') || 'Days TBA'} · {m.start_time && m.end_time ? `${formatTime(m.start_time)}–${formatTime(m.end_time)}` : 'Time TBA'} · {m.location || 'Location TBA'}
    </span>) : 'Not listed'}</dd></div>
    <div><dt>Units</dt><dd>{s.units ?? 'Unknown'}</dd></div>
    <div><dt>Availability</dt><dd><span className={`status ${s.availability}`}>{s.availability}</span> {s.open_seats === null ? 'Seat count unknown' : `${s.open_seats} open seat${s.open_seats === 1 ? '' : 's'}`}</dd></div>
    <div><dt>Last observation</dt><dd>{s.last_checked_at ? new Date(s.last_checked_at).toLocaleString() : 'Not observed'}{s.is_stale && <span className="status unknown">Stale</span>}</dd></div>
    {showNotes && s.notes && <div><dt>Notes</dt><dd>{s.notes}</dd></div>}
  </dl>
}
