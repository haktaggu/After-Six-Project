import { useState } from 'react'
import { addWatch } from '../shared/api/watchlist'
import type { WatchlistEntry, Eligibility } from '../shared/api/types'
import { ErrorNotice } from './Feedback'

// Reusable helper to correct 'unknown' to 'ineligible' if specific mismatches exist
function getDisplayStatus(eligibility: Eligibility) {
  if (eligibility.status !== 'unknown') return eligibility.status;

  const coreReasons = eligibility.reasons.filter(r => {
    const lower = r.toLowerCase()
    if (lower.includes('needs confirmation: major restriction:') && lower.split(':').length === 3) return false
    if (lower.includes('needs confirmation: math enrollment category')) return false
    return true
  })

  const hasSpecificMismatch = coreReasons.some(r => {
    const lower = r.toLowerCase()
    return lower.includes('requires major eq') || lower.includes('actual:')
  })

  if (hasSpecificMismatch || eligibility.missing_course_ids.length > 0) {
    return 'ineligible'
  }
  return 'unknown'
}

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

  const displayStatus = saved ? getDisplayStatus(saved.eligibility) : null

  return <div>
    <button type="button" disabled={pending || !!saved} onClick={() => { void add() }}>
      {pending ? 'Saving…' : saved ? 'Watching' : 'Watch section'}
    </button>

    {saved && displayStatus !== 'eligible' && (
      <p className="muted" role="status">Saved ({displayStatus})</p>
    )}

    <ErrorNotice error={error} />
  </div>
}