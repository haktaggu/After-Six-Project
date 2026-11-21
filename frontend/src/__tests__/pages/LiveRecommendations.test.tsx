import { afterEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, waitFor, within } from '@testing-library/react'
import RecordEditor from '../../components/RecordEditor'
import Dashboard from '../../pages/Dashboard'
import Profile from '../../pages/Profile'
import Roadmap from '../../pages/Roadmap'
import type { CourseRecord, CourseSuggestion, StudentRoadmapEntry } from '../../shared/api/types'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

it('updates open recommendations after changing course history or the profile limit', async () => {
  const prerequisite: CourseRecord = { course_id: 'CMPE-50', status: 'in_progress', grade: null, term: null }
  const courseIds = ['CMPE-70', 'CMPE-126', 'CMPE-131', 'CMPE-140', 'CMPE-146']
  const major = { major_code: 'CMPE', title: 'Computer Engineering', degree_type: 'BS' }
  let history: CourseRecord | null = prerequisite
  let recommendationLimit = 3

  vi.stubGlobal('fetch', vi.fn(async (path: string, request: RequestInit) => {
    if (path === '/api/me/eligibility') {
      return Response.json({ results: [{
        course_id: 'CMPE-50', status: 'eligible', reasons: [], missing_course_ids: [],
      }] })
    }
    if (path === '/api/me/course-records/CMPE-50' && request.method === 'PUT') {
      const record: CourseRecord = { ...prerequisite, ...JSON.parse(String(request.body)) }
      history = record
      return Response.json(record)
    }
    if (path === '/api/me/course-records/CMPE-50' && request.method === 'DELETE') {
      history = null
      return new Response(null, { status: 204 })
    }
    if (path === '/api/me/roadmap') {
      const prerequisitePassed = history?.status === 'completed' && history.grade === 'B'
      const courses: StudentRoadmapEntry[] = courseIds.map(courseId => ({
        course: {
          id: courseId, subject: 'CMPE', catalog_number: courseId.split('-')[1], title: 'Engineering course',
          description: null, units_min: 3, units_max: 3, prerequisite_text: 'CMPE 50',
          corequisite_text: null, restrictions_text: null, catalog_url: null,
        },
        term_order: 5, is_required: true, student_status: 'not_started', grade: null,
        eligibility: {
          course_id: courseId, status: prerequisitePassed ? 'eligible' : 'ineligible',
          reasons: [], missing_course_ids: prerequisitePassed ? [] : ['CMPE-50'],
        },
      }))
      return Response.json({
        major,
        summary: { completed_courses: 0, total_required_courses: courses.length, completion_percent: 0 },
        courses,
        recommendations: prerequisitePassed ? courseIds.slice(0, recommendationLimit) : [],
        recommendation_limit: recommendationLimit,
        suggestions: [
          ...(!history ? [{
            course_id: 'MATH-19', title: 'Precalculus', status: 'ready', reason: 'Can help unlock CMPE-70.',
          }] : []),
          ...courses.map(({ course }): CourseSuggestion => ({
            course_id: course.id, title: course.title,
            status: prerequisitePassed ? 'ready' : history ? 'after_current' : 'requirements_remaining',
            reason: prerequisitePassed ? 'Requirements met.' : 'Complete CMPE-50 with the required grade.',
          })),
        ].slice(0, recommendationLimit),
      })
    }
    if (path === '/api/me') {
      const prerequisitePassed = history?.status === 'completed' && history.grade === 'B'
      if (request.method === 'PATCH') {
        const fields = JSON.parse(String(request.body))
        expect(fields).toEqual({ major_code: 'CMPE', recommendation_limit: 5 })
        recommendationLimit = fields.recommendation_limit
      }
      return Response.json({
        user: { full_name: 'Test Student', email: 'student@example.com' },
        profile: {
          major_code: 'CMPE', gpa: prerequisitePassed ? 3 : null, earned_units: prerequisitePassed ? 4 : 0,
          standing: 'freshman', recommendation_limit: recommendationLimit,
        },
      })
    }
    if (path.startsWith('/api/majors?')) {
      return Response.json({ items: [major], total: 1 })
    }
    if (path === '/api/me/notification-preferences') {
      return Response.json({ available: false, enabled: false })
    }
    if (path === '/api/me/course-calendar') {
      return Response.json([])
    }
    if (path.startsWith('/api/me/watchlist?')) {
      return Response.json({ items: [], total: 0 })
    }
    throw new Error(`Unexpected request: ${request.method} ${path}`)
  }))

  const dashboard = within(render(<Dashboard />).container)
  const onNavigate = vi.fn()
  const roadmap = within(render(<Roadmap onNavigate={onNavigate} />).container)
  const editor = render(
    <RecordEditor record={prerequisite} courseId="CMPE-50" terms={[]} onSaved={() => {}} />,
  )
  const dashboardHeading = await dashboard.findByRole('heading', { name: 'Course suggestions' })
  const dashboardSuggestions = within(dashboardHeading.parentElement!)
  const graph = await roadmap.findByRole('region', { name: 'Scrollable course dependency graph' })
  await dashboardSuggestions.findByText(/CMPE-70/)
  expect(dashboardSuggestions.getAllByText('After current courses')).toHaveLength(3)
  expect(within(graph).getAllByText('After current courses')).toHaveLength(3)
  expect(roadmap.queryByRole('heading', { name: 'Course suggestions' })).toBeNull()

  const suggestedNode = within(graph).getByRole('button', { name: /CMPE-70/ })
  expect(within(suggestedNode).getByText('After current courses')).toBeDefined()
  fireEvent.click(suggestedNode)
  const courseDetails = await roadmap.findByRole('region', { name: 'Selected course CMPE-70' })
  fireEvent.click(within(courseDetails).getByRole('button', { name: 'Add course' }))
  expect(onNavigate).toHaveBeenLastCalledWith('Add Course', 'CMPE-70')
  expect(within(courseDetails).getByText('Complete CMPE-50 with the required grade.')).toBeDefined()
  fireEvent.click(within(courseDetails).getByRole('button', { name: 'Clear selection' }))

  fireEvent.click(roadmap.getByRole('button', { name: 'Semester list' }))
  const courseRow = roadmap.getByRole('heading', { name: 'CMPE-70' }).closest('article')!
  fireEvent.click(within(courseRow).getByRole('button', { name: 'Add course' }))
  expect(onNavigate).toHaveBeenLastCalledWith('Add Course', 'CMPE-70')
  expect(within(courseRow).getByText('After current courses')).toBeDefined()
  expect(within(courseRow).getByText('Complete CMPE-50 with the required grade.')).toBeDefined()

  const form = within(editor.container)
  fireEvent.change(form.getByLabelText('Status'), { target: { value: 'completed' } })
  fireEvent.change(form.getByLabelText('Grade'), { target: { value: 'B' } })
  fireEvent.click(form.getByRole('button', { name: 'Save changes' }))

  await dashboard.findByText('3.00')
  await waitFor(() => {
    expect(dashboardSuggestions.getAllByText('Ready now')).toHaveLength(3)
    expect(roadmap.getAllByText('Ready now')).toHaveLength(3)
  })

  const profile = within(render(<Profile />).container)
  const limit = await profile.findByRole<HTMLSelectElement>('combobox', { name: 'Number of course suggestions' })
  expect(limit.value).toBe('3')
  fireEvent.change(limit, { target: { value: '5' } })
  fireEvent.click(profile.getByRole('button', { name: 'Save profile' }))
  await profile.findByText('Profile saved.')
  await dashboardSuggestions.findByRole('button', { name: /CMPE-146/ })
  expect(profile.getByRole<HTMLSelectElement>('combobox', { name: 'Number of course suggestions' }).value).toBe('5')
  expect(dashboardSuggestions.getAllByRole('listitem')).toHaveLength(5)
  fireEvent.click(roadmap.getByRole('button', { name: 'Dependency graph' }))
  const updatedGraph = await roadmap.findByRole('region', { name: 'Scrollable course dependency graph' })
  await waitFor(() => expect(within(updatedGraph).getAllByText('Ready now')).toHaveLength(5))

  fireEvent.click(form.getByRole('button', { name: 'Remove record' }))

  await waitFor(() => {
    expect(dashboardSuggestions.getAllByText('Requirements remaining')).toHaveLength(4)
    expect(within(updatedGraph).getAllByText('Requirements remaining')).toHaveLength(4)
    expect(dashboard.queryByText('3.00')).toBeNull()
  })
  const outside = roadmap.getByRole('region', { name: 'Suggested courses outside the roadmap' })
  fireEvent.click(within(outside).getByRole('button', { name: /MATH-19/ }))
  expect(onNavigate).toHaveBeenLastCalledWith('Search', 'MATH-19')
  fireEvent.click(roadmap.getByRole('button', { name: 'Semester list' }))
  expect(roadmap.getByRole('button', { name: /MATH-19/ })).toBeDefined()
  expect(roadmap.getAllByText('Requirements remaining')).toHaveLength(4)
})
