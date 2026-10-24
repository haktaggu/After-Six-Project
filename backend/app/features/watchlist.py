# - SQL uses parameters. Mutating services own their transactions; read helpers never commit.
from __future__ import annotations

from app.errors import ApiProblem
from app.schemas import (
    AuthenticatedStudent,
    Database,
    Page,
    WatchMutationResult,
    WatchlistEntry,
)
from app.features.courses import get_section
from app.features.prerequisites import check_eligibility

# - Count active current-student watches with optional term filter; sort added_at DESC,section_id
#   ASC.
# - Build nested Section via get_section and eligibility via check_eligibility, including course
#   grades and profile GPA/units/standing/major. Recalculate on reads; return the page.
# - WatchlistEntry: {section: Section, added_at: string, eligibility: Eligibility}.
def list_watchlist(db: Database, student: AuthenticatedStudent, term: str | None = None, limit: int = 25, offset: int = 0) -> Page[WatchlistEntry]:
    raise NotImplementedError


# - Load section or 404. Get eligibility for its course; retain warnings without blocking save.
# - In one transaction create unique watch or reactivate/update existing watch and added_at.
# - Return entry and created=True only when a row was newly inserted; existing/reactivated is
#   False.
# - Storage: watchlists(id INTEGER PK, student_id FK profiles, section_id FK sections, term TEXT,
#   added_at TEXT, active INTEGER 0/1; UNIQUE(student_id,section_id)).
def add_watch(db: Database, student: AuthenticatedStudent, section_id: str) -> WatchMutationResult:
    raise NotImplementedError


# - Deactivate only matching current-student watch in a transaction.
# - Missing/already-inactive watch succeeds; router sends empty 204.
def remove_watch(db: Database, student: AuthenticatedStudent, section_id: str) -> None:
    raise NotImplementedError
