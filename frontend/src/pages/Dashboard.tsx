import { useCallback, useState } from 'react'
import { getProfile, updateProfile, listCourseRecords, putCourseRecord, deleteCourseRecord } from '../shared/api/accounts'
import { listCourses, listTerms } from '../shared/api/courses'
import { listMajors } from '../shared/api/planning'
import { allPages } from '../shared/api/lookups'
import { useLoad } from '../shared/hooks/useLoad'
import type { CourseRecord, CourseStatus, Grade, ProfileResponse, Standing, Term } from '../shared/api/types'
import { ErrorNotice, Pagination } from '../components/Feedback'

const grades: Grade[] = ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'F', 'CR', 'NC', 'WU', 'IC', 'W', 'I', 'RP', 'RD', 'AU']

function RecordEditor({ record, courseId, terms, onSaved, onRemoved }: { record?: CourseRecord; courseId: string; terms: Term[]; onSaved: () => void; onRemoved?: () => void }) {
  const [status, setStatus] = useState<CourseStatus>(record?.status ?? 'planned')
  const [grade, setGrade] = useState<Grade | ''>(record?.grade ?? '')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const [notice, setNotice] = useState('')
  async function save(form: HTMLFormElement) {
    setPending(true); setError(null); setNotice('')
    try {
      const fields = new FormData(form)
      await putCourseRecord(courseId, { status, grade: status === 'completed' ? grade || null : null, term: String(fields.get('term') || '') || null })
      setNotice('Course record saved.'); onSaved()
    } catch (err) { setError(err) }
    finally { setPending(false) }
  }
  async function remove() {
    setPending(true); setError(null)
    try { await deleteCourseRecord(courseId); (onRemoved ?? onSaved)() }
    catch (err) { setError(err) }
    finally { setPending(false) }
  }
  return <form className="record-form" onSubmit={e => { e.preventDefault(); void save(e.currentTarget) }}>
    <label>Status<select value={status} onChange={e => { setStatus(e.target.value as CourseStatus); setGrade('') }}>
      <option value="planned">Planned</option><option value="in_progress">In progress</option><option value="completed">Completed</option>
    </select></label>
    {status === 'completed' && <label>Grade<select value={grade} onChange={e => setGrade(e.target.value as Grade | '')}><option value="">Unknown</option>{grades.map(g => <option key={g}>{g}</option>)}</select></label>}
    <label>Term<select name="term" defaultValue={record?.term ?? ''}><option value="">Not specified</option>{terms.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}</select></label>
    <div className="actions"><button type="submit" disabled={pending || !courseId}>{pending ? 'Saving…' : record ? 'Save changes' : 'Add course'}</button>
      {record && <button type="button" disabled={pending} onClick={() => { void remove() }}>Remove record</button>}</div>
    <ErrorNotice error={error} />{notice && <p role="status">{notice}</p>}
  </form>
}

