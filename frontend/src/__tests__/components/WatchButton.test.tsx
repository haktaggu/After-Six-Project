import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react'
import WatchButton from '../../components/WatchButton'
import * as watchlistApi from '../../shared/api/watchlist'

vi.mock('../../shared/api/watchlist')

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('WatchButton', () => {
  it('calls addWatch on click and updates button to "Watching"', async () => {
    const mockWatchlistEntry = {
      id: 'watch-1',
      student_id: 'stu-1',
      section: {
        id: 'sec-1',
        term: 'fall-2026',
        class_number: '48201',
        section_number: '01',
        title: 'Software Engineering I',
        mode: 'In Person',
        units: 3,
        open_seats: 5,
        availability: 'open' as const,
        meetings: [],
        instructors: [],
        notes: null,
        source_url: '',
        last_checked_at: null,
        is_stale: false,
        course: {
          id: 'CMPE-131',
          subject: 'CMPE',
          catalog_number: '131',
          title: 'Software Engineering I',
          description: '',
          units_min: 3,
          units_max: 3,
          prerequisite_text: null,
          corequisite_text: null,
          restrictions_text: null,
          catalog_url: null,
        },
      },
      term: 'fall-2026',
      added_at: '2026-11-15T08:00:00Z',
      active: true,
      eligibility: {
        course_id: 'CMPE-131',
        status: 'eligible' as const,
        reasons: [],
        missing_course_ids: [],
      },
    }

    vi.spyOn(watchlistApi, 'addWatch').mockResolvedValue(mockWatchlistEntry)

    render(<WatchButton sectionId="sec-1" />)
    const button = screen.getByRole('button', { name: 'Watch section' })
    fireEvent.click(button)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Watching' })).toBeDefined()
    })
    expect((screen.getByRole('button', { name: 'Watching' }) as HTMLButtonElement).disabled).toBe(true)
  })

  it('renders error notice if adding to watchlist fails', async () => {
    vi.spyOn(watchlistApi, 'addWatch').mockRejectedValue(new Error('Failed to watch course'))

    render(<WatchButton sectionId="sec-1" />)
    fireEvent.click(screen.getByRole('button', { name: 'Watch section' }))

    await waitFor(() => {
      expect(screen.getByText('Failed to watch course')).toBeDefined()
    })
  })
})
