"""The signed-in partner's own registrations, with filters."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from assessment import storage, ui
from assessment.auth import sign_in_sidebar
from assessment.scoring import ROUTE_TEXT, SHORT

ROUTE_OPTIONS = ["Any route", *ROUTE_TEXT.values()]
ROUTE_VALUES = {text: key for key, text in ROUTE_TEXT.items()}


def table(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "id": r["id"],
            "Registered": r["created_at"].replace("T", " ")[:16],
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
    ui.page("My registrations", icon="🗂️")
    partner = sign_in_sidebar()

    st.title("My registrations")
    if not partner:
        st.info("Sign in with your work email in the sidebar to see your registrations.")
        return

    c1, c2 = st.columns([1, 2])
    with c1:
        route = st.selectbox("Route", ROUTE_OPTIONS)
    with c2:
        customer = st.text_input("Customer contains", placeholder="e.g. Harbour")

    rows = storage.list_registrations(
        partner_email=partner,
        route=ROUTE_VALUES.get(route),
        customer=customer or None,
    )
    if not rows:
        st.info("No registrations yet. Fill in the discovery form to create one.")
        return

    st.markdown(f'<p class="hint">{len(rows)} registration(s).</p>', unsafe_allow_html=True)
    st.dataframe(table(rows), hide_index=True, use_container_width=True)

    options = {f"#{r['id']} · {r['customer_company']} · {r['created_at'][:10]}": r["id"] for r in rows}
    chosen = st.selectbox("Open a registration", list(options))
    if st.button("Open qualification", type="primary"):
        st.session_state["current_reg_id"] = options[chosen]
        st.switch_page("pages/1_Qualification.py")


if __name__ == "__main__":
    main()
