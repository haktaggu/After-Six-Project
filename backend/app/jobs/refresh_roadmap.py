from collections.abc import Callable
from dataclasses import dataclass
import re
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from app.features.ingest import check_source
from app.schemas import Database, RoadmapRequirement

ROADMAP_INDEX = 'https://catalog.sjsu.edu/content.php?catoid=23&navoid=8647'
ROADMAP_TITLE = 'Roadmap: Computer Engineering, BS'


@dataclass
class RoadmapCourse:
    course_id: str
    term_order: int
    url: str


@dataclass
class Roadmap:
    courses: list[RoadmapCourse]
    requirements: list[RoadmapRequirement]


def fetch_roadmap(index_url: str, fetch_html: Callable[[str], str]) -> Roadmap:
    check_source(index_url)
    index = BeautifulSoup(fetch_html(index_url), 'html.parser')
    for link in index.select('a[href]'):
        if link.get_text(' ', strip=True) == ROADMAP_TITLE:
            url = urljoin(index_url, link['href'])
            check_source(url)
            return parse_roadmap(fetch_html(url), url)
    raise ValueError('Computer Engineering roadmap link was not found')


def parse_roadmap(html: str, url: str) -> Roadmap:
    soup = BeautifulSoup(html, 'html.parser')
    heading = soup.select_one('h1#acalog-page-title')
    if heading is None or heading.get_text(' ', strip=True) != ROADMAP_TITLE:
        raise ValueError('Expected the official Computer Engineering roadmap page')

    terms = []
    for block in soup.select('.acalog-core'):
        title = block.find('h3', recursive=False)
        if title is None:
            continue
        match = re.fullmatch(r'(Fall|Spring) Semester \((\d+) units\)', title.get_text(' ', strip=True))
        if match:
            terms.append((block, match[1], int(match[2])))
    if [season for _, season, _ in terms] != ['Fall', 'Spring'] * 4:
        raise ValueError('Expected eight roadmap semesters in Fall/Spring order')

    courses = {}
    requirements = []
    for term, (block, _, expected_units) in enumerate(terms, 1):
        total_units = 0
        course_count = 0
        for row in block.select(':scope > ul > li'):
            label = ' '.join(row.stripped_strings)
            label = re.sub(r'\s+([),])', r'\1', ' '.join(label.split()))
            units = re.search(r'\b(\d+)\s+unit(?:s|\(s\))?', label, re.I)
            if units:
                total_units += int(units[1])
            link = row.find('a', href=True)
            detail = urljoin(url, link['href']) if link else ''
            course = re.match(r'^([A-Z][A-Z0-9]{1,5})\s+0*(\d+[A-Z]*)\s*[-–—]', label)
            if course:
                if urlsplit(detail).path not in ('/preview_course.php', '/preview_course_nopop.php') or units is None:
                    raise ValueError(f'Incomplete catalog link or units: {label}')
                check_source(detail)
                course_id = f'{course[1]}-{course[2]}'
                if course_id in courses:
                    raise ValueError(f'Duplicate roadmap course: {course_id}')
                courses[course_id] = RoadmapCourse(course_id, term, detail)
                course_count += 1
            else:
                requirements.append(RoadmapRequirement(
                    term_order=term,
                    label=label[:units.start()].strip() if units else label,
                    units=int(units[1]) if units else None,
                    flexible=label.endswith('*'),
                ))
        if not course_count or total_units != expected_units:
            raise ValueError(f'Semester {term} does not match its published unit total')
    return Roadmap(courses=list(courses.values()), requirements=requirements)


def save_roadmap(db: Database, roadmap: Roadmap) -> None:
    db.execute(
        'INSERT OR IGNORE INTO major_roadmaps (major_code,title,degree_type,description) VALUES (?,?,?,?)',
        ('CMPE', 'Computer Engineering', 'BS', 'SJSU Computer Engineering advising roadmap.'),
    )
    db.execute('DELETE FROM roadmap_courses WHERE major_code=?', ('CMPE',))
    db.executemany(
        'INSERT INTO roadmap_courses (major_code,course_id,term_order,is_required) VALUES (?,?,?,1)',
        [('CMPE', course.course_id, course.term_order) for course in roadmap.courses],
    )
    db.execute('DELETE FROM roadmap_requirements WHERE major_code=?', ('CMPE',))
    db.executemany(
        'INSERT INTO roadmap_requirements (major_code,term_order,label,units,flexible) VALUES (?,?,?,?,?)',
        [('CMPE', row.term_order, row.label, row.units, row.flexible) for row in roadmap.requirements],
    )