export default function Dashboard() {
  const [offset, setOffset] = useState(0)
  const [query, setQuery] = useState('')
  const [courseId, setCourseId] = useState('')
  const [courseOffset, setCourseOffset] = useState(0)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const [notice, setNotice] = useState('')
  const load = useCallback(async () => {
    const [profile, majors, terms, records] = await Promise.all([getProfile(), allPages(listMajors), allPages(listTerms), listCourseRecords({ limit: 10, offset })])
    return { profile, majors, terms, records }
  }, [offset])
  const { data, error: loadError, loading, reload } = useLoad(load)
  const courses = useLoad(useCallback(() => listCourses({ q: query, limit: 25, offset: courseOffset }), [query, courseOffset]))
  async function saveProfile(form: HTMLFormElement) {
    setSaving(true); setError(null); setNotice('')
    const fields = new FormData(form)
    try {
      const gpa = String(fields.get('gpa') ?? '').trim()
      const units = String(fields.get('earned_units') ?? '').trim()
      await updateProfile({ major_code: String(fields.get('major_code') || '') || null, standing: String(fields.get('standing')) as Standing,
        gpa: gpa === '' ? null : Number(gpa), earned_units: units === '' ? null : Number(units) })
      setNotice('Academic profile saved. Roadmap and watchlist eligibility will use these values.'); reload()
    } catch (err) { setError(err) }
    finally { setSaving(false) }
  }
  function refreshHistory() {
    if (data?.records.items.length === 1 && offset > 0) setOffset(Math.max(0, offset - 10))
    else reload()
  }
  const profile: ProfileResponse | undefined = data?.profile
  return <section>
    <div className="page-heading"><h1>Dashboard</h1><button disabled={loading} onClick={reload}>Refresh</button></div>
    <ErrorNotice error={loadError} />{loading && <p role="status">Loading student overview…</p>}
    {profile && data && <>
      <section className="profile-section"><h2>{profile.user.full_name}</h2><p>{profile.user.email}</p>
        <form key={JSON.stringify(profile.profile)} onSubmit={e => { e.preventDefault(); void saveProfile(e.currentTarget) }}>
          <div className="form-grid">
            <label>Major<select name="major_code" defaultValue={profile.profile.major_code ?? ''}><option value="">Not selected</option>{data.majors.map(m => <option key={m.major_code} value={m.major_code}>{m.title} {m.degree_type}</option>)}</select></label>
            <label>Class standing<select name="standing" defaultValue={profile.profile.standing}>{(['unspecified', 'freshman', 'sophomore', 'junior', 'senior', 'graduate'] as Standing[]).map(s => <option key={s} value={s}>{s === 'unspecified' ? 'Unknown' : s[0].toUpperCase() + s.slice(1)}</option>)}</select></label>
            <label>Cumulative GPA<input name="gpa" type="number" min="0" max="4" step="0.01" defaultValue={profile.profile.gpa ?? ''} placeholder="Unknown" /></label>
            <label>Total earned units<input name="earned_units" type="number" min="0" max="250" step="1" defaultValue={profile.profile.earned_units ?? ''} placeholder="Unknown" /></label>
          </div>
          <button className="primary" disabled={saving}>{saving ? 'Saving…' : 'Save academic profile'}</button><ErrorNotice error={error} />{notice && <p className="notice" role="status">{notice}</p>}
        </form>
      </section>
      <section><h2>Course history</h2>
        {!data.records.items.length && !loading && <p className="empty">No course records yet. Add a course below.</p>}
        {data.records.items.map(r => <details className="history-row" key={JSON.stringify(r)}><summary><strong>{r.course_id}</strong><div><span className={`status ${r.status}`}>{r.status.replace('_', ' ')}</span>{r.grade && <span className="status grade">Grade: {r.grade}</span>}</div></summary><RecordEditor record={r} courseId={r.course_id} terms={data.terms} onSaved={reload} onRemoved={refreshHistory} /></details>)}
        <Pagination total={data.records.total} offset={offset} limit={10} loading={loading} onPage={setOffset} />
      </section>
      <section className="add-course-card"><h2>Add a course</h2><label>Find a catalog course<input type="search" value={query} onChange={e => { setQuery(e.target.value); setCourseOffset(0); setCourseId('') }} placeholder="Course code or title" /></label>
        <ErrorNotice error={courses.error} />{courses.loading && <p role="status">Finding courses…</p>}
        {courses.data && <><label>Course<select value={courseId} onChange={e => setCourseId(e.target.value)}><option value="">Select a course</option>{courses.data.items.map(c => <option key={c.id} value={c.id}>{c.id} · {c.title}</option>)}</select></label><Pagination total={courses.data.total} offset={courseOffset} limit={25} loading={courses.loading} onPage={idx => { setCourseOffset(idx); setCourseId('') }} /></>}
        <RecordEditor key={courseId} courseId={courseId} terms={data.terms} onSaved={reload} />
      </section>
    </>}
  </section>
}
