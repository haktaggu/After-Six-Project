import { type CSSProperties, useEffect, useId, useState } from 'react'
import { getCourseCalendar, subscribeToAcademicPlanChanges } from '../shared/api/accounts'
import type { CalendarCourse, PageProps } from '../shared/api/types'
import { useLoad } from '../shared/hooks/useLoad'
import { ErrorNotice } from './Feedback'
import { buildWeek, layoutDay, minuteLabel, type ScheduledClass, weekdays } from './weeklyCalendar'
import './ClassSchedule.css'

function termOrder(id: string) {
  const [season, year] = id.split('-')
  return (Number(year) || 0) * 4 + ['winter', 'spring', 'summer', 'fall'].indexOf(season)
}

export default function ClassSchedule({ onNavigate }: Pick<PageProps, 'onNavigate'>) {
  const { data: courses, error, loading, reload } = useLoad(getCourseCalendar)
  const headingId = useId()
  useEffect(() => subscribeToAcademicPlanChanges(reload), [reload])

  return (
    <section className="class-schedule" aria-labelledby={headingId}>
      <h2 id={headingId}>Class schedule</h2>
      <ErrorNotice error={error} />
      {Boolean(error) && <button type="button" onClick={reload}>Retry schedule</button>}
      {loading && <p role="status" className="help">Loading class schedule…</p>}
      {courses && <div className="schedule-calendars">
        <CalendarPanel status="in_progress" courses={courses.filter(course => course.status === 'in_progress')} />
        <CalendarPanel status="planned" courses={courses.filter(course => course.status === 'planned')} />
      </div>}
      {onNavigate && courses && (
        <button type="button" className="calendar-manage" onClick={() => onNavigate(courses.length ? 'Course History' : 'Add Course')}>
          {courses.length ? 'Manage calendar sections' : 'Add a course'}
        </button>
      )}
    </section>
  )
}

function CalendarPanel({ status, courses }: { status: CalendarCourse['status']; courses: CalendarCourse[] }) {
  const headingId = useId()
  const [term, setTerm] = useState('')
  const label = status === 'in_progress' ? 'Enrolled' : 'Planned'
  const terms = [...new Map(courses.flatMap(course => course.term ? [[course.term.id, course.term] as const] : [])).values()]
    .sort((a, b) => termOrder(a.id) - termOrder(b.id) || a.name.localeCompare(b.name))
  const selectedTerm = terms.find(item => item.id === term) ?? (status === 'in_progress' ? terms.at(-1) : terms[0])
  const { scheduled, unscheduled } = buildWeek(courses.filter(course => !course.term || course.term.id === selectedTerm?.id))

  return (
    <section className="calendar-panel" data-status={status} aria-labelledby={headingId}>
      <header className="calendar-panel-header">
        <h3 id={headingId}>{label} calendar</h3>
        {terms.length > 1 ? (
          <label>
            Term
            <select value={selectedTerm?.id} onChange={event => setTerm(event.target.value)}>
              {terms.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
          </label>
        ) : selectedTerm && <span className="calendar-term">{selectedTerm.name}</span>}
      </header>
      {courses.length === 0 && <p>No {label.toLowerCase()} courses yet.</p>}
      {scheduled.length > 0 && <WeeklyGrid meetings={scheduled} label={`${label} weekly schedule`} />}
      {unscheduled.length > 0 && (
        <div className="calendar-unscheduled">
          <h4>Unscheduled classes</h4>
          <ul>
            {unscheduled.map(entry => <li key={entry.id}>
              <span><strong>{entry.courseId}{entry.section ? ` · ${entry.section}` : ''}</strong> {entry.title}</span>
              <span className="help">{entry.reason}</span>
            </li>)}
          </ul>
        </div>
      )}
    </section>
  )
}

function WeeklyGrid({ meetings, label }: { meetings: ScheduledClass[]; label: string }) {
  const start = Math.floor(Math.min(...meetings.map(meeting => meeting.start)) / 60) * 60
  const end = Math.ceil(Math.max(...meetings.map(meeting => meeting.end)) / 60) * 60
  const hours = (end - start) / 60
  const days = weekdays.filter(({ id }, index) => index < 5 || meetings.some(meeting => meeting.day === id))
    .map(day => {
      const items = layoutDay(meetings.filter(meeting => meeting.day === day.id))
      return { ...day, items, lanes: Math.max(1, ...items.map(meeting => meeting.columns)) }
    })
  const gridStyle = {
    '--calendar-hours': hours,
    '--calendar-lanes': days.reduce((total, day) => total + day.lanes, 0),
    gridTemplateColumns: ['var(--calendar-time-width)', ...days.map(
      ({ lanes }) => `minmax(calc(var(--calendar-lane-width) * ${lanes}), ${lanes}fr)`,
    )].join(' '),
  } as CSSProperties

  return (
    <div className="calendar-scroll" role="region" aria-label={label} tabIndex={0}>
      <div className="calendar-week" style={gridStyle}>
        <div aria-hidden="true" className="calendar-time-column">
          <div className="calendar-day-heading">Time</div>
          <div className="calendar-time-body">
            {Array.from({ length: hours }, (_, index) => (
              <span key={index}>{minuteLabel(start + index * 60).replace(':00', '')}</span>
            ))}
          </div>
        </div>
        {days.map(({ id, name, items }) => (
          <section className="calendar-day-column" aria-label={name} key={id}>
            <h4 className="calendar-day-heading">{name}</h4>
            <div className="calendar-day-body">
              {items.map(meeting => (
                <div className="calendar-block"
                  key={meeting.id}
                  style={{
                    top: `${(meeting.start - start) / (end - start) * 100}%`,
                    height: `${(meeting.end - meeting.start) / (end - start) * 100}%`,
                    left: `${meeting.column / meeting.columns * 100}%`,
                    width: `calc(${100 / meeting.columns}% - 0.375rem)`,
                  }}>
                  <MeetingLabel meeting={meeting} />
                </div>
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  )
}

function MeetingLabel({ meeting }: { meeting: ScheduledClass }) {
  const title = `${meeting.courseId} · ${meeting.section}`
  const time = `${minuteLabel(meeting.start)}–${minuteLabel(meeting.end)}`
  return (
    <div className="calendar-meeting" title={`${title} · ${meeting.title} · ${time} · ${meeting.location || 'Location TBA'}`}>
      <strong>{title}</strong>
      <span className="calendar-meeting-title">{meeting.title}</span>
      <span>{time}</span>
      <span>{meeting.location || 'Location TBA'}</span>
    </div>
  )
}
