import { Fragment } from 'react'
import type { CourseRequirementCheck, Eligibility, EnrollmentRequirement, PageProps, RequirementConfirmation } from '../shared/api/types'
import './RequirementConfirmations.css'

type Props = {
  value: Eligibility
  changes: Record<string, boolean>
  onChange: (id: string, confirmed: boolean) => void
  onNavigate?: PageProps['onNavigate']
  disabled: boolean
}

type Controls = Pick<Props, 'changes' | 'onChange' | 'onNavigate'>

function pathMatch(node: EnrollmentRequirement): number {
  if (node.course) return node.course.status === 'eligible' ? 1 : 0
  if (node.confirmation) return node.confirmation.satisfied || node.confirmation.confirmed ? 1 : 0
  const scores = node.children.map(pathMatch)
  return node.kind === 'any' ? Math.max(0, ...scores) : scores.reduce((total, score) => total + score, 0)
}

function CourseCheck({ course, onNavigate }: { course: CourseRequirementCheck; onNavigate?: PageProps['onNavigate'] }) {
  return <div className="course-requirement-check">
    <div>
      <strong>{course.course_id}</strong>
      <p className="help">{course.concurrent ? 'Enroll in the same term as this course' :
        course.minimum_grade === 'CR' ? 'Requires credit (CR)' :
          course.minimum_grade ? `Requires grade ${course.minimum_grade} or higher` : 'Requires completed credit'}</p>
      <p className="help course-requirement-result">
        {course.recorded_status ? course.recorded_status.replace('_', ' ') : 'No course record'}
        {course.grade && ` · Grade ${course.grade}`}
        {course.status === 'eligible' && ' · Requirement met'}
      </p>
    </div>
    {onNavigate && <button type="button" onClick={() => onNavigate('Add Course', course.course_id)}>
      {course.recorded_status ? 'Edit record' : 'Add record'}
    </button>}
  </div>
}

function ConfirmationField({ requirement, changes, onChange }: { requirement: RequirementConfirmation } & Controls) {
  return <div className="requirement-field">
    {requirement.satisfied && !requirement.confirmed && !(requirement.id in changes)
      ? <div><p>{requirement.text}</p><p className="help">Met from course history.</p></div>
      : <label>
        <span>{requirement.text}</span>
        <select
          value={(changes[requirement.id] ?? requirement.confirmed) ? 'confirmed' : 'unconfirmed'}
          onChange={event => onChange(requirement.id, event.target.value === 'confirmed')}
        >
          <option value="unconfirmed">Not confirmed</option>
          <option value="confirmed">I meet this requirement</option>
        </select>
      </label>}
  </div>
}

function RequirementNode({ node, ...controls }: { node: EnrollmentRequirement } & Controls) {
  if (node.kind === 'all' || node.kind === 'any') {
    if (node.children.length === 0) return <p className="help">No additional enrollment requirements listed.</p>
    const title = node.text.startsWith('Coursework or exam placement') || node.text === 'Choose one enrollment path'
      ? node.text : node.kind === 'any' ? 'Choose one of these options' : 'Meet all of these conditions'
    const children = node.text === 'Choose one enrollment path'
      ? [...node.children].sort((first, second) =>
        Number(second.status === 'eligible') - Number(first.status === 'eligible') || pathMatch(second) - pathMatch(first)) : node.children
    return <div className={`requirement-group requirement-group-${node.kind}`}>
      <h3>{title}</h3>
      <div className="requirement-group-items">
        {children.map((child, index) => <Fragment key={index}>
          {index > 0 && node.kind === 'any' && <p className="requirement-operator">OR</p>}
          <RequirementNode node={child} {...controls} />
        </Fragment>)}
      </div>
    </div>
  }
  return <div className="requirement-condition">
    {node.course && <CourseCheck course={node.course} onNavigate={controls.onNavigate} />}
    {node.confirmation && <ConfirmationField requirement={node.confirmation} {...controls} />}
    {!node.course && !node.confirmation && <p className="help">
      {node.text}{node.status === 'eligible' ? ' · Requirement met' : ' · Condition not met'}
    </p>}
  </div>
}

export default function CourseRequirements({ value, changes, onChange, onNavigate, disabled }: Props) {
  const prerequisites = value.course_requirements ?? []
  const additional = value.additional_requirements ?? []
  const controls = { changes, onChange, onNavigate }

  return <fieldset className="course-requirements" disabled={disabled}>
    <legend>Enrollment requirements</legend>
    <p className="help requirement-save-note">Course history is checked automatically. Confirm the conditions for the path you use and save with your course record.</p>
    {value.requirements ? <RequirementNode node={value.requirements} {...controls} /> : <>
      {prerequisites.length > 0 && <div className="course-prerequisites">
        <h3>Course prerequisites</h3>
        <ul>{prerequisites.map((course, index) => <li key={`${course.course_id}-${index}`}>
          <CourseCheck course={course} onNavigate={onNavigate} />
        </li>)}</ul>
      </div>}
      {additional.length > 0 && <div className="requirement-confirmations">
        <h3>Additional requirements</h3>
        {additional.map(requirement => <ConfirmationField key={requirement.id} requirement={requirement} {...controls} />)}
      </div>}
      {prerequisites.length === 0 && additional.length === 0 && <p className="help">
        {value.status === 'eligible' ? 'No additional enrollment requirements listed.' : 'Catalog requirements have not been verified for this course.'}
      </p>}
    </>}
    {value.source_url && <p className="help requirement-source"><a href={value.source_url} target="_blank" rel="noreferrer">Department enrollment rules</a></p>}
  </fieldset>
}
