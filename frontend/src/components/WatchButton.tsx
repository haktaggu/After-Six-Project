import { useState } from 'react'
import { addWatch } from '../shared/api/watchlist'
import type { WatchlistEntry } from '../shared/api/types'
import { ErrorNotice } from './Feedback'

export default function WatchButton({ sectionId, onAdded }: { sectionId: string; onAdded?: (watch: WatchlistEntry) => void }) {
  const [pending, setPending] = useState(false)
  const [saved, setSaved] = useState<WatchlistEntry | null>(null)
  const [error, setError] = useState<unknown>(null)
  async function add() {
    setPending(true)
    setError(null)
    try {
      const res = await addWatch(sectionId)
      setSaved(res)
      onAdded?.(res)
    } catch (err) { setError(err) }
    finally { setPending(false) }
  }
  return <div>
    <button type="button" disabled={pending || !!saved} onClick={() => { void add() }}>{pending ? 'Saving…' : saved ? 'Watching' : 'Watch section'}</button>
    {saved && saved.eligibility.status !== 'eligible' && <p className="muted" role="status">Saved ({saved.eligibility.status})</p>}
    <ErrorNotice error={error} />
  </div>
}
