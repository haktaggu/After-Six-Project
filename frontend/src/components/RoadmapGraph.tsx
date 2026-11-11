import { useId, useMemo } from 'react'
import type { CourseSuggestion, StudentRoadmapEntry } from '../shared/api/types'
import CourseSuggestionStatus from './CourseSuggestionStatus'

const cardWidth = 176
const cardHeight = 140
const columnGap = 24
const rowHeight = 212
const cardTop = 34
const labelWidth = 104
const laneGap = 10
const gutterPadding = 26
const unitsPerRem = 16

function toRem(units: number) {
  return `${units / unitsPerRem}rem`
}

type Props = {
  courses: StudentRoadmapEntry[]
  terms: number[]
  suggestions: ReadonlyMap<string, CourseSuggestion>
  selectedId: string | null
  showAll: boolean
  onSelect: (id: string) => void
}

type Node = { entry: StudentRoadmapEntry; row: number; x: number }
type Edge = { source: Node; target: Node; alternative: boolean }
type Lane = { side: 'left' | 'right'; index: number }

function layoutGraph(courses: StudentRoadmapEntry[], terms: number[]) {
  const rows = terms.map(term => courses.filter(entry => entry.term_order === term))
  const columns = Math.max(1, ...rows.map(row => row.length))
  const cardsWidth = columns * cardWidth + (columns - 1) * columnGap
  const nodes: Node[] = rows.flatMap((entries, row) => entries.map((entry, column) => ({
    entry,
    row,
    x: (cardsWidth - (entries.length - 1) * (cardWidth + columnGap)) / 2 + column * (cardWidth + columnGap),
  })))
  const nodesById = new Map(nodes.map(node => [node.entry.course.id, node]))
  const edges: Edge[] = nodes.flatMap(target => (target.entry.prerequisites ?? []).flatMap(link => {
    const source = nodesById.get(link.course_id)
    return source && source !== target ? [{ source, target, alternative: link.alternative }] : []
  }))

  // Reuse a lane only when its connections don't share a semester.
  const occupiedThrough = { left: [] as number[], right: [] as number[] }
  const lanes = new Map<Edge, Lane>()
  const firstRow = ({ source, target }: Edge) => Math.min(source.row, target.row)
  const longEdges = edges.filter(({ source, target }) => Math.abs(source.row - target.row) > 1)
  for (const edge of longEdges.sort((a, b) => firstRow(a) - firstRow(b))) {
    const side = edge.source.x + edge.target.x <= cardsWidth ? 'left' : 'right'
    const sideLanes = occupiedThrough[side]
    const available = sideLanes.findIndex(lastRow => lastRow < firstRow(edge))
    const index = available === -1 ? sideLanes.length : available
    sideLanes[index] = Math.max(edge.source.row, edge.target.row)
    lanes.set(edge, { side, index })
  }

  const leftGutter = gutterPadding + occupiedThrough.left.length * laneGap
  const rightGutter = gutterPadding + occupiedThrough.right.length * laneGap
  const cardsLeft = labelWidth + leftGutter
  const width = cardsLeft + cardsWidth + rightGutter
  return { nodes, edges, lanes, cardsLeft, width, height: terms.length * rowHeight }
}

function pathForEdge(edge: Edge, edges: Edge[], cardsLeft: number, route?: { x: number; depth: number }) {
  const { source, target } = edge
  const sameRow = source.row === target.row
  const goesDown = source.row < target.row
  const leavesBottom = source.row <= target.row
  const outgoing = edges
    .filter(edge => edge.source === source && (edge.target.row >= source.row) === leavesBottom)
    .sort((a, b) => a.target.x - b.target.x)
  const incoming = edges
    .filter(edge => edge.target === target && (edge.source.row < target.row) === goesDown)
    .sort((a, b) => a.source.x - b.source.x)
  const portOffset = (connections: Edge[]) => 116 * ((connections.indexOf(edge) + 1) / (connections.length + 1) - 0.5)
  const startX = cardsLeft + source.x + portOffset(outgoing)
  const endX = cardsLeft + target.x + portOffset(incoming)
  const startY = source.row * rowHeight + cardTop + (leavesBottom ? cardHeight : 0)
  const endY = target.row * rowHeight + cardTop + (goesDown ? 0 : cardHeight)

  if (!route) {
    const bendY = sameRow ? startY + 44 : (startY + endY) / 2
    return `M ${startX} ${startY} C ${startX} ${bendY}, ${endX} ${bendY}, ${endX} ${endY}`
  }

  const { x: laneX, depth } = route
  const direction = goesDown ? 1 : -1
  const approachY = startY + direction * depth
  const exitY = endY - direction * depth
  const startBend = approachY - direction * 6
  const endBend = exitY + direction * 6
  return `M ${startX} ${startY}
    C ${startX} ${startBend}, ${laneX} ${startBend}, ${laneX} ${approachY}
    L ${laneX} ${exitY}
    C ${laneX} ${endBend}, ${endX} ${endBend}, ${endX} ${endY}`
}

