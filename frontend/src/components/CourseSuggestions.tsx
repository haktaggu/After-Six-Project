import type { CourseSuggestion } from '../shared/api/types'
import CourseSuggestionStatus from './CourseSuggestionStatus'
import './CourseSuggestions.css'

export default function CourseSuggestions({ suggestions, target, onSelect }: {
  suggestions: CourseSuggestion[]
  target: number
  onSelect: (courseId: string) => void
}) {
  if (!suggestions.length) return <p>No remaining courses to suggest for your degree plan.</p>

  return <>
    <ol className="course-suggestions">
      {suggestions.map(suggestion => (
        <li key={suggestion.course_id}>
          <button type="button" onClick={() => onSelect(suggestion.course_id)}>
            <strong>{suggestion.course_id}</strong> {suggestion.title}
          </button>
          <div className="course-suggestion-detail">
            <CourseSuggestionStatus status={suggestion.status} />
            <p className="help">{suggestion.reason}</p>
          </div>
        </li>
      ))}
    </ol>
    {suggestions.length < target && (
      <p className="help">Showing {suggestions.length} of {target} requested suggestions for your degree plan.</p>
    )}
  </>
}
