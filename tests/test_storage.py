"""SQLite persistence: registrations, filters, gate state and CSV export."""
import copy
import json
from pathlib import Path

import pytest

from assessment import storage
from assessment.scoring import handoff_note, score

EXAMPLE = json.loads((Path(__file__).parent / "expected_results.json").read_text())["example"]


@pytest.fixture
def db(tmp_path):
    return tmp_path / "registrations.db"


def save(answers, db):
    result = score(answers)
    return storage.save_registration(answers, result, handoff_note(answers, result), path=db)


def test_save_and_read_back(db):
    reg_id = save(EXAMPLE, db)
    reg = storage.get_registration(reg_id, path=db)
    assert reg["answers"] == EXAMPLE
    assert reg["customer_company"] == EXAMPLE["company"]
    assert reg["partner_email"] == EXAMPLE["partner"]["email"]
    assert reg["pam_email"] == EXAMPLE["partner"]["pamEmail"]
    assert reg["picks"] == ["ava", "isa", "rt"]
    assert reg["top_route"] == "fast"
    assert reg["note"].startswith("IDENTITY & AI ASSESSMENTS")
    assert reg["gates"] == {}


def test_scores_are_stored_per_track(db):
    reg = storage.get_registration(save(EXAMPLE, db), path=db)
    result = score(EXAMPLE)
    for track in ("isa", "ava", "rt"):
        assert reg[f"{track}_score"] == result.tracks[track].total
        assert reg[f"{track}_route"] == result.tracks[track].route


def test_missing_registration_is_none(db):
    assert storage.get_registration(999, path=db) is None


def test_newest_first_and_latest_for_partner(db):
    first = save(EXAMPLE, db)
    other = copy.deepcopy(EXAMPLE)
    other["company"] = "Second Customer"
    second = save(other, db)
    assert [r["id"] for r in storage.list_registrations(path=db)] == [second, first]
    latest = storage.latest_for_partner(EXAMPLE["partner"]["email"], path=db)
    assert latest["id"] == second


def test_filters(db):
    save(EXAMPLE, db)
    nurture = copy.deepcopy(EXAMPLE)
    nurture.update(company="Quiet Corp", country="India", idps=["other"], roAccess="no",
                   agentsUse=["none"], agentAuth="", agentVis="", aiUse="none", scope=[],
                   modelType="", count="", stage="", endpoint="", prior="",
                   drivers=["curious"], deadline="none")
    nurture["partner"] = dict(EXAMPLE["partner"], email="other.partner@example.com")
    save(nurture, db)

    assert len(storage.list_registrations(path=db)) == 2
    assert len(storage.list_registrations(partner_email=EXAMPLE["partner"]["email"], path=db)) == 1
    assert len(storage.list_registrations(customer="harbour", path=db)) == 1
    assert len(storage.list_registrations(country="India", path=db)) == 1
    assert len(storage.list_registrations(route="fast", path=db)) == 1
    assert len(storage.list_registrations(recommended="ava", path=db)) == 1
    assert len(storage.list_registrations(recommended="rt", path=db)) == 1
    assert storage.list_registrations(pam_email="nobody@cisco.example", path=db) == []


def test_partner_email_is_matched_case_insensitively(db):
    save(EXAMPLE, db)
    shouty = EXAMPLE["partner"]["email"].upper()
    assert len(storage.list_registrations(partner_email=shouty, path=db)) == 1


def test_gates_round_trip(db):
    reg_id = save(EXAMPLE, db)
    storage.save_gates(reg_id, {"isa": [0, 2, 2], "ava": [], "rt": [4]}, path=db)
    assert storage.get_gates(reg_id, path=db) == {"isa": [0, 2], "rt": [4]}
    reg = storage.get_registration(reg_id, path=db)
    assert reg["gates_done"] == 3
    storage.save_gates(reg_id, {}, path=db)
    assert storage.get_gates(reg_id, path=db) == {}


def test_distinct_columns(db):
    save(EXAMPLE, db)
    assert storage.distinct("partner_org", path=db) == [EXAMPLE["partner"]["org"]]
    with pytest.raises(ValueError):
        storage.distinct("note", path=db)


def test_csv_export(db):
    save(EXAMPLE, db)
    rows = storage.list_registrations(path=db)
    csv_text = storage.registrations_csv(rows)
    header, line = csv_text.splitlines()[:2]
    assert header.split(",") == storage.CSV_COLUMNS
    assert EXAMPLE["company"] in line
    assert "Fast-track" in line


def test_db_path_honours_env(monkeypatch, tmp_path):
    monkeypatch.setenv("ASSESSMENT_DB", str(tmp_path / "custom.db"))
    assert storage.db_path() == tmp_path / "custom.db"
    monkeypatch.delenv("ASSESSMENT_DB")
    assert storage.db_path() == storage.DEFAULT_DB
