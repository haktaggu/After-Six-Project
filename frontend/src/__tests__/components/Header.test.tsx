import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, fireEvent, cleanup } from '@testing-library/react'
import Header from '../../components/Header'
import type { User } from '../../shared/api/types'

afterEach(() => {
  cleanup()
})

const mockUser: User = {
  id: 'usr-1',
  email: 'student@sjsu.edu',
  full_name: 'Test Student',
  created_at: '2026-08-20T10:00:00Z',
}

describe('Header', () => {
  it('renders branding and project slogan', () => {
    render(<Header selectedPage="Search" onNavigate={() => {}} />)
    expect(screen.getByText('OurSJSU')).toBeDefined()
    expect(screen.getByText(/"It's like MySJSU, but we do it/)).toBeDefined()
  })

  it('disables navigation links when user is not logged in', () => {
    render(<Header selectedPage="Login" onNavigate={() => {}} />)
    const searchBtn = screen.getByRole('button', { name: 'Search' }) as HTMLButtonElement
    expect(searchBtn.disabled).toBe(true)
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeDefined()
  })

  it('enables navigation and triggers onNavigate when authenticated', () => {
    const onNavigate = vi.fn()
    render(<Header selectedPage="Dashboard" onNavigate={onNavigate} user={mockUser} />)
    const searchBtn = screen.getByRole('button', { name: 'Search' }) as HTMLButtonElement
    expect(searchBtn.disabled).toBe(false)
    fireEvent.click(searchBtn)
    expect(onNavigate).toHaveBeenCalledWith('Search')
  })

  it('renders logout button and handles sign out clicks', () => {
    const onSignOut = vi.fn()
    render(<Header selectedPage="Dashboard" onNavigate={() => {}} user={mockUser} onSignOut={onSignOut} />)
    const logoutBtn = screen.getByRole('button', { name: 'Logout' })
    fireEvent.click(logoutBtn)
    expect(onSignOut).toHaveBeenCalledTimes(1)
  })

  it('shows logging out state while signing out', () => {
    render(<Header selectedPage="Dashboard" onNavigate={() => {}} user={mockUser} signingOut={true} />)
    expect(screen.getByText('Logging out…')).toBeDefined()
  })
})
