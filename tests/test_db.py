"""Round-trip tests for the SQLite layer."""
from __future__ import annotations

import numpy as np
import pytest

from cue import db


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "people.db"
    db.init_db(path)
    return path


def test_insert_retrieve_delete(db_path):
    vec = np.random.randn(256).astype(np.float32)
    vec /= np.linalg.norm(vec)

    pid = db.insert_person(
        db_path, name="Priya", embedding=vec, intro_text="leads platform at Acme"
    )
    assert pid > 0

    people = db.all_people(db_path)
    assert len(people) == 1
    p = people[0]
    assert p.name == "Priya"
    assert p.embedding.shape == (256,)
    np.testing.assert_allclose(p.embedding, vec, rtol=1e-6)

    db.delete_person(db_path, pid)
    assert db.all_people(db_path) == []


def test_append_note_and_set_blurb(db_path):
    vec = np.zeros(256, dtype=np.float32)
    pid = db.insert_person(db_path, name="Sam", embedding=vec, intro_text=None)

    db.append_note(db_path, pid, "promised beta invite")
    db.append_note(db_path, pid, "follow up next week")
    db.set_blurb(db_path, pid, "platform engineer building payments infra at Acme")

    people = db.all_people(db_path)
    assert len(people) == 1
    p = people[0]
    assert "promised beta invite" in (p.user_note or "")
    assert "follow up next week" in (p.user_note or "")
    assert p.blurb and "platform" in p.blurb
