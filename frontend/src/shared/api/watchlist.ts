import { apiRequest, queryString } from './client'
import type { Page, WatchlistEntry, WatchlistQuery } from './types'

export function listWatchlist(query: WatchlistQuery = {}, signal?: AbortSignal): Promise<Page<WatchlistEntry>> {
  return apiRequest<Page<WatchlistEntry>>('/me/watchlist' + queryString(query), { signal })
}

export function addWatch(sectionId: string): Promise<WatchlistEntry> {
  return apiRequest<WatchlistEntry>(`/me/watchlist/${encodeURIComponent(sectionId)}`, { method: 'PUT' })
}

export function removeWatch(sectionId: string): Promise<void> {
  return apiRequest<void>(`/me/watchlist/${encodeURIComponent(sectionId)}`, { method: 'DELETE' })
}
