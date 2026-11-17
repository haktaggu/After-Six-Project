import { useCallback, useState } from 'react'
import { putCourseRecord, deleteCourseRecord } from '../shared/api/accounts'
import type { CourseRecord, CourseStatus, Grade, PageProps, Term } from '../shared/api/types'
import { checkEligibility } from '../shared/api/planning'
import { useLoad } from '../shared/hooks/useLoad'
import { ErrorNotice } from './Feedback'
import RecordSectionChoices from './RecordSectionChoices'
import CourseRequirements from './CourseRequirements'
import './RecordEditor.css'

const grades: Grade[] = ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'F', 'CR', 'NC', 'WU', 'IC', 'W', 'I', 'RP', 'RD', 'AU']

export interface RecordEditorProps {
  record?: CourseRecord
  courseId: string
  terms: Term[]
  onSaved: () => void
  onRemoved?: () => void
  onNavigate?: PageProps['onNavigate']
}

export default function RecordEditor({ record, courseId, terms, onSaved, onRemoved, onNavigate }: RecordEditorProps) {
  const [status, setStatus] = useState<CourseStatus>(record?.status ?? 'planned')
  const [grade, setGrade] = useState<Grade | ''>(record?.grade ?? '')
  const [term, setTerm] = useState(record?.term ?? '')
  const [sectionIds, setSectionIds] = useState(record?.section_ids ?? [])
  const [sectionsOpen, setSectionsOpen] = useState(false)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const [notice, setNotice] = useState('')
  const [confirmationChanges, setConfirmationChanges] = useState<Record<string, boolean>>({})
  const requirements = useLoad(useCallback(
    () => checkEligibility({ course_ids: [courseId] }).then(result => result.results[0]),
    [courseId],
  ))

  async function save() {
    if (requirements.loading || requirements.error) return
    setPending(true)
    setError(null)
    setNotice('')
    try {
      await putCourseRecord(courseId, {
        status,
        grade: status === 'completed' ? grade || null : null,
        term: term || null,
        ...(status !== 'completed' && term ? { section_ids: sectionIds } : {}),
        ...(Object.keys(confirmationChanges).length ? {
          requirement_confirmations: Object.fromEntries(
            (requirements.data?.additional_requirements ?? [])
              .filter(requirement => requirement.id in confirmationChanges)
              .map(requirement => [requirement.id, confirmationChanges[requirement.id]]),
          ),
        } : {}),
      })
      setNotice('Course record saved.')
      requirements.reload()
      onSaved()
    } catch (err) {
      setError(err)
    } finally {
      setPending(false)
    }
  }

  async function remove() {
    setPending(true)
    setError(null)
    try {
      await deleteCourseRecord(courseId)
      ;(onRemoved ?? onSaved)()
    } catch (err) {
      setError(err)
    } finally {
      setPending(false)
    }
  }

  return (
    <form className="record-form" onSubmit={e => { e.preventDefault(); void save() }}>
      <div className="record-fields">
        <label>
          Status
          <select value={status} disabled={pending} onChange={e => { setStatus(e.target.value as CourseStatus); setGrade('') }}>
            <option value="planned">Planned</option>
            <option value="in_progress">In progress</option>
            <option value="completed">Completed</option>
          </select>
        </label>
        {status === 'completed' && (
          <label>
            Grade
            <select value={grade} disabled={pending} onChange={e => setGrade(e.target.value as Grade | '')}>
              <option value="">Unknown</option>
              {grades.map(g => <option key={g}>{g}</option>)}
            </select>
          </label>
        )}
        <label>
          Term
          <select name="term" value={term} disabled={pending} onChange={event => {
            setTerm(event.target.value)
            setSectionIds([])
            setSectionsOpen(Boolean(event.target.value))
          }}>
            <option value="">Not specified</option>
            {terms.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
        </label>
      </div>
      {requirements.loading && <p role="status">Loading enrollment requirements…</p>}
      <ErrorNotice error={requirements.error} />
      {Boolean(requirements.error) && <button type="button" disabled={pending} onClick={requirements.reload}>Retry requirements</button>}
      {requirements.data && <CourseRequirements
        value={requirements.data}
        changes={confirmationChanges}
        onChange={(id, confirmed) => setConfirmationChanges(changes => ({ ...changes, [id]: confirmed }))}
        onNavigate={onNavigate}
        disabled={pending || requirements.loading}
      />}
      {courseId && term && status !== 'completed' && (
        <details className="record-sections" open={sectionsOpen} onToggle={event => setSectionsOpen(event.currentTarget.open)}>
          <summary>
            {sectionIds.length ? `Calendar sections (${sectionIds.length} selected)` : 'Choose sections for calendar'}
          </summary>
          {sectionsOpen && <RecordSectionChoices
            key={term}
            courseId={courseId}
            term={term}
            sectionIds={sectionIds}
            onChange={setSectionIds}
            disabled={pending}
          />}
        </details>
      )}
      <div className="actions">
        <button type="submit" disabled={pending || !courseId || requirements.loading || Boolean(requirements.error)}>
          {pending ? 'Saving…' : record ? 'Save changes' : 'Add course'}
        </button>
        {record && (
          <button type="button" disabled={pending} onClick={() => { void remove() }}>
            Remove record
          </button>
        )}
      </div>
      <ErrorNotice error={error} />
      {notice && <p role="status">{notice}</p>}
    </form>
  )
}
