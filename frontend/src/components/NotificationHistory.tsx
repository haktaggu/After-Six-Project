import { useState } from 'react'
import type { Notification, Page, PaginationQuery } from '../shared/api/types'

// - shared/api/notifications.listNotifications(query) returns Page<Notification>.
// - Query {limit?:number,offset?:number} defaults to 25/0. Show the latest deliveries without
//   filter controls; keep loading, empty and failed states distinct.
// - Notification fields: id,section_id,event_type='section_opened',status pending/sent/failed,
//   created_at UTC,sent_at UTC|null. Sort is created_at DESC then ID ASC.
// - sent means Discord accepted the request; leave a missing sent_at blank.
async function loadNotifications(query: PaginationQuery = {}): Promise<Page<Notification>> {
  void query
  throw new Error('loadNotifications is not implemented')
}

const actions = { loadNotifications }

export default function NotificationHistory() {
  const [notice, setNotice] = useState('')
  return <section>
    <h2>Recent alerts</h2>
    <button type="button" disabled onClick={() => {
      void actions.loadNotifications().catch((error: unknown) => setNotice(error instanceof Error ? error.message : 'Request failed'))
    }}>Refresh</button>
    {notice && <p role="alert">{notice}</p>}
  </section>
}
