import { describe, it, expect, afterEach } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import SectionComparison from '../../components/SectionComparison'
import type { Section } from '../../shared/api/types'

afterEach(() => {
  cleanup()
})

const mockSections: Section[] = [
  {
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
      description: 'Intro to SE',
      units_min: 3,
      units_max: 3,
      prerequisite_text: null,
      corequisite_text: null,
      restrictions_text: null,
      catalog_url: null,
    },
    meetings: [],
    instructors: [{ name: 'Dr. Smith' }],
    notes: null,
    source_url: '',
    last_checked_at: null,
    is_stale: false,
  },
  {
    id: 'sec-2',
    term: 'fall-2026',
    class_number: '48202',
    section_number: '02',
    title: 'Software Engineering I',
    mode: 'Online',
    units: 3,
    open_seats: 0,
    availability: 'closed',
    course: {
      id: 'CMPE-131',
      subject: 'CMPE',
      catalog_number: '131',
      title: 'Software Engineering I',
      description: 'Intro to SE',
      units_min: 3,
      units_max: 3,
      prerequisite_text: null,
      corequisite_text: null,
      restrictions_text: null,
      catalog_url: null,
    },
    meetings: [],
    instructors: [{ name: 'Prof. Johnson' }],
    notes: null,
    source_url: '',
    last_checked_at: null,
    is_stale: false,
  },
]

describe('SectionComparison', () => {
  it('renders side-by-side cards for both selected sections', () => {
    render(<SectionComparison sections={mockSections} />)
    expect(screen.getByRole('heading', { level: 2, name: 'Compare sections' })).toBeDefined()
    expect(screen.getByText('CMPE-131 · Section 01')).toBeDefined()
    expect(screen.getByText('CMPE-131 · Section 02')).toBeDefined()
    expect(screen.getByText('Dr. Smith')).toBeDefined()
    expect(screen.getByText('Prof. Johnson')).toBeDefined()
  })
})
