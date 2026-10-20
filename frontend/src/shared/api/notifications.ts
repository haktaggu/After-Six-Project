import { apiRequest, queryString } from './client'
import type { Notification, NotificationPreferences, Page, PaginationQuery, PreferencesUpdate } from './types'

// - GET /api/me/notification-preferences -> {enabled: boolean, available: boolean}.
// - The Discord destination stays on the backend.
export function getPreferences(): Promise<NotificationPreferences> {
  return apiRequest<NotificationPreferences>('/me/notification-preferences')
}

// - PATCH /api/me/notification-preferences with {enabled: boolean}.
// - 503 CHANNEL_UNAVAILABLE when enabling without a configured Discord webhook.
export function updatePreferences(body: PreferencesUpdate): Promise<NotificationPreferences> {
  return apiRequest<NotificationPreferences>('/me/notification-preferences', { method: 'PATCH', body })
}

// - GET /api/me/notifications; sort created_at DESC then ID ASC, count before pagination.
// - Notification: {id,section_id,event_type:'section_opened',status:'pending'|'sent'|'failed',
//   created_at:UTC string,sent_at:UTC string|null}. sent means provider acceptance, not read.
// - Query is {limit?:number,offset?:number}; defaults 25/0. Empty history returns items=[].
export function listNotifications(query: PaginationQuery = {}): Promise<Page<Notification>> {
  return apiRequest<Page<Notification>>('/me/notifications' + queryString(query))
}
