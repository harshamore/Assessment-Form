"""Smoke tests for the Streamlit pages, driven through AppTest."""
import copy
import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from assessment import storage
from assessment.scoring import score

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = json.loads((Path(__file__).parent / "expected_results.json").read_text())["example"]
TIMEOUT = 30


@pytest.fixture(autouse=True)
def temp_db(monkeypatch, tmp_path):
    monkeypatch.setenv("ASSESSMENT_DB", str(tmp_path / "registrations.db"))


def markdown_text(at) -> str:
    return "\n".join(block.value for block in at.markdown) + "\n".join(h.value for h in at.subheader)


def test_example_config_matches_the_parity_fixture():
    """config/example_registration.json is what the Qualification page falls back to."""
    assert json.loads((ROOT / "config" / "example_registration.json").read_text()) == EXAMPLE


def test_form_opens_on_step_one():
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=TIMEOUT).run()
    assert not at.exception
    assert at.title[0].value == "Identity & AI Security Assessments"
    assert "1 · Partner" in markdown_text(at)
    assert "Your details" in markdown_text(at)


def test_continue_on_an_empty_step_shows_the_spec_message():
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=TIMEOUT).run()
    at.button[0].click().run()
    assert not at.exception
    assert at.error[0].value == "Enter your organisation and region or country."
    assert "1 · Partner" in markdown_text(at)


def test_example_answers_reach_the_result_screen():
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=TIMEOUT)
    at.session_state["store"] = copy.deepcopy(EXAMPLE)
    at.session_state["step"] = 5
    at.run()
    assert not at.exception

    submit = [b for b in at.button if b.label == "See the recommendation"]
    assert submit, [b.label for b in at.button]
    submit[0].click().run()
    assert not at.exception

    page_text = markdown_text(at)
    assert "Recommended: AVA, then ISA, then AI Red Teaming" in page_text
    assert "Recommended · start here" in page_text
    for score_text in ("85<small>/100</small>", "76<small>/100</small>"):
        assert score_text in page_text
    assert "Register another customer" in [b.label for b in at.button]


def test_submitting_saves_the_registration():
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=TIMEOUT)
    at.session_state["store"] = copy.deepcopy(EXAMPLE)
    at.session_state["step"] = 5
    at.run()
    [b for b in at.button if b.label == "See the recommendation"][0].click().run()

    rows = storage.list_registrations()
    assert len(rows) == 1
    assert rows[0]["answers"] == EXAMPLE
    assert rows[0]["id"] == at.session_state["current_reg_id"]


def test_register_another_customer_keeps_partner_details():
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=TIMEOUT)
    at.session_state["store"] = copy.deepcopy(EXAMPLE)
    at.session_state["step"] = 5
    at.run()
    [b for b in at.button if b.label == "See the recommendation"][0].click().run()
    [b for b in at.button if b.label == "Register another customer"][0].click().run()

    assert not at.exception
    assert at.session_state["step"] == 2
    assert at.session_state["store"]["partner"] == EXAMPLE["partner"]
    assert at.session_state["store"]["company"] == ""
    assert at.session_state["store"]["idps"] == []


def test_qualification_page_falls_back_to_the_example():
    at = AppTest.from_file(str(ROOT / "pages" / "1_Qualification.py"), default_timeout=TIMEOUT).run()
    assert not at.exception
    page_text = markdown_text(at)
    result = score(EXAMPLE)
    assert result.headline in page_text
    assert "Example registration" in page_text
    assert "Flags for the call" in page_text
    assert "Handoff note" in page_text
    assert "Scoping call · 20 min" in page_text
    assert len(at.code) == 1 and at.code[0].value.startswith("IDENTITY & AI ASSESSMENTS")


def test_qualification_gate_ticks_are_saved():
    result = score(EXAMPLE)
    reg_id = storage.save_registration(EXAMPLE, result, "note")
    at = AppTest.from_file(str(ROOT / "pages" / "1_Qualification.py"), default_timeout=TIMEOUT)
    at.session_state["current_reg_id"] = reg_id
    at.run()
    assert not at.exception

    gate = at.checkbox(key=f"gate_isa_0_{reg_id}")
    gate.check().run()
    assert storage.get_gates(reg_id) == {"isa": [0]}
    assert "Not ready · 1 of 5" in markdown_text(at)


def test_my_registrations_needs_sign_in():
    at = AppTest.from_file(str(ROOT / "pages" / "2_My_registrations.py"), default_timeout=TIMEOUT).run()
    assert not at.exception
    assert "Sign in with your work email in the sidebar to see your registrations." in at.info[0].value


def test_my_registrations_lists_the_partners_own_rows():
    result = score(EXAMPLE)
    storage.save_registration(EXAMPLE, result, "note")
    at = AppTest.from_file(str(ROOT / "pages" / "2_My_registrations.py"), default_timeout=TIMEOUT)
    at.session_state["partner_email"] = EXAMPLE["partner"]["email"]
    at.run()
    assert not at.exception
    assert at.dataframe[0].value["Customer"].tolist() == [EXAMPLE["company"]]


def test_admin_page_is_locked_without_a_password():
    at = AppTest.from_file(str(ROOT / "pages" / "3_Admin.py"), default_timeout=TIMEOUT).run()
    assert not at.exception
    assert at.warning[0].value.startswith("Set `admin_password`")
    assert not at.dataframe


def test_answers_survive_continue_and_back():
    """Widgets are re-seeded from session_state, so stepping back doesn't lose answers."""
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=TIMEOUT).run()
    partner = EXAMPLE["partner"]
    at.text_input[0].set_value(partner["org"])
    at.text_input[1].set_value(partner["name"])
    at.text_input[2].set_value(partner["email"])
    at.selectbox[0].set_value(partner["country"])
    at.text_input[3].set_value(partner["title"])
    at.text_input[5].set_value(partner["pamName"])
    at.text_input[6].set_value(partner["pamEmail"])
    at.button[0].click().run()

    assert not at.exception
    assert not at.error
    assert at.session_state["step"] == 2
    assert at.session_state["store"]["partner"]["org"] == partner["org"]

    back = [b for b in at.button if b.label == "Back"][0]
    back.click().run()
    assert at.session_state["step"] == 1
    assert at.text_input[0].value == partner["org"]
    assert at.selectbox[0].value == partner["country"]
    assert at.text_input[6].value == partner["pamEmail"]


def test_none_yet_is_exclusive_with_real_agent_platforms():
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=TIMEOUT)
    at.session_state["store"] = copy.deepcopy(EXAMPLE)
    at.session_state["step"] = 3
    at.run()

    at.multiselect[1].set_value(["copilot", "none"]).run()
    assert at.session_state["store"]["agentsUse"] == ["none"]
    # With no agents, the two agent follow-up questions disappear and are cleared.
    assert at.session_state["store"]["agentAuth"] == ""
    assert at.session_state["store"]["agentVis"] == ""

    at.multiselect[1].set_value(["none", "custom"]).run()
    assert at.session_state["store"]["agentsUse"] == ["custom"]


def test_ai_step_hides_red_teaming_questions_when_the_customer_only_uses_saas():
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=TIMEOUT)
    at.session_state["store"] = copy.deepcopy(EXAMPLE)
    at.session_state["step"] = 4
    at.run()
    at.radio[0].set_value("saasonly").run()

    assert not at.exception
    assert "No more AI questions needed." in markdown_text(at)
    assert at.session_state["store"]["scope"] == []
    assert at.session_state["store"]["endpoint"] == ""
    assert len(at.radio) == 1
