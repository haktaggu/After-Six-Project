import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, fireEvent, cleanup } from '@testing-library/react'
import { ErrorNotice, Pagination } from '../../components/Feedback'
import { ApiClientError } from '../../shared/api/client'

afterEach(cleanup)

describe('ErrorNotice', () => {
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
  it('shows the result range and moves between pages', () => {
    const onPage = vi.fn()
    const { rerender } = render(<Pagination total={204} offset={0} limit={25} onPage={onPage} />)
    expect(screen.getByText('1–25 of 204')).toBeDefined()
    expect(screen.getByRole<HTMLButtonElement>('button', { name: 'Previous' }).disabled).toBe(true)
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    expect(onPage).toHaveBeenCalledWith(25)

    rerender(<Pagination total={204} offset={200} limit={25} onPage={onPage} />)
    expect(screen.getByText('201–204 of 204')).toBeDefined()
    expect(screen.getByRole<HTMLButtonElement>('button', { name: 'Next' }).disabled).toBe(true)
  })
})
