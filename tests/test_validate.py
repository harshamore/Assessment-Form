"""Each step must reject exactly what SPEC.md says it rejects, with its wording."""
import copy
import json
from pathlib import Path

import pytest

from assessment.validate import valid_email, validate_step

EXAMPLE = json.loads((Path(__file__).parent / "expected_results.json").read_text())["example"]


@pytest.fixture
def answers():
    return copy.deepcopy(EXAMPLE)


def test_complete_example_passes_every_step(answers):
    assert [validate_step(step, answers) for step in range(1, 6)] == ["", "", "", "", ""]


def test_empty_form_fails_every_step():
    for step in range(1, 6):
        assert validate_step(step, {}) != ""


@pytest.mark.parametrize(
    ("step", "mutate", "message"),
    [
        (1, lambda a: a["partner"].update(org=""), "Enter your organisation and region or country."),
        (1, lambda a: a["partner"].update(country=""), "Enter your organisation and region or country."),
        (1, lambda a: a["partner"].update(name=""), "Enter your name."),
        (1, lambda a: a["partner"].update(email="daniel.lim"),
         "Enter a valid work email address for yourself."),
        (1, lambda a: a["partner"].update(pamName=""),
         "Enter your Cisco Partner Account Manager's name and a valid email address."),
        (1, lambda a: a["partner"].update(pamEmail="alex@"),
         "Enter your Cisco Partner Account Manager's name and a valid email address."),
        (2, lambda a: a.update(company=""), "Enter the customer's organisation and country."),
        (2, lambda a: a.update(industry=""), "Choose the customer's industry and company size."),
        (2, lambda a: a.update(size=""), "Choose the customer's industry and company size."),
        (2, lambda a: a.update(name=""), "Enter the customer contact's name."),
        (2, lambda a: a.update(email="priya"), "Enter a valid work email address for the customer contact."),
        (2, lambda a: a.update(role=""), "Choose the customer contact's role."),
        (3, lambda a: a.update(idps=[]), 'Choose at least one identity provider, or "Other or not sure".'),
        (3, lambda a: a.update(humans=""), "Answer each human identity question."),
        (3, lambda a: a.update(mfa=""), "Answer each human identity question."),
        (3, lambda a: a.update(nhiRot=""), "Answer both non-human identity questions."),
        (3, lambda a: a.update(agentsUse=[]), 'Choose which AI agents are in use, or "None yet".'),
        (3, lambda a: a.update(agentAuth=""),
         "Answer how agents authenticate and whether they can be listed."),
        (3, lambda a: a.update(agentVis=""),
         "Answer how agents authenticate and whether they can be listed."),
        (3, lambda a: a.update(edr=""), "Answer the three assessment readiness questions."),
        (4, lambda a: a.update(aiUse=""), "Answer whether the customer builds or runs its own AI."),
        (4, lambda a: a.update(scope=[]), "Choose at least one thing to test."),
        (4, lambda a: a.update(stage=""), "Answer each AI question to continue."),
        (5, lambda a: a.update(drivers=[]), "Choose at least one reason."),
        (5, lambda a: a.update(deadline=""), "Answer the deadline and findings-owner questions."),
        (5, lambda a: a.update(owner=""), "Answer the deadline and findings-owner questions."),
        (5, lambda a: a.update(attest=False), "Confirm the authorisation statement."),
        (5, lambda a: a.update(consent=False),
         "Confirm the customer has agreed to share these details and be contacted."),
    ],
)
def test_step_messages(answers, step, mutate, message):
    mutate(answers)
    assert validate_step(step, answers) == message


def test_agent_questions_only_required_when_agents_in_use(answers):
    answers.update(agentsUse=["none"], agentAuth="", agentVis="")
    assert validate_step(3, answers) == ""


def test_ai_questions_only_required_when_customer_builds(answers):
    answers.update(aiUse="saasonly", scope=[], modelType="", count="", stage="", endpoint="", prior="")
    assert validate_step(4, answers) == ""


@pytest.mark.parametrize("address", ["a@b.co", "first.last@sub.example.com"])
def test_valid_emails(address):
    assert valid_email(address)


@pytest.mark.parametrize("address", ["", None, "a@b", "a b@c.com", "no-at-sign.com", "a@@b.com"])
def test_invalid_emails(address):
    assert not valid_email(address)