export default function RoadmapGraph({ courses, terms, suggestions, selectedId, showAll, onSelect }: Props) {
  const markerId = useId()
  const { nodes, edges, lanes, cardsLeft, width, height } = useMemo(
    () => layoutGraph(courses, terms),
    [courses, terms],
  )
  const connectsToSelection = ({ source, target }: Edge) =>
    source.entry.course.id === selectedId || target.entry.course.id === selectedId
  const activeEdges = selectedId ? edges.filter(connectsToSelection) : []
  const relatedIds = new Set(activeEdges.flatMap(({ source, target }) => [source.entry.course.id, target.entry.course.id]))
  const contextEdges = showAll || !selectedId
    ? edges.filter(edge => !connectsToSelection(edge) && (showAll || !lanes.has(edge)))
    : []
  const visibleEdges = [...contextEdges, ...activeEdges]

  return (
    <div className="roadmap-scroll" role="region" aria-label="Scrollable course dependency graph" tabIndex={0}>
      <div className="roadmap-graph" style={{ minWidth: toRem(width), height: toRem(height) }}>
        <div className="roadmap-bands" aria-hidden="true">
          {terms.map(term => <div className="roadmap-band" key={term} style={{ height: toRem(rowHeight) }} />)}
        </div>
        <div className="roadmap-diagram" style={{ width: toRem(width), height: '100%' }}>
          <svg className="roadmap-lines" width="100%" height="100%" viewBox={`0 0 ${width} ${height}`} aria-hidden="true">
            <defs>
              <marker id={`${markerId}-arrow`} viewBox="0 0 10 10" refX="10" refY="5" markerWidth="8" markerHeight="8" markerUnits="userSpaceOnUse" orient="auto">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="context-stroke" />
              </marker>
            </defs>
            {visibleEdges.map(edge => {
              const { source, target, alternative } = edge
              const active = connectsToSelection(edge)
              const lane = lanes.get(edge)
              const offset = gutterPadding / 2 + (lane?.index ?? 0) * laneGap
              const route = lane && {
                x: lane.side === 'left' ? labelWidth + offset : width - offset,
                depth: 24 + (lane.index % 5) * 8,
              }
              const edgeClass = active ? ' is-active' : selectedId ? ' is-muted' : ''
              return (
                <path
                  key={`${source.entry.course.id}/${target.entry.course.id}`}
                  className={`roadmap-edge${edgeClass}`}
                  d={pathForEdge(edge, visibleEdges, cardsLeft, route)}
                  strokeDasharray={alternative ? '5 4' : undefined}
                  markerEnd={`url(#${markerId}-arrow)`}
                />
              )
            })}
          </svg>
          {terms.map((term, row) => (
            <section
              className="roadmap-graph-row"
              key={term}
              aria-labelledby={`${markerId}-term-${term}`}
              style={{ top: toRem(row * rowHeight), height: toRem(rowHeight) }}
            >
              <h2 id={`${markerId}-term-${term}`}>Semester {term}</h2>
              {nodes.filter(node => node.row === row).map(({ entry, x }) => {
                const { id, title } = entry.course
                const suggestion = suggestions.get(id)
                return (
                  <button
                    type="button"
                    key={id}
                    id={`graph-course-${id}`}
                    className={`roadmap-node${relatedIds.has(id) ? ' is-related' : ''}${suggestion ? ' is-suggested' : ''}`}
                    style={{
                      left: toRem(cardsLeft + x),
                      top: toRem(cardTop),
                      width: toRem(cardWidth),
                      height: toRem(cardHeight),
                    }}
                    aria-pressed={selectedId === id}
                    onClick={() => onSelect(id)}
                  >
                    <strong>{id}</strong>
                    <span className="roadmap-node-title">{title}</span>
                    <span className={`status ${entry.student_status}`}>{entry.student_status.replaceAll('_', ' ')}</span>
                    {suggestion && <CourseSuggestionStatus status={suggestion.status} />}
                  </button>
                )
              })}
            </section>
          ))}
        </div>
      </div>
    </div>
  )
}
