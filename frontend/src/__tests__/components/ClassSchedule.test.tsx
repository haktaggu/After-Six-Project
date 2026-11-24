import { afterEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import ClassSchedule from '../../components/ClassSchedule'
import * as accounts from '../../shared/api/accounts'
import type { CalendarCourse, Meeting } from '../../shared/api/types'

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

function course(courseId: string, title: string, status: CalendarCourse['status'],
                term: CalendarCourse['term'], meetings: Meeting[] = []): CalendarCourse {
  return {
    course_id: courseId,
    title,
    status,
    term,
    sections: meetings.length ? [{ id: courseId, section_number: '01', title, meetings }] : [],
  }
}

it('separates enrolled and planned meetings, with independent terms and side-by-side conflicts', async () => {
  const fall = { id: 'fall-2026', name: 'Fall 2026' }
  const spring = { id: 'spring-2027', name: 'Spring 2027' }
  const summer = { id: 'summer-2026', name: 'Summer 2026' }
  vi.spyOn(accounts, 'getCourseCalendar').mockResolvedValue([
    course('CHEM-10', 'Chemistry', 'in_progress', fall, [
      { days: ['mon', 'wed'], start_time: '09:00', end_time: '10:15', location: 'Room A', is_tba: false },
    ]),
    course('HIST-20', 'History', 'planned', fall, [
      { days: ['mon'], start_time: '09:30', end_time: '10:45', location: 'Room B', is_tba: false },
    ]),
    course('PHYS-20', 'Physics', 'in_progress', fall, [
      { days: ['mon'], start_time: '09:30', end_time: '10:45', location: 'Lab', is_tba: false },
    ]),
    course('MUS-15', 'Music', 'in_progress', summer, [
      { days: ['fri'], start_time: '11:00', end_time: '12:15', location: 'Hall', is_tba: false },
    ]),
    course('ART-30', 'Art', 'planned', spring, [
      { days: ['sat'], start_time: '13:00', end_time: '14:15', location: 'Studio', is_tba: false },
      { days: [], start_time: null, end_time: null, location: null, is_tba: true },
    ]),
    course('MATH-40', 'Mathematics', 'planned', null),
  ])
  render(<ClassSchedule />)

  const enrolled = within(await screen.findByRole('region', { name: 'Enrolled calendar' }))
  const planned = within(screen.getByRole('region', { name: 'Planned calendar' }))
  const enrolledGrid = within(enrolled.getByRole('region', { name: 'Enrolled weekly schedule' }))
  const plannedGrid = within(planned.getByRole('region', { name: 'Planned weekly schedule' }))
  const enrolledMonday = within(enrolledGrid.getByRole('region', { name: 'Monday' }))
  const plannedMonday = within(plannedGrid.getByRole('region', { name: 'Monday' }))
  expect(enrolledMonday.getByText('Chemistry').closest<HTMLElement>('.calendar-block')?.style.left).toBe('0%')
  expect(enrolledMonday.getByText('Physics').closest<HTMLElement>('.calendar-block')?.style.left).toBe('50%')
  expect(plannedMonday.getByText('History').closest<HTMLElement>('.calendar-block')?.style.left).toBe('0%')
  expect(enrolled.queryByText('History')).toBeNull()
  expect(planned.queryByText('Physics')).toBeNull()
  expect(within(enrolledGrid.getByRole('region', { name: 'Wednesday' })).getByText('Room A')).toBeDefined()
  expect(plannedGrid.queryByRole('region', { name: 'Saturday' })).toBeNull()
  expect(planned.getByText('Choose a term and sections in Course history.')).toBeDefined()

  const enrolledTerm = enrolled.getByRole<HTMLSelectElement>('combobox', { name: 'Term' })
  const plannedTerm = planned.getByRole<HTMLSelectElement>('combobox', { name: 'Term' })
  expect(enrolledTerm.value).toBe(fall.id)
  expect(plannedTerm.value).toBe(fall.id)
  fireEvent.change(plannedTerm, { target: { value: spring.id } })
  expect(enrolledTerm.value).toBe(fall.id)
  expect(enrolledMonday.getByText('Chemistry')).toBeDefined()
  expect(plannedGrid.queryByText('History')).toBeNull()
  expect(within(plannedGrid.getByRole('region', { name: 'Saturday' })).getByText('1:00 PM–2:15 PM')).toBeDefined()
  expect(planned.getByText('Additional meeting time TBA.')).toBeDefined()
  fireEvent.change(enrolledTerm, { target: { value: summer.id } })
  expect(enrolledGrid.getByText('Music')).toBeDefined()
  expect(plannedTerm.value).toBe(spring.id)
  expect(screen.queryByRole('button', { name: 'Agenda' })).toBeNull()
})

it('keeps the empty calendar visible when only one schedule has courses', async () => {
  vi.spyOn(accounts, 'getCourseCalendar').mockResolvedValue([
    course('ART-30', 'Art', 'planned', { id: 'spring-2027', name: 'Spring 2027' }),
  ])
  render(<ClassSchedule />)

  const enrolled = within(await screen.findByRole('region', { name: 'Enrolled calendar' }))
  const planned = within(screen.getByRole('region', { name: 'Planned calendar' }))
  expect(enrolled.getByText('No enrolled courses yet.')).toBeDefined()
  expect(planned.getByText('Spring 2027')).toBeDefined()
  expect(planned.getByText('Choose sections in Course history.')).toBeDefined()
})
