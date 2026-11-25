"""Per-step validation for the discovery form.

Messages are the ones SPEC.md fixes, word for word. Pure functions so they can
be tested without Streamlit.
"""
from __future__ import annotations

import re

from .scoring import agents_in_use

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s.]+(\.[^@\s.]+)+$")


def valid_email(value: str | None) -> bool:
    return bool(EMAIL_RE.match((value or "").strip()))


def _filled(value) -> bool:
    if isinstance(value, (list, tuple)):
        return len(value) > 0
    return bool((value or "") if isinstance(value, str) else value)


def _all(a: dict, *keys: str) -> bool:
    return all(_filled(a.get(k)) for k in keys)


def validate_step(step: int, a: dict) -> str:
    """Return the error message for `step`, or "" when the step is complete."""
    p = a.get("partner", {})

    if step == 1:
        if not _all(p, "org", "country"):
            return "Enter your organisation and region or country."
        if not _filled(p.get("name")):
            return "Enter your name."
        if not valid_email(p.get("email")):
            return "Enter a valid work email address for yourself."
        if not _filled(p.get("pamName")) or not valid_email(p.get("pamEmail")):
            return "Enter your Cisco Partner Account Manager's name and a valid email address."
        return ""

    if step == 2:
        if not _all(a, "company", "country"):
            return "Enter the customer's organisation and country."
        if not _all(a, "industry", "size"):
            return "Choose the customer's industry and company size."
        if not _filled(a.get("name")):
            return "Enter the customer contact's name."
        if not valid_email(a.get("email")):
            return "Enter a valid work email address for the customer contact."
        if not _filled(a.get("role")):
            return "Choose the customer contact's role."
        return ""

    if step == 3:
        if not _filled(a.get("idps")):
            return 'Choose at least one identity provider, or "Other or not sure".'
        if not _all(a, "humans", "singleView", "mfa", "dormant"):
            return "Answer each human identity question."
        if not _all(a, "nhiInv", "nhiRot"):
            return "Answer both non-human identity questions."
        if not _filled(a.get("agentsUse")):
            return 'Choose which AI agents are in use, or "None yet".'
        if agents_in_use(a) and not _all(a, "agentAuth", "agentVis"):
            return "Answer how agents authenticate and whether they can be listed."
        if not _all(a, "roAccess", "edr", "residency"):
            return "Answer the three assessment readiness questions."
        return ""

    if step == 4:
        if not _filled(a.get("aiUse")):
            return "Answer whether the customer builds or runs its own AI."
        if a.get("aiUse") == "builds":
            if not _filled(a.get("scope")):
                return "Choose at least one thing to test."
            if not _all(a, "modelType", "count", "stage", "endpoint", "prior"):
                return "Answer each AI question to continue."
        return ""

    if step == 5:
        if not _filled(a.get("drivers")):
            return "Choose at least one reason."
        if not _all(a, "deadline", "owner"):
            return "Answer the deadline and findings-owner questions."
        if not a.get("attest"):
            return "Confirm the authorisation statement."
        if not a.get("consent"):
            return "Confirm the customer has agreed to share these details and be contacted."
        return ""

    return ""
