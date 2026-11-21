import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import AddCourse from '../../pages/AddCourse'
import * as accounts from '../../shared/api/accounts'
import * as courses from '../../shared/api/courses'
import * as planning from '../../shared/api/planning'

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

beforeEach(() => {
  vi.spyOn(planning, 'checkEligibility').mockImplementation(async body => ({
    results: body.course_ids.map(id => ({ course_id: id, status: 'eligible', reasons: [], missing_course_ids: [] })),
  }))
})

const catalogCourse = {
  id: 'MATH-32', subject: 'MATH', catalog_number: '32', title: 'Calculus III',
  description: null, units_min: 3, units_max: 3, prerequisite_text: 'MATH 31',
  corequisite_text: null, restrictions_text: null, catalog_url: null,
}

function catalog() {
  vi.spyOn(courses, 'listTerms').mockResolvedValue({
    items: [{ id: 'spring-2027', name: 'Spring 2027' }], total: 1, limit: 100, offset: 0,
  })
  return vi.spyOn(courses, 'listCourses').mockResolvedValue({
    items: [catalogCourse], total: 1, limit: 25, offset: 0,
  })
}

it('preselects a roadmap course and saves it through the course editor', async () => {
  const search = catalog()
  vi.spyOn(accounts, 'listCourseRecords').mockResolvedValue({ items: [], total: 0, limit: 100, offset: 0 })
  const save = vi.spyOn(accounts, 'putCourseRecord').mockResolvedValue({
    course_id: 'MATH-32', status: 'planned', grade: null, term: null,
  })
  render(<AddCourse target="MATH-32" />)
  const submit = await screen.findByRole('button', { name: 'Add course' })
  expect(screen.getByRole('heading', { name: 'MATH-32 · Calculus III' })).toBeDefined()
  expect(screen.queryByRole('searchbox')).toBeNull()
  expect(search).toHaveBeenCalledWith({ q: 'MATH-32', limit: 25, offset: 0 })
  await waitFor(() => expect((submit as HTMLButtonElement).disabled).toBe(false))
  fireEvent.click(submit)
  await waitFor(() => expect(save).toHaveBeenCalledWith('MATH-32', { status: 'planned', grade: null, term: null }))
})

it('loads an existing course record when editing from the roadmap', async () => {
  catalog()
  const record = { course_id: 'MATH-32', status: 'completed' as const, grade: 'B' as const, term: 'spring-2027' }
  vi.spyOn(accounts, 'listCourseRecords').mockResolvedValue({ items: [record], total: 1, limit: 100, offset: 0 })
  const save = vi.spyOn(accounts, 'putCourseRecord').mockResolvedValue(record)
  render(<AddCourse target="MATH-32" />)
  const submit = await screen.findByRole('button', { name: 'Save changes' })
  expect(screen.getByRole<HTMLSelectElement>('combobox', { name: 'Status' }).value).toBe('completed')
  expect(screen.getByRole<HTMLSelectElement>('combobox', { name: 'Grade' }).value).toBe('B')
  expect(screen.getByRole<HTMLSelectElement>('combobox', { name: 'Term' }).value).toBe('spring-2027')
  await waitFor(() => expect((submit as HTMLButtonElement).disabled).toBe(false))
  fireEvent.click(submit)
  await waitFor(() => expect(save).toHaveBeenCalledWith('MATH-32', {
    status: 'completed', grade: 'B', term: 'spring-2027',
  }))
})
