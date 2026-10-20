import { useState } from 'react'
import type { WatchlistEntry } from '../shared/api/types'

interface WatchButtonProps {
  sectionId: string
  onAdded?: (watch: WatchlistEntry) => void
}

// - shared/api/watchlist.addWatch(sectionId)->WatchlistEntry; PUT has no body.
// - 201 means new, 200 existing/reactivated. Duplicate clicks must not duplicate watches.
// - Entry contains section:Section, added_at:UTC string, eligibility:{course_id,status,
//   reasons:string[],missing_course_ids:string[]}. Unknown/ineligible warns but doesn't block.
// - Keep the row pending while adding; surface failure without pretending success.
async function handleAdd(sectionId: string): Promise<WatchlistEntry> {
  void sectionId
  throw new Error('Adding watches is not implemented')
}

// - sectionId is the exact string from Section.id; onAdded lets the caller refresh.
// - Show pending/saved/error states and a visible keyboard focus.
export default function WatchButton({ sectionId, onAdded }: WatchButtonProps) {
  const [notice, setNotice] = useState('')
  return <>
    <button type="button" disabled onClick={() => {
      void handleAdd(sectionId).then(watch => onAdded?.(watch))
        .catch((error: unknown) => setNotice(error instanceof Error ? error.message : 'Request failed'))
    }}>Add to watchlist</button>
    {notice && <span role="alert">{notice}</span>}
  </>
}
