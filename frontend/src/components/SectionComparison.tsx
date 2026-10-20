import type { Section } from '../shared/api/types'

interface SectionComparisonProps {
  sections: Section[]
}

// - sections comes from courses.compareSections({section_ids})->{sections:Section[]}; keep that order.
// - Show nested course title/code, instructors[].name, meetings, location, units,
//   open_seats, availability, last_checked_at and is_stale for exactly two same-term sections.
// - Meeting fields: days:mon..sun[], start_time/end_time/location nullable, is_tba:boolean.
//   Missing times/seats are unknown, not midnight/zero. Times use America/Los_Angeles.
// - Use WatchButton(sectionId,onAdded?) per section. Add horizontal scrolling or a
//   stacked mobile layout with readable row labels and keyboard-accessible controls.
export default function SectionComparison({ sections }: SectionComparisonProps) {
  void sections
  return <p>Section comparison will be built here.</p>
}
