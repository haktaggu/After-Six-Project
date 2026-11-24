import { useCallback, useState, type FormEvent } from 'react'
import { compareSections, getCourse, getSection, listSections, listTerms } from '../shared/api/courses'
import { ApiClientError } from '../shared/api/client'
import { allPages } from '../shared/api/lookups'
import { useLoad } from '../shared/hooks/useLoad'
import type { Course, Eligibility, PageProps, Section } from '../shared/api/types'
import { ErrorNotice, Pagination } from '../components/Feedback'
import SectionDetails, { EligibilityDetails } from '../components/SectionDetails'
import { checkEligibility } from '../shared/api/planning'
import SectionComparison from '../components/SectionComparison'
import WatchButton from '../components/WatchButton'
import './Search.css'

function CourseDetails({ section, onNavigate }: { section: Section; onNavigate: PageProps['onNavigate'] }) {
  const [course, setCourse] = useState<Course | null>(null)
  const [eligibility, setEligibility] = useState<Eligibility | null>(null)
  const [current, setCurrent] = useState(section)
  const [error, setError] = useState<unknown>(null)
  const [loading, setLoading] = useState(false)
  async function load(open: boolean) {
    if (!open || course || loading) return
    setLoading(true)
    setError(null)
    try {
      const [courseDetails, sectionDetails, result] = await Promise.all([
        getCourse(section.course.id),
        getSection(section.id),
        checkEligibility({ course_ids: [section.course.id] }),
      ])
      setCourse(courseDetails)
      setCurrent(sectionDetails)
      setEligibility(result.results[0] ?? null)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }
  return <details onToggle={e => { void load(e.currentTarget.open) }}><summary>Course and section details</summary>
    <SectionDetails section={current} />{eligibility && <EligibilityDetails value={eligibility} onNavigate={onNavigate} />}<ErrorNotice error={error} />{loading && <p role="status">Loading course…</p>}
    {Boolean(error) && <button onClick={() => { void load(true) }}>Retry details</button>}
    {course && (course.catalog_url || course.prerequisite_text || course.corequisite_text || course.restrictions_text) && (
      <div className="course-description">
        <p>{course.description || 'Description not provided.'}</p>
        <dl>
          <dt>Units</dt><dd>{course.units_min != null ? (course.units_min === course.units_max ? `${course.units_min} units` : `${course.units_min}–${course.units_max} units`) : 'Units not specified'}</dd>
          <dt>Prerequisites</dt><dd>{course.prerequisite_text || 'Not available in the imported data'}</dd>
          <dt>Corequisites</dt><dd>{course.corequisite_text || 'Not available in the imported data'}</dd>
          <dt>Restrictions</dt><dd>{course.restrictions_text || 'Not available in the imported data'}</dd>
        </dl>
        {course.catalog_url && <a href={course.catalog_url} target="_blank" rel="noreferrer">Official catalog</a>}
      </div>
    )}
    <a href="https://one.sjsu.edu/" target="_blank" rel="noreferrer">Open MySJSU to enroll</a>
  </details>
}

export default function Search({ target, onNavigate }: PageProps) {
  const terms = useLoad(useCallback(() => allPages(listTerms), []))
  const [term, setTerm] = useState('')
  const activeTerm = term || terms.data?.[0]?.id || ''
  const [query, setQuery] = useState({ q: '', course_id: target ?? '', offset: 0 })
  const [selected, setSelected] = useState<Section[]>([])
  const [comparison, setComparison] = useState<Section[] | null>(null)
  const [comparing, setComparing] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const loadSections = useCallback(async (signal: AbortSignal) => {
    if (!activeTerm) return null
    return listSections({
      term: activeTerm,
      q: query.q || undefined,
      course_id: query.course_id || undefined,
      offset: query.offset,
      limit: 25,
    }, signal)
  }, [activeTerm, query])
  const results = useLoad(loadSections)

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const fields = new FormData(event.currentTarget)
    setQuery({
      q: String(fields.get('q') || '').trim(),
      course_id: String(fields.get('course_id') || '').trim(),
      offset: 0,
    })
  }

  function changeTerm(nextTerm: string) {
    setTerm(nextTerm)
    setQuery(previous => ({ ...previous, offset: 0 }))
    setSelected([])
    setComparison(null)
    setError(null)
  }

  function toggle(section: Section) {
    setError(null)
    setComparison(null)
    if (section.term !== activeTerm) return
    if (selected.some(item => item.id === section.id)) {
      setSelected(selected.filter(item => item.id !== section.id))
      return
    }
    if (selected.length === 2) {
      setError('Choose up to two sections. Remove one before adding another.')
      return
    }
    setSelected([...selected, section])
  }

  async function compare() {
    setComparing(true)
    setError(null)
    try {
      const result = await compareSections({ section_ids: selected.map(section => section.id) })
      setComparison(result.sections)
    } catch (err) {
      setError(err)
      if (err instanceof ApiClientError && err.status === 404) {
        setSelected([])
        setComparison(null)
        results.reload()
      }
    } finally {
      setComparing(false)
    }
  }
  return <section className="search-page">
    <div className="page-heading"><h1>Find your classes</h1><button disabled={results.loading} onClick={results.reload}>Refresh observations</button></div>
    <ErrorNotice error={terms.error} />
    <form className="search-form" onSubmit={submitSearch}>
      <label>
        Term
        <select value={activeTerm} disabled={terms.loading || comparing} onChange={event => changeTerm(event.target.value)}>
          <option value="" disabled>Select a term</option>
          {terms.data?.map(term => <option key={term.id} value={term.id}>{term.name}</option>)}
        </select>
      </label>
      <label>Course code or title<input name="q" type="search" placeholder="Try CMPE 131" /></label>
      <label>Exact course ID (optional)<input name="course_id" placeholder="CMPE-131" defaultValue={target ?? ''} /></label>
      <button className="primary" disabled={!activeTerm || results.loading}>Search sections</button>
    </form>
    {!terms.loading && !terms.data?.length && !terms.error && <p className="empty">No course schedules found.</p>}
    <ErrorNotice error={results.error} />{results.loading && <p role="status">Loading sections…</p>}
    {selected.length > 0 && <div className="comparison-tray"><div><strong>{selected.length} of 2 selected</strong>{selected.map(s => <button key={s.id} type="button" disabled={comparing} onClick={() => toggle(s)} aria-label={`Remove ${s.course.id} section ${s.section_number} from comparison`}>{s.course.id} · {s.section_number} ×</button>)}</div><button className="primary" disabled={selected.length !== 2 || comparing} onClick={() => { void compare() }}>{comparing ? 'Comparing…' : 'Compare sections'}</button></div>}
    <ErrorNotice error={error} />{comparison && <SectionComparison sections={comparison} />}
    {results.data && <><div className="results-heading"><h2>Sections</h2><span>{results.data.total} matching sections</span></div>
      {!results.loading && !results.data.items.length && <p className="empty">No matching sections found.</p>}
      <div aria-busy={results.loading}>{results.data.items.map(s => <article className="section-row" key={s.id}>
        <div className="section-heading"><div><h3>{s.course.id} <span>Section {s.section_number}</span></h3><p>{s.course.title}</p></div><span className={`status ${s.availability}`}>{s.open_seats === null ? 'Seats unknown' : `${s.open_seats} seats open`}</span></div>
        <p className="section-preview">{s.instructors.map(i => i.name).join(', ') || 'Instructor TBA'} · {s.mode}</p><CourseDetails section={s} onNavigate={onNavigate} />
        <div className="actions"><label className="checkbox"><input type="checkbox" aria-label={`Compare ${s.course.id} section ${s.section_number}`} disabled={results.loading || comparing} checked={selected.some(curr => curr.id === s.id)} onChange={() => toggle(s)} />Compare</label><WatchButton sectionId={s.id} /></div>
      </article>)}</div>
      <Pagination total={results.data.total} offset={query.offset} limit={25} loading={results.loading} onPage={offset => setQuery(q => ({ ...q, offset }))} />
    </>}
  </section>
}
