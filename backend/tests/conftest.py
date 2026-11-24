from contextlib import closing

import pytest

from app.db.connection import connect, init_db
from app.features.auth import register_user
from app.schemas import AuthenticatedStudent, SignupRequest


@pytest.fixture
def engineering_student(tmp_path):
    path = tmp_path / 'test.db'
    init_db(path)
    with closing(connect(path)) as db:
        user = register_user(db, SignupRequest(
            email='engineering@example.com', password='example-password', full_name='Engineering Student',
        ))
        with db:
            db.execute("INSERT INTO major_roadmaps (major_code,title) VALUES ('CMPE','Computer Engineering')")
            db.execute("UPDATE student_profiles SET major='CMPE' WHERE student_id=?", (user.id,))
        yield db, AuthenticatedStudent(user.id, user.id)
