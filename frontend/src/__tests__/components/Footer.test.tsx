import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import Footer from '../../components/Footer'

describe('Footer', () => {
  it('renders student project disclaimer', () => {
    render(<Footer />)
    expect(
      screen.getByText(/Independent student project\. Not affiliated with or endorsed by San José State University\./)
    ).toBeDefined()
  })
})
