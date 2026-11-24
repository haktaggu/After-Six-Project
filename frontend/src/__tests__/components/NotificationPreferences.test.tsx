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

  it('loads existing webhook URL and saves changes', async () => {
    const updateSpy = vi.spyOn(notifApi, 'updatePreferences').mockResolvedValue({
      enabled: true,
      available: true,
      webhook_url: 'https://discord.com/api/webhooks/123/abc',
    })
    vi.spyOn(notifApi, 'getPreferences').mockResolvedValue({
      enabled: true,
      available: true,
      webhook_url: 'https://discord.com/api/webhooks/123/abc',
    })

    render(<NotificationPreferences />)

    await waitFor(() => {
      const input = screen.getByPlaceholderText('https://discord.com/api/webhooks/...') as HTMLInputElement
      expect(input.value).toBe('https://discord.com/api/webhooks/123/abc')
    })

    const saveButton = screen.getByRole('button', { name: 'Save webhook' })
    fireEvent.click(saveButton)

    await waitFor(() => {
      expect(screen.getByText('Discord alerts enabled.')).toBeDefined()
    })

    expect(updateSpy).toHaveBeenCalledWith({
      enabled: true,
      webhook_url: 'https://discord.com/api/webhooks/123/abc',
    })
  })

  it('masks webhook URL by default and toggles visibility', async () => {
    vi.spyOn(notifApi, 'getPreferences').mockResolvedValue({
      enabled: true,
      available: true,
      webhook_url: 'https://discord.com/api/webhooks/123/abc',
    })

    render(<NotificationPreferences />)

    await waitFor(() => {
      const input = screen.getByPlaceholderText('https://discord.com/api/webhooks/...') as HTMLInputElement
      expect(input.type).toBe('password')
    })

    const toggleBtn = screen.getByRole('button', { name: 'Show webhook URL' })
    fireEvent.click(toggleBtn)

    const input = screen.getByPlaceholderText('https://discord.com/api/webhooks/...') as HTMLInputElement
    expect(input.type).toBe('text')
    expect(screen.getByRole('button', { name: 'Hide webhook URL' })).toBeDefined()
  })
})
