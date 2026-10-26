import { apiRequest, queryString } from './client'
import type { Notification, NotificationPreferences, Page, PaginationQuery, PreferencesUpdate } from './types'

export function getPreferences(): Promise<NotificationPreferences> {
  return apiRequest<NotificationPreferences>('/me/notification-preferences')
}

export function updatePreferences(body: PreferencesUpdate): Promise<NotificationPreferences> {
  return apiRequest<NotificationPreferences>('/me/notification-preferences', { method: 'PATCH', body })
}

export function listNotifications(query: PaginationQuery = {}): Promise<Page<Notification>> {
  return apiRequest<Page<Notification>>('/me/notifications' + queryString(query))
}
