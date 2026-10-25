from __future__ import annotations

from datetime import datetime, timezone
import json
import re
from urllib.parse import urljoin, urlsplit
from urllib.request import build_opener, HTTPRedirectHandler, Request
from uuid import uuid4

from bs4 import BeautifulSoup

from app.features.prerequisites import parse_requirement_rule
from app.schemas import Course, Database, ImportedCourse, IngestionDocument, RefreshResult, RequirementRule, SeatOpeningEvent, Section, Term

SOURCE_HOSTS = {'catalog.sjsu.edu', 'www.sjsu.edu', 'sjsu.edu'}


class OfficialRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        check_source(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def check_source(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname not in SOURCE_HOSTS or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError('Import sources must use an approved official HTTPS host')


def fetch_source(url: str) -> str:
    check_source(url)
    req = Request(url, headers={'User-Agent': 'OurSJSU/0.1 (student course planning project)', 'Accept': 'text/html'})
    with build_opener(OfficialRedirect()).open(req, timeout=10) as res:
        if res.status != 200:
            raise ValueError(f'Source returned HTTP {res.status}; cached data retained')
        buf = res.read(5 * 1024 * 1024 + 1)
        if len(buf) > 5 * 1024 * 1024:
            raise ValueError('Source exceeds the 5 MiB limit')
        html = buf.decode(res.headers.get_content_charset() or 'utf-8')
    if not html.strip() or 'awswaf' in html.lower() or 'captcha' in html.lower() or 'verify you are human' in html.lower():
        raise ValueError('Source is empty or requires browser verification')
    return html


def normalize_course(raw: dict[str, object]) -> ImportedCourse:
    data = dict(raw)
    confirmed = data.pop('confirmed_empty', False)
    for field in ('subject', 'catalog_number', 'title'):
        if not isinstance(data.get(field), str) or not data[field].strip():
            raise ValueError(f'Course requires {field}')
    data['subject'] = data['subject'].strip().upper()
    data['catalog_number'] = data['catalog_number'].strip().upper()
    data['id'] = f'{data["subject"]}-{data["catalog_number"]}'
    for field in ('description', 'units_min', 'units_max', 'prerequisite_text', 'corequisite_text', 'restrictions_text', 'catalog_url'):
        data.setdefault(field, None)
    course = Course.model_validate(data)
    clauses = [parse_requirement_rule(t) for t in (course.prerequisite_text, course.corequisite_text, course.restrictions_text) if t]
    rule = RequirementRule(kind='all', text='Course requirements', children=clauses) if clauses else parse_requirement_rule(None, confirmed_empty=bool(confirmed))
    # Corequisites cannot become satisfied just because a matching past attempt exists.
    if course.corequisite_text:
        idx = 1 if course.prerequisite_text else 0
        rule.children[idx] = RequirementRule(kind='unknown', text=course.corequisite_text)
    return ImportedCourse(course=course, prerequisite_rule=rule)


def parse_catalog(html: str, source_url: str) -> IngestionDocument:
    soup = BeautifulSoup(html, 'html.parser')
    title = soup.select_one('h1#course_preview_title') or soup.select_one('h1#course-title')
    content = soup.select_one('.block_content, .course-description, .courseblock')
    if not title or not content:
        raise ValueError('Catalog course structure not recognized')
    match = re.search(r'\b([A-Z][A-Z0-9]{1,5})\s*0*(\d+[A-Z]*)\s*[-–—]\s*(.+)', title.get_text(' ', strip=True))
    if not match:
        raise ValueError('Catalog course heading not recognized')
    chunks = []
    for node in title.next_siblings:
        if getattr(node, 'name', None) == 'p' and 'Class Schedule' in node.get_text():
            break
        if getattr(node, 'name', None) == 'div' and 'gateway-toolbar' in node.get('class', []):
            break
        chunks.append(str(node))
    body = BeautifulSoup(''.join(chunks), 'html.parser')
    text = body.get_text('\n', strip=True)
    raw = dict(subject=match[1], catalog_number=match[2], title=match[3], catalog_url=source_url)
    units = re.search(r'(\d+(?:\.\d+)?)\s*(?:[-–]\s*(\d+(?:\.\d+)?))?\s*(?:unit(?:s|\(s\))?|credits?)', text, re.I)
    raw['units_min'] = float(units[1]) if units else None
    raw['units_max'] = float(units[2] or units[1]) if units else None
    labels = r'Prerequisite\(s\)|Prerequisites?|Corequisite\(s\)|Corequisites?|Restrictions?|Grading|Repeatable|Satisfies|Misc/Lab Fee|Note'
    matches = list(re.finditer(r'(?im)^(' + labels + r')\s*:', text))
    description = text[:matches[0].start()].strip() if matches else text.strip()
    raw['description'] = description[units.end():].strip() if units else description
    for i, match in enumerate(matches):
        value = text[match.end():matches[i + 1].start() if i + 1 < len(matches) else len(text)].strip()
        label = match[1].lower()
        if label.startswith('prereq'):
            raw['prerequisite_text'] = value
        elif label.startswith('coreq'):
            raw['corequisite_text'] = value
        elif label.startswith('restriction'):
            raw['restrictions_text'] = value
    raw['confirmed_empty'] = not any(k in raw for k in ('prerequisite_text', 'corequisite_text', 'restrictions_text')) and not re.search(r'prereq|coreq|restrict|permission|consent|standing|major', text, re.I)
    return IngestionDocument(terms=[], courses=[normalize_course(raw)], sections=[])


def normalize_section(raw: dict[str, object], course: Course, term: str, source_url: str, checked_at: str) -> Section:
    data = dict(raw)
    number = data.get('class_number')
    if not isinstance(number, str) or not number.strip() or not term:
        raise ValueError('Section requires a class number and term')
    seats = data.get('open_seats')
    if seats is not None and (not isinstance(seats, int) or isinstance(seats, bool) or seats < 0):
        raise ValueError('Seat count must be a nonnegative integer or null')
    data.update(id=f'{term}:{number}', term=term, course=course, source_url=source_url, last_checked_at=checked_at,
                availability='unknown' if seats is None else 'open' if seats > 0 else 'closed', is_stale=False)
    return Section.model_validate(data)


def schedule_rows(html: str) -> list[dict[str, object]]:
    soup = BeautifulSoup(html, 'html.parser')
    table = next((t for t in soup.select('table') if 'Class Number' in t.get_text() and 'Open Seats' in t.get_text()), None)
    if table is None:
        raise ValueError('Schedule table not recognized')
    rows = []
    for tr in table.select('tr'):
        cells = tr.find_all('td', recursive=False)
        if not cells:
            continue
        if len(cells) != 14:
            raise ValueError('Schedule column layout changed')
        values = [c.get_text(' ', strip=True) for c in cells]
        match = re.fullmatch(r'([A-Z][A-Z0-9]{1,5})\s+0*(\d+[A-Z]*)\s*(?:\(Section\s+(\S+)\)|Sec\s*(\S+))', values[0])
        if not match:
            raise ValueError(f'Schedule course code not recognized: {values[0]}')
        seats = values[12].replace(',', '')
        if seats and seats.lower() not in ('tba', 'n/a', 'unknown', '—', '-') and not seats.isdigit():
            raise ValueError('Schedule seat count not recognized')
        days = values[7].split()
        meetings = []
        day_codes = {'M': 'mon', 'T': 'tue', 'W': 'wed', 'R': 'thu', 'F': 'fri', 'S': 'sat', 'U': 'sun'}
        blocks = re.split(r'<br\s*/?>\s*<br\s*/?>', str(cells[8]))
        times = []
        for block in blocks:
            matches = re.findall(r'\d{2}:\d{2}[AP]M\s*-\s*\d{2}:\d{2}[AP]M|TBA', BeautifulSoup(block, 'html.parser').get_text(' ', strip=True))
            if matches:
                times.append(matches[-1])
        locations = [p.strip() for p in cells[10].get_text('\n', strip=True).splitlines() if p.strip()]
        if len(times) != len(days):
            raise ValueError('Schedule meeting columns are not aligned')
        for i, day in enumerate(days):
            if day != 'TBA' and any(ch not in day_codes for ch in day):
                raise ValueError('Schedule weekday format not recognized')
            start = end = None
            if times[i] != 'TBA':
                start, end = [datetime.strptime(t.strip(), '%I:%M%p').strftime('%H:%M') for t in times[i].split('-')]
            location = locations[i] if i < len(locations) else locations[0] if len(locations) == 1 else None
            meetings.append(dict(days=[day_codes[ch] for ch in day] if day != 'TBA' else [], start_time=start, end_time=end,
                                 location=location, is_tba=times[i] == 'TBA' or day == 'TBA'))
        names = [re.sub(r'\s*\([^)]*@[^)]*\)', '', name).strip() for name in re.split(r'\s*;\s*|\n', cells[9].get_text('\n', strip=True))]
        names = [n for n in names if n and '@' not in n and n.lower() != 'tba']
        link = cells[0].find('a', href=True)
        rows.append(dict(course_id=f'{match[1]}-{match[2]}', subject=match[1], catalog_number=match[2],
                         catalog_url=urljoin('https://catalog.sjsu.edu/', link['href']) if link else None,
                         class_number=values[1], section_number=match[3] or match[4], title=values[3], mode=values[2],
                         units=float(values[5]) if re.fullmatch(r'\d+(?:\.\d+)?', values[5]) else None,
                         open_seats=int(seats) if seats.isdigit() else None, meetings=meetings,
                         instructors=[dict(name=n) for n in names], notes=values[13] or None))
    if not rows:
        raise ValueError('Schedule contains no recognized sections')
    return rows


def parse_schedule(html: str, term: str, source_url: str) -> IngestionDocument:
    rows = schedule_rows(html)
    now = datetime.now(timezone.utc).isoformat()
    sections = []
    # Course linkage is completed by the job using the persisted, verified catalog.
    for row in rows:
        raw = dict(row)
        course = Course(id=raw.pop('course_id'), subject=raw.pop('subject'), catalog_number=raw.pop('catalog_number'), title=raw['title'],
                        description=None, units_min=None, units_max=None, prerequisite_text=None, corequisite_text=None, restrictions_text=None, catalog_url=raw.pop('catalog_url'))
        sections.append(normalize_section(raw, course, term, source_url, now))
    return IngestionDocument(terms=[Term(id=term, name=term.replace('-', ' ').title())], courses=[], sections=sections)


def upsert_catalog(db: Database, document: IngestionDocument) -> int:
    for term in document.terms:
        db.execute('INSERT INTO terms VALUES (?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name', (term.id, term.name))
    for imported in document.courses:
        data = imported.course.model_dump()
        cur = db.execute('SELECT * FROM courses WHERE id=?', (data['id'],))
        row = cur.fetchone()
        if row:
            old = dict(zip((c[0] for c in cur.description), row))
            for key in data:
                if data[key] is None:
                    data[key] = old[key]
            merged = normalize_course({**data, 'confirmed_empty': imported.prerequisite_rule.kind == 'all' and not imported.prerequisite_rule.children})
            rule = merged.prerequisite_rule
        else:
            rule = imported.prerequisite_rule
        data['prerequisite_rule_json'] = rule.model_dump_json()
        fields = list(data)
        updates = ','.join(f'{key}=COALESCE(excluded.{key},courses.{key})' for key in fields if key != 'id')
        db.execute(f'INSERT INTO courses ({",".join(fields)}) VALUES ({",".join("?" for _ in fields)}) ON CONFLICT(id) DO UPDATE SET {updates}', list(data.values()))
    return len(document.courses)


def upsert_sections(db: Database, document: IngestionDocument, checked_at: str) -> RefreshResult:
    ids = [s.id for s in document.sections]
    if len(ids) != len(set(ids)):
        raise ValueError('Schedule contains duplicate section IDs')
    for section in document.sections:
        if not db.execute('SELECT 1 FROM courses WHERE id=?', (section.course.id,)).fetchone():
            raise ValueError(f'Catalog missing course {section.course.id}; schedule not imported')
    upsert_catalog(db, IngestionDocument(terms=document.terms, courses=[], sections=[]))
    events = []
    for section in document.sections:
        prev = db.execute('SELECT open_seats FROM sections WHERE id=?', (section.id,)).fetchone()
        data = section.model_dump(exclude={'course', 'meetings', 'instructors', 'availability', 'is_stale'})
        data['course_id'] = section.course.id
        data['last_checked_at'] = checked_at
        fields = list(data)
        updates = ','.join(f'{key}=excluded.{key}' for key in fields if key != 'id')
        db.execute(f'INSERT INTO sections ({",".join(fields)}) VALUES ({",".join("?" for _ in fields)}) ON CONFLICT(id) DO UPDATE SET {updates}', list(data.values()))
        db.execute('DELETE FROM meetings WHERE section_id=?', (section.id,))
        db.execute('DELETE FROM instructors WHERE section_id=?', (section.id,))
        db.executemany('INSERT INTO meetings (section_id,days_json,start_time,end_time,location,is_tba) VALUES (?,?,?,?,?,?)',
                       [(section.id, json.dumps(m.days), m.start_time, m.end_time, m.location, int(m.is_tba)) for m in section.meetings])
        db.executemany('INSERT INTO instructors (section_id,name) VALUES (?,?)', [(section.id, i.name) for i in section.instructors])
        event = record_opening_event(db, section.id, prev[0] if prev else None, section.open_seats, checked_at)
        if event:
            events.append(event.id)
    return RefreshResult(updated_records=len(ids), event_ids=events, checked_at=checked_at)


def record_opening_event(db: Database, section_id: str, previous_seats: int | None, new_seats: int | None, detected_at: str) -> SeatOpeningEvent | None:
    if previous_seats != 0 or new_seats is None or new_seats <= 0:
        return None
    event = SeatOpeningEvent(id=str(uuid4()), section_id=section_id, previous_seats=0, new_seats=new_seats, detected_at=detected_at)
    db.execute('INSERT INTO availability_events (id,section_id,previous_seats,new_seats,detected_at) VALUES (?,?,?,?,?)', tuple(event.model_dump().values()))
    return event
