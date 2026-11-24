import { useCallback, useState } from 'react'
import { listCourses, listTerms } from '../shared/api/courses'
import { allPages } from '../shared/api/lookups'
import { listCourseRecords } from '../shared/api/accounts'
import { useLoad } from '../shared/hooks/useLoad'
import type { PageProps } from '../shared/api/types'
import { ErrorNotice, Pagination } from '../components/Feedback'
import RecordEditor from '../components/RecordEditor'

export default function AddCourse({ onNavigate, target }: PageProps) {
  const [query, setQuery] = useState(target ?? '')
  const [courseId, setCourseId] = useState(target ?? '')
  const [courseOffset, setCourseOffset] = useState(0)
  const [savedNotice, setSavedNotice] = useState('')
  const [choosingCourse, setChoosingCourse] = useState(false)

  const terms = useLoad(useCallback(() => allPages(listTerms), []))
  const courses = useLoad(useCallback(() => listCourses({ q: query, limit: 25, offset: courseOffset }), [query, courseOffset]))
  const records = useLoad(useCallback(() => allPages(listCourseRecords), []))

  const selectedCourse = courses.data?.items.find(course => course.id === courseId)
  const selectedRecord = records.data?.find(record => record.course_id === courseId)
  const pickerHidden = Boolean(target && selectedCourse && !choosingCourse)

  function handleSaved() {
    setSavedNotice('Course record saved.')
    records.reload()
  }

  return (
    <section className="add-course-page">
      <div className="page-heading">
        <h1>Add a course record</h1>
        <button onClick={() => onNavigate?.('Course History')}>Course history</button>
      </div>
      <section className="add-course-card">
        {pickerHidden && selectedCourse ? <div className="selected-course-heading">
          <h2>{selectedCourse.id} · {selectedCourse.title}</h2>
          <button type="button" onClick={() => setChoosingCourse(true)}>Choose another course</button>
        </div> : <h2>Find a course</h2>}
        <ErrorNotice error={courses.error} />
        <div hidden={pickerHidden}>
          <label>
            Find a catalog course
            <input
              type="search"
              value={query}
              onChange={e => {
                setQuery(e.target.value)
                setCourseOffset(0)
                setCourseId('')
                setSavedNotice('')
              }}
              placeholder="Course code or title"
            />
          </label>
          {courses.loading && <p role="status">Finding courses…</p>}
          {!courses.loading && courses.data?.items.length === 0 && !courses.error && (
            <p className="empty" role="status">No catalog courses match your search.</p>
          )}
          {courses.data && courses.data.items.length > 0 && !courses.error && (
            <label>
              Course
              <select
                value={courseId}
                disabled={courses.loading}
                onChange={e => {
                  setCourseId(e.target.value)
                  setSavedNotice('')
                  setChoosingCourse(false)
                }}
              >
                <option value="">Select a course</option>
                {courses.data.items.map(c => (
                  <option key={c.id} value={c.id}>
                    {c.id} · {c.title}
                  </option>
                ))}
              </select>
            </label>
          )}
          {courses.data && (courses.data.items.length > 0 || courseOffset > 0) && !courses.error && (
            <Pagination
              total={courses.data.total}
              offset={courseOffset}
              limit={25}
              loading={courses.loading}
              onPage={idx => {
                setCourseOffset(idx)
                setCourseId('')
                setSavedNotice('')
              }}
            />
          )}
        </div>
        {selectedCourse && (
          <p className="help">
            {selectedCourse.units_min != null && selectedCourse.units_min === selectedCourse.units_max
              ? `Catalog units: ${selectedCourse.units_min}`
              : 'This course has missing or variable catalog units.'}
          </p>
        )}
        <ErrorNotice error={terms.error} />
        {terms.loading && <p role="status">Loading terms…</p>}
        {Boolean(terms.error) && <button type="button" onClick={terms.reload}>Retry terms</button>}
        <ErrorNotice error={records.error} />
        {records.loading && <p role="status">Loading course history…</p>}
        {Boolean(records.error) && <button type="button" onClick={records.reload}>Retry course history</button>}
        {terms.data && records.data && selectedCourse && !records.loading && (
          <RecordEditor
            key={courseId}
            courseId={courseId}
            record={selectedRecord}
            terms={terms.data}
            onSaved={handleSaved}
            onRemoved={records.reload}
            onNavigate={onNavigate}
          />
        )}
        {savedNotice && (
          <div className="notice" style={{ marginTop: '16px' }}>
              <p role="status">{savedNotice}</p>
            {onNavigate && (
              <button
                type="button"
                className="small"
                style={{ marginTop: '8px' }}
                onClick={() => onNavigate('Course History')}
              >
                View course history
              </button>
            )}
          </div>
        )}
      </section>
    </section>
  )
}
