import { describe, it, expect, afterEach } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import SectionDetails, { EligibilityDetails } from '../../components/SectionDetails'
import type { Eligibility, Section } from '../../shared/api/types'

afterEach(() => {
  cleanup()
})

const mockSection: Section = {
  id: 'sec-1',
  term: 'fall-2026',
  class_number: '48201',
  section_number: '01',
  title: 'Software Engineering I',
  mode: 'In Person',
  units: 3,
  open_seats: 5,
  availability: 'open',
  course: {
    id: 'CMPE-131',
    subject: 'CMPE',
    catalog_number: '131',
    title: 'Software Engineering I',
    description: 'Engineering methods for software systems.',
    units_min: 3,
    units_max: 3,
    prerequisite_text: 'CMPE 126 or CS 46B with C- or better',
    corequisite_text: null,
    restrictions_text: null,
    catalog_url: 'https://catalog.sjsu.edu',
  },
  meetings: [
    {
      days: ['tue', 'thu'],
      start_time: '10:30 AM',
      end_time: '11:45 AM',
      location: 'ENG 331',
      is_tba: false,
    },
  ],
  instructors: [{ name: 'Dr. Smith' }],
  notes: 'Class includes mandatory lab attendance.',
  source_url: 'https://sjsu.edu/classes',
  last_checked_at: '2026-11-15T08:00:00Z',
  is_stale: false,
}

describe('SectionDetails', () => {
  it('renders section class number and mode', () => {
    render(<SectionDetails section={mockSection} />)
    expect(screen.getByText('48201 · In Person')).toBeDefined()
  })

  it('renders instructor names', () => {
    render(<SectionDetails section={mockSection} />)
    expect(screen.getByText('Dr. Smith')).toBeDefined()
  })

  it('renders meeting days, times, and room', () => {
    render(<SectionDetails section={mockSection} />)
    expect(screen.getByText('Meetings')).toBeDefined()
    expect(screen.getByText(/Tue, Thu · 10:30 AM–11:45 AM · ENG 331/)).toBeDefined()
  })

  it('formats 24-hour meeting times to 12-hour AM/PM', () => {
    const sectionWith24h = {
      ...mockSection,
      meetings: [
        {
          days: ['mon', 'wed'] as any,
          start_time: '13:30',
          end_time: '14:45',
          location: 'DH 250',
          is_tba: false,
        },
      ],
    }
    render(<SectionDetails section={sectionWith24h} />)
    expect(screen.getByText(/Mon, Wed · 1:30 PM–2:45 PM · DH 250/)).toBeDefined()
  })

  it('renders availability status and seat count', () => {
    render(<SectionDetails section={mockSection} />)
    expect(screen.getByText('5 open seats')).toBeDefined()
  })

  it('renders section notes when present', () => {
    render(<SectionDetails section={mockSection} />)
    expect(screen.getByText('Class includes mandatory lab attendance.')).toBeDefined()
  })

  it('hides section notes when showNotes is false', () => {
    render(<SectionDetails section={mockSection} showNotes={false} />)
    expect(screen.queryByText('Class includes mandatory lab attendance.')).toBeNull()
  })
})

describe('EligibilityDetails', () => {
  it('renders eligibility badge and satisfied notice when conditions apply', () => {
    const value: Eligibility = {
      course_id: 'CMPE-131',
      status: 'eligible',
      reasons: ['Prerequisites satisfied: CMPE 126 completed with grade B+'],
      missing_course_ids: [],
    }
    render(<EligibilityDetails value={value} />)
    expect(screen.getByText(/Prerequisites satisfied: CMPE 126/)).toBeDefined()
  })

  it('renders missing credit warning when student is ineligible', () => {
    const value: Eligibility = {
      course_id: 'CMPE-131',
      status: 'ineligible',
      reasons: ['Missing prerequisite course'],
      missing_course_ids: ['CMPE-126'],
    }
    render(<EligibilityDetails value={value} />)
    expect(screen.getByText('Missing credit: CMPE-126')).toBeDefined()
  })
})
