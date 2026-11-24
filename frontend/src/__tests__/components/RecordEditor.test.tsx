import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { render, screen, fireEvent, cleanup, waitFor } from '@testing-library/react'
import RecordEditor from '../../components/RecordEditor'
import * as accountsApi from '../../shared/api/accounts'
import * as coursesApi from '../../shared/api/courses'
import * as planning from '../../shared/api/planning'
import type { EnrollmentRequirement, Section, Term } from '../../shared/api/types'

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

beforeEach(() => {
  vi.spyOn(planning, 'checkEligibility').mockImplementation(async body => ({
    results: body.course_ids.map(id => ({
      course_id: id, status: 'eligible', reasons: [], missing_course_ids: [], additional_requirements: [],
    })),
  }))
})

const mockTerms: Term[] = [
  { id: 'fall-2026', name: 'Fall 2026' },
]

describe('RecordEditor', () => {
  it('groups alternative enrollment paths and saves only the workshop answer for a qualifying C+', async () => {
    const coursework = (minimum_grade: string, status: 'eligible' | 'ineligible'): EnrollmentRequirement => ({
      kind: 'course', text: 'Calculus II', status, children: [],
      course: { course_id: 'MATH-31', minimum_grade, status, recorded_status: 'completed', grade: 'C+', alternative: true },
    })
    const exam = (score: number): EnrollmentRequirement => ({
      kind: 'confirmation', text: `AP Calculus BC score ${score} or higher`, status: 'unknown', children: [],
      confirmation: { id: `ap-${score}`, text: `AP Calculus BC score ${score} or higher`, confirmed: false },
    })
    vi.mocked(planning.checkEligibility).mockResolvedValue({ results: [{
      course_id: 'MATH-32', status: 'unknown', reasons: [], missing_course_ids: [],
      additional_requirements: [
        { id: 'ap-4', text: 'AP Calculus BC score 4 or higher', confirmed: false },
        { id: 'ap-3', text: 'AP Calculus BC score 3 or higher', confirmed: false },
        { id: 'workshop', text: 'Enroll in MATH-32W in the same term', confirmed: false },
      ],
      requirements: { kind: 'any', text: 'Choose one enrollment path', status: 'unknown', children: [
        { kind: 'all', text: 'Coursework or exam placement without MATH-32W', status: 'unknown', children: [
          { kind: 'any', text: 'Coursework or exam', status: 'unknown', children: [coursework('B', 'ineligible'), exam(4)] },
          { kind: 'check', text: 'First enrollment in this course', status: 'eligible', children: [] },
        ] },
        { kind: 'all', text: 'Coursework or exam placement with MATH-32W', status: 'unknown', children: [
          { kind: 'any', text: 'Coursework or exam', status: 'eligible', children: [coursework('C-', 'eligible'), exam(3)] },
          { kind: 'course', text: 'Enroll in MATH-32W in the same term', status: 'unknown', children: [],
            course: { course_id: 'MATH-32W', minimum_grade: null, status: 'unknown', recorded_status: null, grade: null, alternative: true, concurrent: true },
            confirmation: { id: 'workshop', text: 'Enroll in MATH-32W in the same term', confirmed: false } },
        ] },
      ] },
    }] })
    const save = vi.spyOn(accountsApi, 'putCourseRecord').mockResolvedValue({
      course_id: 'MATH-32', status: 'planned', grade: null, term: null,
    })
    render(<RecordEditor courseId="MATH-32" terms={[]} onSaved={() => {}} />)
    const workshop = await screen.findByRole<HTMLSelectElement>('combobox', { name: 'Enroll in MATH-32W in the same term' })
    const paths = screen.getAllByRole('heading').filter(heading => heading.textContent?.startsWith('Coursework or exam placement'))
    expect(paths.map(path => path.textContent)).toEqual([
      'Coursework or exam placement with MATH-32W', 'Coursework or exam placement without MATH-32W',
    ])
    expect(screen.getByText('completed · Grade C+ · Requirement met')).toBeDefined()
    fireEvent.change(workshop, { target: { value: 'confirmed' } })
    expect(screen.getByRole<HTMLSelectElement>('combobox', { name: 'AP Calculus BC score 3 or higher' }).value).toBe('unconfirmed')
    expect(screen.getByRole<HTMLSelectElement>('combobox', { name: 'AP Calculus BC score 4 or higher' }).value).toBe('unconfirmed')
    fireEvent.click(screen.getByRole('button', { name: 'Add course' }))
    await screen.findByText('Course record saved.')
    expect(save).toHaveBeenCalledWith('MATH-32', {
      status: 'planned', grade: null, term: null, requirement_confirmations: { workshop: true },
    })
  })

  it('stages requirement answers and saves them with the course record', async () => {
    vi.mocked(planning.checkEligibility).mockResolvedValue({ results: [{
      course_id: 'MATH-31', status: 'unknown', reasons: [], missing_course_ids: [],
      additional_requirements: [{ id: 'placement', text: 'Placement assessment completed', confirmed: false }],
      course_requirements: [{
        course_id: 'MATH-30', minimum_grade: 'C-', recorded_status: 'completed', grade: 'B',
        status: 'eligible', alternative: true,
      }],
    }] })
    const save = vi.spyOn(accountsApi, 'putCourseRecord').mockResolvedValue({
      course_id: 'MATH-31', status: 'planned', grade: null, term: null,
    })
    const navigate = vi.fn()
    render(<RecordEditor courseId="MATH-31" terms={[]} onSaved={() => {}} onNavigate={navigate} />)
    const selector = await screen.findByRole<HTMLSelectElement>('combobox', { name: 'Placement assessment completed' })
    fireEvent.change(selector, { target: { value: 'confirmed' } })
    expect(save).not.toHaveBeenCalled()
    expect(screen.getByText('completed · Grade B · Requirement met')).toBeDefined()
    fireEvent.click(screen.getByRole('button', { name: 'Add course' }))
    await screen.findByText('Course record saved.')
    expect(save).toHaveBeenCalledWith('MATH-31', {
      status: 'planned', grade: null, term: null, requirement_confirmations: { placement: true },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Edit record' }))
    expect(navigate).toHaveBeenCalledWith('Add Course', 'MATH-30')
  })

  it('preserves draft answers when a combined save fails', async () => {
    vi.mocked(planning.checkEligibility).mockResolvedValue({ results: [{
      course_id: 'ART-10', status: 'unknown', reasons: [], missing_course_ids: [],
      additional_requirements: [{ id: 'consent', text: 'Instructor consent', confirmed: false }],
    }] })
    vi.spyOn(accountsApi, 'putCourseRecord').mockRejectedValue(new Error('Unable to save course'))
    const saved = vi.fn()
    render(<RecordEditor courseId="ART-10" terms={[]} onSaved={saved} />)
    const selector = await screen.findByRole<HTMLSelectElement>('combobox', { name: 'Instructor consent' })
    fireEvent.change(selector, { target: { value: 'confirmed' } })
    fireEvent.click(screen.getByRole('button', { name: 'Add course' }))
    await screen.findByText('Unable to save course')
    expect(selector.value).toBe('confirmed')
    expect(saved).not.toHaveBeenCalled()
  })

  it('renders form inputs and saves course record', async () => {
    const putSpy = vi.spyOn(accountsApi, 'putCourseRecord').mockResolvedValue({
      course_id: 'CMPE-131',
      status: 'planned',
      grade: null,
      term: 'fall-2026',
    })
    const onSaved = vi.fn()

    render(<RecordEditor courseId="CMPE-131" terms={mockTerms} onSaved={onSaved} />)

    expect(screen.getByRole('button', { name: 'Add course' })).toBeDefined()

    await waitFor(() => expect(screen.getByRole<HTMLButtonElement>('button', { name: 'Add course' }).disabled).toBe(false))
    const form = screen.getByRole('button', { name: 'Add course' }).closest('form')!
    fireEvent.submit(form)

    await waitFor(() => {
      expect(onSaved).toHaveBeenCalledTimes(1)
      expect(putSpy).toHaveBeenCalledWith('CMPE-131', {
        status: 'planned',
        grade: null,
        term: null,
      })
    })
  })

  it('renders remove button when editing an existing record', async () => {
    const deleteSpy = vi.spyOn(accountsApi, 'deleteCourseRecord').mockResolvedValue()
    const onRemoved = vi.fn()

    render(
      <RecordEditor
        record={{ course_id: 'CMPE-131', status: 'completed', grade: 'A', term: 'fall-2026' }}
        courseId="CMPE-131"
        terms={mockTerms}
        onSaved={() => {}}
        onRemoved={onRemoved}
      />
    )

    const removeBtn = screen.getByRole('button', { name: 'Remove record' })
    fireEvent.click(removeBtn)

    await waitFor(() => {
      expect(deleteSpy).toHaveBeenCalledWith('CMPE-131')
      expect(onRemoved).toHaveBeenCalledTimes(1)
    })
  })

  it('saves selected lecture and lab sections for a planned course', async () => {
    const course = {
      id: 'CMPE-131', title: 'Software Engineering', subject: 'CMPE', catalog_number: '131',
      description: null, units_min: 3, units_max: 3, prerequisite_text: null, corequisite_text: null,
      restrictions_text: null, catalog_url: null,
    }
    const sections: Section[] = ['Lecture', 'Lab'].map((kind, index) => ({
      id: `section-${index}`, term: 'fall-2026', class_number: `100${index}`, section_number: `0${index + 1}`,
      course, title: kind, mode: 'In Person', units: 3, open_seats: 0, availability: 'closed', meetings: [],
      instructors: [], notes: null, source_url: 'https://www.sjsu.edu/', last_checked_at: null, is_stale: true,
    }))
    const list = vi.spyOn(coursesApi, 'listSections').mockResolvedValue({ items: sections, total: 2, offset: 0, limit: 100 })
    const put = vi.spyOn(accountsApi, 'putCourseRecord').mockResolvedValue({
      course_id: course.id, status: 'planned', grade: null, term: 'fall-2026', section_ids: sections.map(s => s.id),
    })
    render(<RecordEditor courseId={course.id} terms={mockTerms} onSaved={() => {}} />)

    fireEvent.change(screen.getByLabelText('Term'), { target: { value: 'fall-2026' } })
    fireEvent.click(await screen.findByRole('checkbox', { name: /Lecture/ }))
    fireEvent.click(screen.getByRole('checkbox', { name: /Lab/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Add course' }))

    await screen.findByText('Course record saved.')
    expect(list).toHaveBeenCalledWith({ term: 'fall-2026', course_id: course.id, limit: 100, offset: 0 }, expect.any(AbortSignal))
    expect(put).toHaveBeenCalledWith(course.id, {
      status: 'planned', grade: null, term: 'fall-2026', section_ids: ['section-0', 'section-1'],
    })
  })
})
