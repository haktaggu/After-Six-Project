import { useCallback, useState } from 'react'
import { listNotifications } from '../shared/api/notifications'
import { useLoad } from '../shared/hooks/useLoad'
import { ErrorNotice, Pagination } from './Feedback'

export default function NotificationHistory() {
  const [offset, setOffset] = useState(0)
  const { data, error, loading, reload } = useLoad(useCallback(() => listNotifications({ limit: 10, offset }), [offset]))
  return <section className="notification-history"><div className="results-heading"><h2>Recent alerts</h2><button disabled={loading} onClick={reload}>Refresh alerts</button></div>
    <ErrorNotice error={error} />{loading && <p role="status">Loading alerts…</p>}
    {data && <>{!data.items.length && !loading && <p className="empty">No alerts yet.</p>}
      <ul className="notification-list">{[...data.items].reverse().map(n => <li key={n.id}><div><strong>{n.section_id}</strong><span className={`status ${n.status}`}>{n.status}</span></div><p>{new Date(n.created_at).toLocaleString()}{n.sent_at ? ` · Sent ${new Date(n.sent_at).toLocaleString()}` : ''}</p></li>)}</ul>
      {data.total > 10 && <Pagination total={data.total} offset={offset} limit={10} loading={loading} onPage={setOffset} />}</>}
  </section>
}
