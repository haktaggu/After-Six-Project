import type { Section } from '../shared/api/types'
import SectionDetails from './SectionDetails'
import WatchButton from './WatchButton'

export default function SectionComparison({ sections }: { sections: Section[] }) {
  return <section className="comparison" aria-label="Section comparison">
    <h2>Compare sections</h2>
    <div className="comparison-grid">{sections.map(s => <article key={s.id}>
      <h3>{s.course.id} · Section {s.section_number}</h3><p>{s.course.title}</p>
      <SectionDetails section={s} /><WatchButton sectionId={s.id} />
    </article>)}</div>
  </section>
}
