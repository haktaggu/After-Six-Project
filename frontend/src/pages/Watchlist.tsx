import { useCallback, useState } from 'react'
import { listWatchlist, removeWatch } from '../shared/api/watchlist'
import { listTerms } from '../shared/api/courses'
import { allPages } from '../shared/api/lookups'
import { useLoad } from '../shared/hooks/useLoad'
import type { PageProps } from '../shared/api/types'
import NotificationPreferences from '../components/NotificationPreferences'
import NotificationHistory from '../components/NotificationHistory'
import SectionDetails, { EligibilityDetails } from '../components/SectionDetails'
import { ErrorNotice, Pagination } from '../components/Feedback'
import './Watchlist.css'

export default function Watchlist({ onNavigate }: PageProps) {
  const [term, setTerm] = useState('')
  const [offset, setOffset] = useState(0)
  const [pending, setPending] = useState<string[]>([])
  const [error, setError] = useState<unknown>(null)
  const terms = useLoad(useCallback(() => allPages(listTerms), []))
  const { data, error: loadError, loading, reload } = useLoad(useCallback((signal: AbortSignal) => listWatchlist({ term: term || undefined, offset, limit: 10 }, signal), [term, offset]))
  async function remove(id: string) {
    setPending(curr => [...curr, id]); setError(null)
    try {
      await removeWatch(id)
      if (data?.items.length === 1 && offset > 0) setOffset(Math.max(0, offset - 10))
      else reload()
    } catch (err) { setError(err) }
    finally { setPending(curr => curr.filter(idx => idx !== id)) }
  }
  return <section className="watchlist-page">
    <div className="page-heading"><h1>Your watchlist</h1><button disabled={loading} onClick={reload}>Refresh watchlist</button></div>
    <div className="watchlist-layout"><div><label>Filter by term<select value={term} onChange={e => { setTerm(e.target.value); setOffset(0) }}><option value="">All terms</option>{terms.data?.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}</select></label>
      <ErrorNotice error={terms.error} /><ErrorNotice error={loadError} /><ErrorNotice error={error} />{loading && <p role="status">Loading watched sections…</p>}
      {data && <><h2>{data.total} watched section{data.total === 1 ? '' : 's'}</h2>{!data.items.length && !loading && <div className="empty"><p>No watched sections match this view.</p><button onClick={() => onNavigate?.('Search')}>Find a section to watch</button></div>}
        {data.items.map(w => <article className="section-row" key={w.section.id}><div className="section-heading"><div><h3>{w.section.course.id} · Section {w.section.section_number}</h3><p>{w.section.course.title}</p></div><button disabled={pending.includes(w.section.id)} onClick={() => { void remove(w.section.id) }}>{pending.includes(w.section.id) ? 'Removing…' : 'Remove watch'}</button></div>
          <SectionDetails section={w.section} showNotes={false} /><EligibilityDetails value={w.eligibility} />
        </article>)}<Pagination total={data.total} offset={offset} limit={10} loading={loading} onPage={setOffset} /></>}
    </div><aside><NotificationPreferences /><NotificationHistory /></aside></div>
  </section>
}