import { useState } from 'react'
import type { ComparisonResponse, Page, PageProps, Section, SectionQuery, Term } from '../shared/api/types'
import './Search.css'

// - shared/api/courses.listTerms({limit?,offset?})->Page<Term>; Term is {id:string,name:string}.
// - Pick an imported term before searching. Fetch all lookup pages when total exceeds items.length.
async function loadTerms(): Promise<Page<Term>> {
  throw new Error('loadTerms is not implemented')
}

// - shared/api/courses.listSections(query)->Page<Section>; Page has items,total,limit,offset.
// - SectionQuery is {term:string,q?:string,course_id?:string,limit?:number,offset?:number}.
//   q searches code/title ignoring case. Exact course_id and term must also match.
// - Reset offset when search/term changes; cancel or ignore stale responses. Render nested
//   course title/code, units, mode, instructors, meetings, seats, notes and source freshness.
// - Section has id,term,class_number,section_number,course:Course,title,mode,units|null,
//   open_seats|null,availability(open/closed/unknown),meetings[],instructors[],notes|null,
//   source_url,last_checked_at|null,is_stale. Unknown seats remain unknown, not zero.
// - Details use courses.getCourse(courseId) and getSection(sectionId). Course has id,subject,
//   catalog_number,title,nullable description/units_min/units_max/prerequisite_text/
//   corequisite_text/restrictions_text/catalog_url. Keep the normal MySJSU enrollment link.
async function runSearch(query: SectionQuery): Promise<Page<Section>> {
  void query
  throw new Error('runSearch is not implemented')
}

// - Reload using runSearch({...query,offset}); preserve keyword, course ID, term and limit.
// - offset must be nonnegative; default limit is 25, bounded 1..100. Enable next only when
//   offset + items.length < total. Never discard later results from a full import.
async function changePage(offset: number, query: SectionQuery): Promise<Page<Section>> {
  void [offset, query]
  throw new Error('changePage is not implemented')
}

// - Toggle section.id locally; cap selection at two and reject a different term.
// - Clear selection when changing term. Keep the student's selection order.
async function toggleComparison(selected: string[], section: Section, selectedTerm: string): Promise<string[]> {
  void [selected, section, selectedTerm]
  throw new Error('toggleComparison is not implemented')
}

// - shared/api/courses.compareSections({section_ids:sectionIds})->{sections:Section[]}.
// - Require exactly two unique same-term IDs. Render SectionComparison in returned order.
// - 404 needs a selection refresh; 422 needs correction. Use WatchButton for adding a section.
async function compareSelected(sectionIds: string[]): Promise<ComparisonResponse> {
  void sectionIds
  throw new Error('compareSelected is not implemented')
}

const actions = { loadTerms, runSearch, changePage, toggleComparison, compareSelected }

// - Keep loading, empty and error states separate; retain keyboard labels and a narrow-screen layout.
export default function Search(props: PageProps = {}) {
  const [notice, setNotice] = useState('')
  void props
  return <section className="search-page">
    <h1>Search</h1>
    <p>Course search will be built here.</p>
    <button type="button" disabled onClick={() => {
      void actions.loadTerms().catch((error: unknown) => setNotice(error instanceof Error ? error.message : 'Request failed'))
    }}>Refresh</button>
    {notice && <p role="alert">{notice}</p>}
  </section>
}
