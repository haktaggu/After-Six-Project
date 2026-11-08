import type { CalendarCourse, Weekday } from '../shared/api/types'
import { formatTime } from '../shared/meetingTime'

export const weekdays: Array<{ id: Weekday; name: string }> = [
  { id: 'mon', name: 'Monday' },
  { id: 'tue', name: 'Tuesday' },
  { id: 'wed', name: 'Wednesday' },
  { id: 'thu', name: 'Thursday' },
  { id: 'fri', name: 'Friday' },
  { id: 'sat', name: 'Saturday' },
  { id: 'sun', name: 'Sunday' },
]

type ClassEntry = {
  id: string
  courseId: string
  title: string
  section?: string
}

export type ScheduledClass = ClassEntry & {
  day: Weekday
  start: number
  end: number
  location: string | null
}

type UnscheduledClass = ClassEntry & { reason: string }

function minutes(time: string): number {
  const [hour, minute] = time.split(':').map(Number)
  return hour * 60 + minute
}

export function minuteLabel(value: number): string {
  const minute = value % 1440
  return formatTime(`${Math.floor(minute / 60)}:${String(minute % 60).padStart(2, '0')}`)
}

export function buildWeek(courses: CalendarCourse[]) {
  const scheduled: ScheduledClass[] = []
  const unscheduled: UnscheduledClass[] = []
  for (const course of courses) {
    const entry = { id: course.course_id, courseId: course.course_id, title: course.title }
    if (!course.term || !course.sections.length) {
      unscheduled.push({ ...entry, reason: course.term ? 'Choose sections in Course history.' : 'Choose a term and sections in Course history.' })
      continue
    }
    for (const section of course.sections) {
      const sectionEntry = { ...entry, id: section.id, section: section.section_number, title: section.title || course.title }
      let needsTime = section.meetings.length === 0
      let hasTime = false
      section.meetings.forEach((meeting, index) => {
        if (meeting.is_tba || !meeting.start_time || !meeting.end_time || !meeting.days.length) {
          needsTime = true
          return
        }
        const start = minutes(meeting.start_time)
        const end = minutes(meeting.end_time)
        if (start === end) {
          needsTime = true
          return
        }
        hasTime = true
        for (const day of new Set(meeting.days)) {
          const id = `${section.id}-${index}-${day}`
          scheduled.push({ ...sectionEntry, id, day, start, end: end > start ? end : 1440, location: meeting.location })
          if (end < start && end > 0) {
            const nextDay = weekdays[(weekdays.findIndex(item => item.id === day) + 1) % weekdays.length].id
            scheduled.push({ ...sectionEntry, id: `${id}-continued`, day: nextDay, start: 0, end, location: meeting.location })
          }
        }
      })
      if (needsTime) {
        unscheduled.push({ ...sectionEntry, reason: hasTime ? 'Additional meeting time TBA.' : 'Meeting time TBA or arranged.' })
      }
    }
  }
  scheduled.sort((a, b) => a.start - b.start || a.end - b.end || a.id.localeCompare(b.id))
  return { scheduled, unscheduled }
}

export function layoutDay(meetings: ScheduledClass[]) {
  const positioned: Array<ScheduledClass & { column: number; columns: number }> = []
  let groupStart = 0
  let groupEnd = 0
  let columnEnds: number[] = []
  for (const meeting of meetings) {
    if (meeting.start >= groupEnd) {
      for (const event of positioned.slice(groupStart)) event.columns = columnEnds.length
      groupStart = positioned.length
      columnEnds = []
    }
    const available = columnEnds.findIndex(end => end <= meeting.start)
    const column = available >= 0 ? available : columnEnds.length
    columnEnds[column] = meeting.end
    positioned.push({ ...meeting, column, columns: 1 })
    groupEnd = Math.max(groupEnd, meeting.end)
  }
  for (const event of positioned.slice(groupStart)) event.columns = columnEnds.length
  return positioned
}
