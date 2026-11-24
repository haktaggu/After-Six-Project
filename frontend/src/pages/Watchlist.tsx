import { useCallback, useEffect, useState } from 'react'
import { listWatchlist, removeWatch } from '../shared/api/watchlist'
import { listTerms } from '../shared/api/courses'
import { allPages } from '../shared/api/lookups'
import { useLoad } from '../shared/hooks/useLoad'
import type { PageProps } from '../shared/api/types'
import NotificationHistory from '../components/NotificationHistory'
import SectionDetails, { EligibilityDetails } from '../components/SectionDetails'
import { ErrorNotice, Pagination } from '../components/Feedback'
import './Watchlist.css'

const pageSize = 10

export default function Watchlist({ onNavigate, target }: PageProps) {
  const [term, setTerm] = useState('')
  const [offset, setOffset] = useState(0)
  const [pending, setPending] = useState<string[]>([])
  const [error, setError] = useState<unknown>(null)

  const terms = useLoad(useCallback(() => allPages(listTerms), []))
  const loadWatchlist = useCallback((signal: AbortSignal) => {
    return listWatchlist({ term: term || undefined, offset, limit: pageSize }, signal)
  }, [term, offset])
  const { data, error: loadError, loading, reload } = useLoad(loadWatchlist)

  useEffect(() => {
    if (target && data) document.getElementById(`watched-${target}`)?.focus()
  }, [target, data])

  function changeTerm(nextTerm: string) {
    setTerm(nextTerm)
    setOffset(0)
  }

  async function removeSection(sectionId: string) {
    setPending(ids => [...ids, sectionId])
    setError(null)
    try {
      await removeWatch(sectionId)
      if (data?.items.length === 1 && offset > 0) {
        setOffset(Math.max(0, offset - pageSize))
      } else {
        reload()
      }
    } catch (err) {
      setError(err)
    } finally {
      setPending(ids => ids.filter(id => id !== sectionId))
    }
  }

  return (
    <section className="watchlist-page">
      <div className="page-heading">
        <h1>Your watchlist</h1>
        <button disabled={loading} onClick={reload}>Refresh watchlist</button>
      </div>
      <div className="watchlist-layout">
        <div>
          <label>
            Filter by term
            <select value={term} onChange={event => changeTerm(event.target.value)}>
              <option value="">All terms</option>
              {terms.data?.map(term => <option key={term.id} value={term.id}>{term.name}</option>)}
            </select>
          </label>
          <ErrorNotice error={terms.error} />
          <ErrorNotice error={loadError} />
          <ErrorNotice error={error} />
          {loading && <p role="status">Loading watched sections…</p>}
          {data && (
            <>
              <h2>{data.total} watched section{data.total === 1 ? '' : 's'}</h2>
              {!data.items.length && !loading && (
                <div className="empty">
                  <p>No watched sections match this view.</p>
                  <button onClick={() => onNavigate?.('Search')}>Find a section to watch</button>
                </div>
              )}
              {data.items.map(({ section, eligibility }) => {
                const removing = pending.includes(section.id)
                return (
                  <article className="section-row" key={section.id} id={`watched-${section.id}`} tabIndex={-1}>
                    <div className="section-heading">
                      <div>
                        <h3>{section.course.id} · Section {section.section_number}</h3>
                        <p>{section.course.title}</p>
                      </div>
                      <button disabled={removing} onClick={() => void removeSection(section.id)}>
                        {removing ? 'Removing…' : 'Remove watch'}
                      </button>
                    </div>
                    <SectionDetails section={section} showNotes={false} />
                    <EligibilityDetails value={eligibility} onNavigate={onNavigate} />
                  </article>
                )
              })}
              <Pagination total={data.total} offset={offset} limit={pageSize} loading={loading} onPage={setOffset} />
            </>
          )}
        </div>
        <aside><NotificationHistory /></aside>
      </div>
    </section>
  )
}
