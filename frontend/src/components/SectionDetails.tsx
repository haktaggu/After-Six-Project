import type { Eligibility, Section } from '../shared/api/types'

export function EligibilityDetails({ value }: { value: Eligibility }) {
  return <details className="eligibility">
    <summary><span className={`status ${value.status}`}>{value.status}</span> Prerequisite details</summary>
    {value.reasons.length ? <ul>{value.reasons.map((r, i) => <li key={i}>{r}</li>)}</ul> : <p>No prerequisite conditions apply.</p>}
    {value.missing_course_ids.length > 0 && <p>Missing credit: {value.missing_course_ids.join(', ')}</p>}
  </details>
}

export default function SectionDetails({ section: s }: { section: Section }) {
  return <dl className="section-facts">
    <div><dt>Class number</dt><dd>{s.class_number} · {s.mode}</dd></div>
    <div><dt>Instructor</dt><dd>{s.instructors.map(i => i.name).join(', ') || 'Not listed'}</dd></div>
    <div><dt>Meetings · Pacific time</dt><dd>{s.meetings.length ? s.meetings.map((m, i) => <span className="meeting" key={i}>
      {m.days.map(d => d[0].toUpperCase() + d.slice(1)).join(', ') || 'Days TBA'} · {m.start_time && m.end_time ? `${m.start_time}–${m.end_time}` : 'Time TBA'} · {m.location || 'Location TBA'}
    </span>) : 'Not listed'}</dd></div>
    <div><dt>Units</dt><dd>{s.units ?? 'Unknown'}</dd></div>
    <div><dt>Availability</dt><dd><span className={`status ${s.availability}`}>{s.availability}</span> {s.open_seats === null ? 'Seat count unknown' : `${s.open_seats} open seat${s.open_seats === 1 ? '' : 's'}`}</dd></div>
    <div><dt>Last observation</dt><dd>{s.last_checked_at ? new Date(s.last_checked_at).toLocaleString() : 'Not observed'}{s.is_stale && <span className="status unknown">Stale</span>}</dd></div>
    {s.notes && <div><dt>Notes</dt><dd>{s.notes}</dd></div>}
  </dl>
}
