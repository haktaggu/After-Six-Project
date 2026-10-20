import { useState } from 'react'
import type { Page, PageProps, WatchlistEntry, WatchlistQuery } from '../shared/api/types'
import './Watchlist.css'
import NotificationPreferences from '../components/NotificationPreferences'
import NotificationHistory from '../components/NotificationHistory'

// - shared/api/watchlist.listWatchlist(query)->Page<WatchlistEntry>. Order added_at DESC then
//   section ID ASC; optional term filter.
// - Render nested section, freshness and eligibility warnings. Empty list gets a useful empty
//   state; loading/failure are different.
// - WatchlistQuery: {limit?: number, offset?: number, term?: string}.
// - WatchlistEntry: {section: Section, added_at: string, eligibility: Eligibility}.
async function loadWatchlist(query: WatchlistQuery = {}): Promise<Page<WatchlistEntry>> {
  void [query]
  throw new Error('loadWatchlist is not implemented')
}

// - shared/api/watchlist.removeWatch(sectionId)->void, including repeat delete. Mark only the row
//   pending; retain it on error.
// - After success reload the page; step back a page if removal emptied the last one. Warnings
//   never block adding a watch.
async function handleRemove(sectionId: string): Promise<void> {
  void [sectionId]
  throw new Error('handleRemove is not implemented')
}

// - Use a nonnegative offset and existing filter/limit. Call listWatchlist({...query,offset}).
//   total counts all matches, not the current page length.
async function changePage(offset: number, query: WatchlistQuery): Promise<Page<WatchlistEntry>> {
  void [offset, query]
  throw new Error('changePage is not implemented')
}

const actions = { loadWatchlist, handleRemove, changePage }

export default function Watchlist(props: PageProps = {}) {
  const [notice, setNotice] = useState('')
  void props
  return (
    <section className="watchlist-page">
      <h1>Watchlist</h1>
      <p>Section monitoring will be built here.</p>
      <button type="button" disabled onClick={() => {
        void actions.loadWatchlist().catch((error: unknown) => setNotice(error instanceof Error ? error.message : 'Request failed'))
      }}>Refresh</button>
      <NotificationPreferences />
      <NotificationHistory />
      {notice && <p role="alert">{notice}</p>}
    </section>
  )
}
