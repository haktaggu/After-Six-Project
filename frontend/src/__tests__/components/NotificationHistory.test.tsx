import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, waitFor, cleanup } from '@testing-library/react'
import NotificationHistory from '../../components/NotificationHistory'
import * as notifApi from '../../shared/api/notifications'

vi.mock('../../shared/api/notifications')

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('NotificationHistory', () => {
  it('renders "No alerts yet." when there are zero notifications', async () => {
    vi.spyOn(notifApi, 'listNotifications').mockResolvedValue({
      items: [],
      total: 0,
      limit: 10,
      offset: 0,
    })

    render(<NotificationHistory />)

    await waitFor(() => {
      expect(screen.getByText('No alerts yet.')).toBeDefined()
    })
  })

  it('renders notifications in API chronological order (BUG-003 regression fix)', async () => {
    vi.spyOn(notifApi, 'listNotifications').mockResolvedValue({
      items: [
        {
          id: 'notif-newer',
          section_id: 'CMPE-131-01',
          event_type: 'section_opened',
          status: 'sent',
          created_at: '2026-11-15T10:00:00Z',
          sent_at: '2026-11-15T10:00:05Z',
        },
        {
          id: 'notif-older',
          section_id: 'CMPE-130-02',
          event_type: 'section_opened',
          status: 'sent',
          created_at: '2026-11-14T09:00:00Z',
          sent_at: '2026-11-14T09:00:05Z',
        },
      ],
      total: 2,
      limit: 10,
      offset: 0,
    })

    render(<NotificationHistory />)

    await waitFor(() => {
      expect(screen.getByText('CMPE-131-01')).toBeDefined()
      expect(screen.getByText('CMPE-130-02')).toBeDefined()
    })

    // Verify ordering: newer alert must appear before older alert in DOM order
    const listItems = screen.getAllByRole('listitem')
    expect(listItems[0].textContent).toContain('CMPE-131-01')
    expect(listItems[1].textContent).toContain('CMPE-130-02')
  })
})
