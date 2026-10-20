import { apiRequest, queryString } from './client'
import type { Page, WatchlistEntry, WatchlistQuery } from './types'

// - GET /api/me/watchlist.
// - Sort added_at DESC then section ID ASC. Optional term filter before pagination.
// - WatchlistQuery: {limit?: number, offset?: number, term?: string}.
// - WatchlistEntry: {section: Section, added_at: string, eligibility: Eligibility}.
export function listWatchlist(query: WatchlistQuery = {}): Promise<Page<WatchlistEntry>> {
  return apiRequest<Page<WatchlistEntry>>('/me/watchlist' + queryString(query))
}

// - PUT /api/me/watchlist/{sectionId}.
// - 201 new, 200 existing/reactivated. No body. Eligibility warnings do not block saving.
export function addWatch(sectionId: string): Promise<WatchlistEntry> {
  return apiRequest<WatchlistEntry>(`/me/watchlist/${encodeURIComponent(sectionId)}`, { method: 'PUT' })
}

// - DELETE /api/me/watchlist/{sectionId}.
// - 204, including repeat removal. No body and no JSON response.
export function removeWatch(sectionId: string): Promise<void> {
  return apiRequest<void>(`/me/watchlist/${encodeURIComponent(sectionId)}`, { method: 'DELETE' })
}
