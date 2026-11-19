import { useCallback, useState } from 'react'
import { listNotifications, markNotificationRead } from '../shared/api/notifications'
import { useLoad } from '../shared/hooks/useLoad'
import { ErrorNotice, Pagination } from './Feedback'

export default function NotificationHistory() {
  const [offset, setOffset] = useState(0)
  const [pendingId, setPendingId] = useState<string | null>(null)
  const { data, error, loading, reload } = useLoad(useCallback(() => listNotifications({ limit: 10, offset }), [offset]))

  async function handleMarkRead(id: string) {
    setPendingId(id)
    try {
      await markNotificationRead(id)
      reload()
    } catch {
      // ignore
    } finally {
      setPendingId(null)
    }
  }

  return <section className="notification-history"><div className="results-heading"><h2>Recent alerts</h2><button disabled={loading} onClick={reload}>Refresh alerts</button></div>
    <ErrorNotice error={error} />{loading && <p role="status">Loading alerts…</p>}
    {data && <>{!data.items.length && !loading && <p className="empty">No alerts yet.</p>}
      <ul className="notification-list">{data.items.map(n => <li key={n.id} className={n.is_read ? 'read' : 'unread'}>
        <div>
          <strong>{n.section_id}</strong>
          <div>
            <span className={`status ${n.status}`}>{n.status}</span>
            {n.is_read === false && <span className="status new">Unread</span>}
          </div>
        </div>
        <p>{new Date(n.created_at).toLocaleString()}{n.sent_at ? ` · Sent ${new Date(n.sent_at).toLocaleString()}` : ''}</p>
        {n.is_read === false && <button className="mark-read-btn" type="button" disabled={pendingId === n.id} onClick={() => void handleMarkRead(n.id)}>{pendingId === n.id ? 'Marking…' : 'Mark read'}</button>}
      </li>)}</ul>
      {data.total > 10 && <Pagination total={data.total} offset={offset} limit={10} loading={loading} onPage={setOffset} />}</>}
  </section>
}