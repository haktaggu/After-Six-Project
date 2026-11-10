import pytest
from fastapi.testclient import TestClient

from app.db.connection import init_db
from app.features import ingest
from app.jobs.refresh_catalog import refresh_catalog, refresh_roadmap_catalog
from app.jobs.refresh_roadmap import ROADMAP_INDEX, parse_roadmap
from app.main import create_app

ROADMAP_URL = 'https://catalog.sjsu.edu/preview_program.php?catoid=23&poid=19250&returnto=8647'
COURSE_URL = 'https://catalog.sjsu.edu/preview_course_nopop.php?catoid=23&coid=198765'


COURSE_HTML = """<div class="block_content">
<h1 id="course_preview_title">CMPE 140 - Computer Architecture and Design</h1>
<p>3 units</p>
<p><strong>Prerequisite(s):</strong> CMPE 125 (with grade of “C-” or better),
Computer Engineering or Software Engineering Majors Only.</p>
</div>"""


def test_catalog_import_exposes_cmpe_140_prerequisite(tmp_path, monkeypatch):
    monkeypatch.setenv('SESSION_SECRET', 'catalog-test-session-secret-at-least-32-bytes')
    monkeypatch.setenv('CATALOG_SOURCE_URL', COURSE_URL)
    monkeypatch.setattr(ingest, 'fetch_source', lambda url: COURSE_HTML)
    path = tmp_path / 'catalog.db'
    init_db(path)
    assert refresh_catalog(path).updated_records == 1

    with TestClient(create_app(path)) as client:
        csrf = client.get('/api/auth/csrf').json()['csrf_token']
        response = client.post('/api/auth/signup', headers={'X-CSRF-Token': csrf},
                               json={'email': 'student@example.com', 'password': 'example-password', 'full_name': 'Test Student'})
        assert response.status_code == 201
        course = client.get('/api/courses/CMPE-140').json()
        assert course['catalog_url'] == COURSE_URL
        assert 'CMPE 125' in course['prerequisite_text']
        result = client.post('/api/me/eligibility',
                             headers={'X-CSRF-Token': response.json()['csrf_token']},
                             json={'course_ids': ['CMPE-140']})
        eligibility = result.json()['results'][0]
        assert eligibility['status'] == 'ineligible'
        assert eligibility['missing_course_ids'] == ['CMPE-125']
        assert any('C-' in reason for reason in eligibility['reasons'])


def roadmap_html():
    semesters = []
    for term in range(1, 9):
        number = 140 if term == 7 else 100 + term
        season = 'Fall' if term % 2 else 'Spring'
        semesters.append(f"""
            <div class="acalog-core"><h3>{season} Semester (6 units)</h3>
            <ul><li><div><a href="preview_course_nopop.php?catoid=23&amp;coid={number}">
              CMPE {number} - Test course</a></div> 3 unit(s)</li>
              <li><a href="preview_program.php?catoid=23&amp;poid=1">GE Area 1A</a>
              (Recommend <a href="preview_course_nopop.php?catoid=23&amp;coid=2">ENGL 1A</a>) 3 unit(s)*</li>
              <li>Apply to Graduate</li>
            </ul></div>
        """)
    return '<h1 id="acalog-page-title">Roadmap: Computer Engineering, BS</h1>' + ''.join(semesters)


def test_roadmap_import_uses_official_links_and_keeps_prior_data_on_failure(tmp_path):
    from app.db.connection import connect, init_db

    path = tmp_path / 'catalog.db'
    init_db(path)

    def fetch(url):
        if url == ROADMAP_INDEX:
            return f'<a href="{ROADMAP_URL}">Roadmap: Computer Engineering, BS</a>'
        if url == ROADMAP_URL:
            return roadmap_html()
        number = url.split('coid=')[1]
        return COURSE_HTML.replace('CMPE 140', f'CMPE {number}', 1)

    assert refresh_roadmap_catalog(path, fetch).updated_records == 8
    with connect(path) as db:
        assert db.execute("SELECT term_order FROM roadmap_courses WHERE course_id='CMPE-140'").fetchone() == (7,)
        assert db.execute("SELECT count(*) FROM roadmap_requirements WHERE flexible=1").fetchone() == (8,)
        assert db.execute("SELECT count(*) FROM roadmap_requirements WHERE units IS NULL").fetchone() == (8,)
        assert db.execute("SELECT count(*) FROM courses WHERE id='ENGL-1A'").fetchone() == (0,)

    def incomplete(url):
        if url.endswith('coid=140'):
            raise ingest.SourceUnavailable('Course temporarily unavailable')
        return fetch(url)

    with pytest.raises(ingest.SourceUnavailable, match='CMPE-140:.*cached roadmap'):
        refresh_roadmap_catalog(path, incomplete)
    with connect(path) as db:
        assert db.execute('SELECT count(*) FROM roadmap_courses').fetchone() == (8,)


def test_roadmap_rejects_missing_units_or_semesters():
    with pytest.raises(ValueError, match='published unit total'):
        parse_roadmap(roadmap_html().replace('3 unit(s)*', '2 unit(s)*', 1), ROADMAP_URL)
    with pytest.raises(ValueError, match='eight roadmap semesters'):
        parse_roadmap(roadmap_html().replace('Fall Semester', 'Quarter', 1), ROADMAP_URL)


def test_live_worker_uses_browser_and_still_refreshes_sections_on_failure(tmp_path, monkeypatch):
    from threading import Event
    from app.jobs import runner

    calls = []

    def browser_catalog(path):
        calls.append('browser')
        raise ingest.SourceUnavailable('catalog unavailable')

    monkeypatch.setattr(runner, 'refresh_catalog_with_browser', browser_catalog)
    monkeypatch.setattr(runner, 'refresh_sections', lambda path, term: calls.append('sections'))
    monkeypatch.setattr(runner, 'send_notifications', lambda path: None)
    runner.JobRunner(tmp_path / 'test.db', runner.Settings()).tick(Event())
    assert calls == ['browser', 'sections']
