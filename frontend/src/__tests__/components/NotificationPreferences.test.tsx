import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react'
import NotificationPreferences from '../../components/NotificationPreferences'
import * as notifApi from '../../shared/api/notifications'

vi.mock('../../shared/api/notifications')

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('NotificationPreferences', () => {
  it('renders preference checkbox with loaded state', async () => {
    vi.spyOn(notifApi, 'getPreferences').mockResolvedValue({
      enabled: true,
      available: true,
    })

    render(<NotificationPreferences />)

    await waitFor(() => {
      const checkbox = screen.getByRole('checkbox') as HTMLInputElement
      expect(checkbox.checked).toBe(true)
    })
  })

  it('updates preference and displays confirmation when toggled', async () => {
    vi.spyOn(notifApi, 'getPreferences').mockResolvedValue({
      enabled: false,
      available: true,
    })
    vi.spyOn(notifApi, 'updatePreferences').mockResolvedValue({
      enabled: true,
      available: true,
    })

    render(<NotificationPreferences />)

    await waitFor(() => {
      expect(screen.getByRole('checkbox')).toBeDefined()
    })

    const checkbox = screen.getByRole('checkbox')
    fireEvent.click(checkbox)

    await waitFor(() => {
      expect(screen.getByText('Discord alerts enabled.')).toBeDefined()
    })
  })

  it('shows help text when Discord notifications are unavailable', async () => {
    vi.spyOn(notifApi, 'getPreferences').mockResolvedValue({
      enabled: false,
      available: false,
    })

    render(<NotificationPreferences />)

    await waitFor(() => {
      expect(screen.getByText('Discord notifications are unavailable.')).toBeDefined()
    })
  })
})
