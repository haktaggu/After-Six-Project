import { ApiClientError } from '../shared/api/client'

export function ErrorNotice({ error }: { error: unknown }) {
  if (!error) return null
  return <div className="notice error" role="alert">
    <p>{error instanceof Error ? error.message : String(error)}</p>
    {error instanceof ApiClientError && error.fields.length > 0 && <ul>{error.fields.map((f, i) => <li key={i}>{f.path}: {f.message}</li>)}</ul>}
  </div>
}

export function Pagination({ total, offset, limit, loading, onPage, start }: {
  total: number; offset: number; limit: number; loading?: boolean; onPage: (offset: number) => void; start?: number
}) {
  return <div className="pagination" aria-label="Result pages">
    <span>{total ? `${start ?? offset + 1}–${Math.min(offset + limit, total)} of ${total}` : '0 results'}</span>
    <div className="actions">
      <button type="button" disabled={loading || offset === 0} onClick={() => onPage(Math.max(0, offset - limit))}>Previous</button>
      <button type="button" disabled={loading || offset + limit >= total} onClick={() => onPage(offset + limit)}>Next</button>
    </div>
  </div>
}
