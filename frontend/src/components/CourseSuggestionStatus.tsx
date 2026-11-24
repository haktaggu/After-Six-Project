import type { CourseSuggestion } from '../shared/api/types'

const statuses = {
  ready: { label: 'Ready now', style: 'eligible' },
  after_current: { label: 'After current courses', style: 'planned' },
  needs_review: { label: 'Needs review', style: 'unknown' },
  requirements_remaining: { label: 'Requirements remaining', style: 'planned' },
} satisfies Record<CourseSuggestion['status'], { label: string; style: string }>

export default function CourseSuggestionStatus({ status }: { status: CourseSuggestion['status'] }) {
  const { label, style } = statuses[status]
  return <span className={`status ${style} course-suggestion-status`}>{label}</span>
}
