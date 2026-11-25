"""Secrets access and the admin gate.

There is no partner sign-in: the intake form is open, and a registration is
attributed to whoever the partner details name. Only the admin view is gated.
"""
from __future__ import annotations

import hmac

import streamlit as st


def secret(name: str, default=None):
    try:
        return st.secrets.get(name, default)
    except Exception:  # no secrets.toml at all
        return default


def _matches(given: str, expected: str) -> bool:
    return hmac.compare_digest(str(given).strip(), str(expected).strip())


def admin_ok() -> bool:
    """True once the admin password from secrets has been entered."""
    expected = secret("admin_password")
    if not expected:
        st.warning("Set `admin_password` in `.streamlit/secrets.toml` (or the app's Secrets on "
                   "Streamlit Cloud) to open the admin view.")
        return False
    if st.session_state.get("admin_ok"):
        return True
    given = st.text_input("Admin password", type="password")
    if given:
        if _matches(given, expected):
            st.session_state["admin_ok"] = True
            st.rerun()
        st.error("That password isn't right.")
    return False
