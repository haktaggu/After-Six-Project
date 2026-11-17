import { useCallback, useState } from 'react'
import { listCourseRecords } from '../shared/api/accounts'
import { listTerms } from '../shared/api/courses'
import { allPages } from '../shared/api/lookups'
import { useLoad } from '../shared/hooks/useLoad'
import type { PageProps } from '../shared/api/types'
import { ErrorNotice, Pagination } from '../components/Feedback'
import RecordEditor from '../components/RecordEditor'

export default function CourseHistory({ onNavigate }: PageProps) {
  const [offset, setOffset] = useState(0)
  const load = useCallback(async () => {
    const [terms, records] = await Promise.all([allPages(listTerms), listCourseRecords({ limit: 10, offset })])
    return { terms, records }
  }, [offset])
  const { data, error, loading, reload } = useLoad(load)

  function refreshHistory() {
    if (data?.records.items.length === 1 && offset > 0) setOffset(Math.max(0, offset - 10))
    else reload()
  }

  return <section>
    <div className="page-heading">
      <h1>Course history</h1>
      <button className="primary" onClick={() => onNavigate?.('Add Course')}>Add a course</button>
    </div>
    <ErrorNotice error={error} />
    {loading && <p role="status">Loading course history…</p>}
    {data && <section>
        {!data.records.items.length && !loading && (
          <div className="empty">
            <p>No course records yet.</p>
          </div>
        )}
        {data.records.items.map(record => (
          <details className="history-row" key={record.course_id}>
            <summary>
              <span className="history-summary">
                <strong>{record.course_id}</strong>
                <span className="history-statuses">
                  <span className={`status ${record.status}`}>{record.status.replace('_', ' ')}</span>
                  {record.grade && <span className="status grade">Grade: {record.grade}</span>}
                  {record.status === 'completed' && (
                    <span className="status">
                      {record.earned_units != null
                        ? `${record.earned_units} earned units`
                        : record.grade ? 'Units missing or variable' : 'Grade needed'}
                    </span>
                  )}
                </span>
              </span>
            </summary>
            <RecordEditor record={record} courseId={record.course_id} terms={data.terms} onSaved={reload} onRemoved={refreshHistory} onNavigate={onNavigate} />
          </details>
        ))}
        <Pagination total={data.records.total} offset={offset} limit={10} loading={loading} onPage={setOffset} />
      </section>}
  </section>
}
