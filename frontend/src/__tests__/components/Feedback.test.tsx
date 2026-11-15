import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, fireEvent, cleanup } from '@testing-library/react'
import { ErrorNotice, Pagination } from '../../components/Feedback'
import { ApiClientError } from '../../shared/api/client'

afterEach(() => {
  cleanup()
})

describe('ErrorNotice', () => {
  it('renders nothing when there is no error', () => {
    const { container } = render(<ErrorNotice error={null} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders error message for generic Error', () => {
    render(<ErrorNotice error={new Error('Network disconnected')} />)
    expect(screen.getByText('Network disconnected')).toBeDefined()
  })

  it('renders field-specific errors for ApiClientError', () => {
    const err = new ApiClientError(422, 'VALIDATION_ERROR', 'Invalid request body', [
      { path: 'term', message: 'Term is required' },
      { path: 'limit', message: 'Limit must be positive' },
    ])
    render(<ErrorNotice error={err} />)
    expect(screen.getByText('Invalid request body')).toBeDefined()
    expect(screen.getByText('term: Term is required')).toBeDefined()
    expect(screen.getByText('limit: Limit must be positive')).toBeDefined()
  })
})

describe('Pagination', () => {
  it('displays "0 results" when total is 0', () => {
    render(<Pagination total={0} offset={0} limit={25} onPage={() => {}} />)
    expect(screen.getByText('0 results')).toBeDefined()
  })

  it('defaults start index to offset + 1 (BUG-001 regression fix)', () => {
    render(<Pagination total={204} offset={0} limit={25} onPage={() => {}} />)
    expect(screen.getByText('1–25 of 204')).toBeDefined()
  })

  it('calculates the correct range for middle pages', () => {
    render(<Pagination total={204} offset={25} limit={25} onPage={() => {}} />)
    expect(screen.getByText('26–50 of 204')).toBeDefined()
  })

  it('caps the upper range at the total count on the last page', () => {
    render(<Pagination total={204} offset={200} limit={25} onPage={() => {}} />)
    expect(screen.getByText('201–204 of 204')).toBeDefined()
  })

  it('disables previous button on the first page', () => {
    render(<Pagination total={204} offset={0} limit={25} onPage={() => {}} />)
    const prev = screen.getByRole('button', { name: 'Previous' }) as HTMLButtonElement
    expect(prev.disabled).toBe(true)
  })

  it('disables next button on the last page', () => {
    render(<Pagination total={204} offset={200} limit={25} onPage={() => {}} />)
    const next = screen.getByRole('button', { name: 'Next' }) as HTMLButtonElement
    expect(next.disabled).toBe(true)
  })

  it('calls onPage callback with next page offset', () => {
    const onPage = vi.fn()
    render(<Pagination total={204} offset={0} limit={25} onPage={onPage} />)
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    expect(onPage).toHaveBeenCalledWith(25)
  })
})
