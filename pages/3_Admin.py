"""Cisco admin view: every registration, filters and a CSV export."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from assessment import storage, ui
from assessment.auth import admin_ok, sign_in_sidebar
from assessment.scoring import NAME, ROUTE_TEXT, SHORT, TRACKS

ROUTE_OPTIONS = ["Any route", *ROUTE_TEXT.values()]
ROUTE_VALUES = {text: key for key, text in ROUTE_TEXT.items()}
ASSESSMENT_OPTIONS = ["Any assessment", *(NAME[t] for t in TRACKS)]
ASSESSMENT_VALUES = {NAME[t]: t for t in TRACKS}


def table(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "id": r["id"],
            "Registered": r["created_at"].replace("T", " ")[:16],
            "Partner": r["partner_org"],
            "Partner contact": r["partner_email"],
            "Cisco PAM": r["pam_name"],
            "Customer": r["customer_company"],
            "Country": r["customer_country"],
            "Recommended": " > ".join(SHORT[p] for p in r["picks"]) or "None",
            "Route": ROUTE_TEXT.get(r["top_route"], ""),
            "ISA": r["isa_score"],
            "AVA": r["ava_score"],
            "RT": r["rt_score"],
            "Gate items ticked": r["gates_done"],
        }
        for r in rows
    ])


def main() -> None:
    ui.page("Admin", icon="🔐")
    sign_in_sidebar()

    st.title("Admin")
    st.markdown('<p class="hint">Every registration from every partner.</p>', unsafe_allow_html=True)
    if not admin_ok():
        return

    partners = ["Any partner", *storage.distinct("partner_org")]
    pams = ["Any PAM", *storage.distinct("pam_name")]
    countries = ["Any country", *storage.distinct("customer_country")]

    c1, c2, c3 = st.columns(3)
    with c1:
        partner = st.selectbox("Partner", partners)
        route = st.selectbox("Route", ROUTE_OPTIONS)
    with c2:
        pam = st.selectbox("Cisco PAM", pams)
        assessment = st.selectbox("Recommended assessment", ASSESSMENT_OPTIONS)
    with c3:
        country = st.selectbox("Customer country", countries)
        customer = st.text_input("Customer contains", placeholder="e.g. Harbour")

    rows = storage.list_registrations(
        route=ROUTE_VALUES.get(route),
        customer=customer or None,
        country=None if country.startswith("Any") else country,
        recommended=ASSESSMENT_VALUES.get(assessment),
    )
    # Partner org and PAM name aren't indexed filters in storage, so narrow here.
    if not partner.startswith("Any"):
        rows = [r for r in rows if r["partner_org"] == partner]
    if not pam.startswith("Any"):
        rows = [r for r in rows if r["pam_name"] == pam]

    if not rows:
        st.info("No registrations match those filters.")
        return

    st.markdown(f'<p class="hint">{len(rows)} registration(s).</p>', unsafe_allow_html=True)
    st.dataframe(table(rows), hide_index=True, use_container_width=True)
    st.download_button("Export CSV", storage.registrations_csv(rows),
                       file_name="registrations.csv", mime="text/csv")

    options = {f"#{r['id']} · {r['customer_company']} · {r['partner_org']}": r["id"] for r in rows}
    chosen = st.selectbox("Open a registration", list(options))
    if st.button("Open qualification", type="primary"):
        st.session_state["current_reg_id"] = options[chosen]
        st.switch_page("pages/1_Qualification.py")


if __name__ == "__main__":
    main()
