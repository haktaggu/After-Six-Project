import type { Eligibility, Section } from '../shared/api/types'

const statusNotes: Record<string, string> = {
  eligible: 'You meet the prerequisite requirements for this course.',
  ineligible: 'You currently do not meet one or more prerequisite requirements.',
  unknown: 'Prerequisite eligibility requires verification (department consent, placement exam, or concurrent enrollment).',
}

export function EligibilityDetails({ value, section }: { value: Eligibility; section?: Section }) {
  let displayStatus = value.status

  // Filter out redundant system noise and keep specific mismatches
  const coreReasons = value.reasons.filter(r => {
    const lower = r.toLowerCase()
    if (lower.includes('needs confirmation: major restriction:') && lower.split(':').length === 3) return false
    if (lower.includes('needs confirmation: math enrollment category')) return false
    return true
  })

  // Upgrade 'unknown' to 'ineligible' if specific mismatch is found
  const hasSpecificMismatch = coreReasons.some(r => {
    const lower = r.toLowerCase()
    return lower.includes('requires major eq') || lower.includes('actual:')
  })
  if (displayStatus === 'unknown' && (hasSpecificMismatch || value.missing_course_ids.length > 0)) {
    displayStatus = 'ineligible'
  }

  return <details className="eligibility">
    <summary>
      <span className={`status ${displayStatus}`}>{displayStatus}</span> Prerequisite & Fit Details
    </summary>

    <div className="eligibility-content" style={{ marginTop: '12px' }}>
      {section && (
        <div style={{ marginBottom: '16px', padding: '12px', background: 'var(--canvas)', borderRadius: '4px', border: '1px solid var(--border)' }}>
          <div style={{ marginBottom: '6px' }}>
            <strong>Prerequisite Courses:</strong> {section.course.prerequisite_text || 'None specified.'}
          </div>
          {section.course.restrictions_text && (
            <div>
              <strong>Fit/Restrictions:</strong> {section.course.restrictions_text}
            </div>
          )}
        </div>
      )}

      {displayStatus === 'eligible' && (
        <p style={{ color: '#166534', fontWeight: 500, margin: '8px 0' }}>
          You meet the prerequisite and major requirements for this course.
        </p>
      )}

      {displayStatus === 'ineligible' && (
        <div style={{ margin: '8px 0' }}>
          <p style={{ color: '#991b1b', fontWeight: 500, marginBottom: '6px' }}>
            You do not currently meet the requirements for this course.
          </p>
          {coreReasons.length > 0 && (
            <ul style={{ paddingLeft: '20px', fontSize: '13px' }}>
              {coreReasons.map((r, i) => {
                let formatted = r.replace(/needs confirmation:\s*/i, '')
                formatted = formatted.charAt(0).toUpperCase() + formatted.slice(1)
                return <li key={i}>{formatted}</li>
              })}
            </ul>
          )}
        </div>
      )}

      {displayStatus === 'unknown' && (
        <div style={{ margin: '8px 0' }}>
          <p style={{ color: '#92400e', fontWeight: 500, marginBottom: '4px' }}>
            Prerequisite eligibility requires verification.
          </p>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
            Please check with the department to confirm prerequisites or placement requirements.
          </p>
        </div>
      )}

      {value.missing_course_ids.length > 0 && (
        <p className="missing-credit" style={{ marginTop: '12px', padding: '8px', background: '#fef2f2', color: '#991b1b', borderRadius: '4px', fontSize: '13px' }}>
          <strong>Missing required courses:</strong> {value.missing_course_ids.join(', ')}
        </p>
      )}
    </div>
  </details>
}

function formatTime(time: string): string {
  if (!time) return ''

  // Handle ISO formatted time, automatically adapt to the user's local timezone
  if (time.includes('T') || time.includes('Z') || time.includes('+')) {
    try {
      return new Date(time).toLocaleTimeString('en-US', {
        // Removed hardcoded timeZone, it will now adapt to the local system timezone
        hour: 'numeric',
        minute: '2-digit'
      })
    } catch { return time; }
  }

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