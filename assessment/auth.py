"""Minimal partner sign-in and the admin gate.

Not real authentication — SPEC.md v1 asks only for a partner email plus a shared
access code from st.secrets, so registrations can be attributed to a partner.
"""
from __future__ import annotations

import hmac

import streamlit as st

from .validate import valid_email


def secret(name: str, default=None):
    try:
        return st.secrets.get(name, default)
    except Exception:  # no secrets.toml at all
        return default


def _matches(given: str, expected: str) -> bool:
    return hmac.compare_digest(str(given).strip(), str(expected).strip())


def partner_email() -> str:
    return st.session_state.get("partner_email", "")


def sign_in_sidebar() -> str:
    """Render sign-in in the sidebar and return the signed-in partner email."""
    code = secret("partner_access_code")
    with st.sidebar:
        st.markdown("**Partner sign-in**")
        if partner_email():
            st.success(partner_email())
            if st.button("Sign out", use_container_width=True):
                for key in ("partner_email", "current_reg_id", "store", "step", "submitted"):
                    st.session_state.pop(key, None)
                st.rerun()
            return partner_email()

        with st.form("sign_in", clear_on_submit=False):
            email = st.text_input("Work email")
            given = st.text_input("Access code", type="password") if code else ""
            ok = st.form_submit_button("Sign in", use_container_width=True)
        if not code:
            st.caption("No access code is configured, so any work email can sign in.")
        if ok:
            if not valid_email(email):
                st.error("Enter a valid work email address.")
            elif code and not _matches(given, code):
                st.error("That access code isn't right.")
            else:
                st.session_state["partner_email"] = email.strip().lower()
                st.rerun()
    return partner_email()


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
