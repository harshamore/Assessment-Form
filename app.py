"""Discovery form: the 5-step wizard partners fill in with a customer.

Scoring, routing and the handoff note all come from assessment.scoring. This
module only collects answers, validates them and saves the registration.
"""
from __future__ import annotations

import streamlit as st

from assessment import notify, storage, ui
from assessment.auth import secret, sign_in_sidebar
from assessment.scoring import agents_in_use, handoff_note, score
from assessment.ui import CONTENT
from assessment.validate import validate_step

PARTNER_FIELDS = ("org", "country", "name", "title", "email", "phone", "pamName", "pamEmail")
SINGLE_FIELDS = (
    "industry", "size", "role", "humans", "singleView", "mfa", "dormant", "nhiInv", "nhiRot",
    "agentAuth", "agentVis", "roAccess", "edr", "residency", "aiUse", "modelType", "count",
    "stage", "endpoint", "prior", "deadline", "owner",
)
MULTI_FIELDS = ("idps", "agentsUse", "scope", "drivers")


def blank_store() -> dict:
    """Hidden and unanswered fields are empty strings or empty lists, as score() expects."""
    store: dict = {"partner": {k: "" for k in PARTNER_FIELDS}}
    store.update({k: "" for k in ("company", "country", "name", "email", "ctitle", "cphone")})
    store.update({k: "" for k in SINGLE_FIELDS})
    store.update({k: [] for k in MULTI_FIELDS})
    store.update({"attest": False, "consent": False})
    return store


def init_state() -> None:
    st.session_state.setdefault("store", blank_store())
    st.session_state.setdefault("step", 1)
    st.session_state.setdefault("error", "")
    st.session_state.setdefault("submitted", False)


def start_another() -> None:
    """Keep the partner's own details, clear the customer and start again at step 2."""
    partner = dict(st.session_state.store["partner"])
    st.session_state.store = blank_store()
    st.session_state.store["partner"] = partner
    st.session_state.step = 2
    st.session_state.submitted = False
    st.session_state.error = ""
    st.session_state.pop("current_reg_id", None)


# ---------- steps ----------
def step_partner(store: dict) -> None:
    st.subheader("Your details")
    p = store["partner"]
    c1, c2 = st.columns(2)
    with c1:
        p["org"] = ui.text("Partner organisation", p, "org")
        p["name"] = ui.text("Your name", p, "name")
        p["email"] = ui.text("Work email", p, "email")
    with c2:
        p["country"] = ui.select("Region / country", CONTENT["country_options"]["partner"], p, "country")
        p["title"] = ui.text("Your role", p, "title", optional=True,
                             placeholder="e.g. Security pre-sales engineer")
        p["phone"] = ui.text("Phone", p, "phone", optional=True)

    st.markdown('<p class="subhead">Cisco Partner Account Manager</p>', unsafe_allow_html=True)
    c3, c4 = st.columns(2)
    with c3:
        p["pamName"] = ui.text("Name", p, "pamName")
    with c4:
        p["pamEmail"] = ui.text("Email", p, "pamEmail")


def step_customer(store: dict) -> None:
    st.subheader("The customer")
    c1, c2 = st.columns(2)
    with c1:
        store["company"] = ui.text("Customer organisation", store, "company")
    with c2:
        store["country"] = ui.select("Country", CONTENT["country_options"]["customer"], store, "country")
    # Industry and size come from questions.json, so they stay value/label pairs.
    c3, c4 = st.columns(2)
    with c3:
        store["industry"] = ui.question_radio("industry", "Industry", store)
    with c4:
        store["size"] = ui.question_radio("size", "Company size", store)

    st.markdown('<p class="subhead">Customer contact</p>', unsafe_allow_html=True)
    c5, c6 = st.columns(2)
    with c5:
        store["name"] = ui.text("Full name", store, "name")
        store["ctitle"] = ui.text("Job title", store, "ctitle", optional=True)
    with c6:
        store["email"] = ui.text("Work email", store, "email")
        store["cphone"] = ui.text("Phone", store, "cphone", optional=True)
    store["role"] = ui.question_radio("role", "Contact's role", store)


def step_identity(store: dict) -> None:
    st.subheader("Identity visibility")

    st.markdown('<p class="subhead">Human identities</p>', unsafe_allow_html=True)
    store["idps"] = ui.question_multi("idps", "Which identity providers and directories do they use?",
                                      store, hint="Select all that apply.")
    store["humans"] = ui.question_radio(
        "humans", "Roughly how many human identities (employees, contractors, partners)?", store)
    store["singleView"] = ui.question_radio(
        "singleView", "Can they see all identities, across every directory, in one place?", store)
    store["mfa"] = ui.question_radio("mfa", "How far does MFA reach?", store)
    store["dormant"] = ui.question_radio(
        "dormant", "How often are dormant and privileged accounts reviewed?", store)

    st.markdown('<p class="subhead">Non-human identities</p>', unsafe_allow_html=True)
    store["nhiInv"] = ui.question_radio(
        "nhiInv", "Do they have an inventory of service accounts, API keys, OAuth apps and tokens?", store)
    store["nhiRot"] = ui.question_radio("nhiRot", "How are those credentials rotated?", store)

    st.markdown('<p class="subhead">AI agent identities</p>', unsafe_allow_html=True)
    selected = ui.question_multi("agentsUse", "Which AI agents are in use?", store,
                                 hint='Select all that apply. "None yet" clears the others.')
    fixed = ui.resolve_exclusive(selected, store.get("agentsUse") or [], "none")
    store["agentsUse"] = fixed
    if fixed != selected:
        st.rerun()

    if agents_in_use(store):
        store["agentAuth"] = ui.question_radio(
            "agentAuth", "How do those agents authenticate to systems?", store)
        store["agentVis"] = ui.question_radio(
            "agentVis", "Can they list every agent and what it can access?", store)
    else:
        store["agentAuth"] = ""
        store["agentVis"] = ""

    st.markdown('<p class="subhead">Assessment readiness</p>', unsafe_allow_html=True)
    store["roAccess"] = ui.question_radio(
        "roAccess", "Can the identity team grant read-only API access to their identity providers?", store)
    store["edr"] = ui.question_radio(
        "edr", "Which endpoint detection and response (EDR) tool do they run?", store)
    store["residency"] = ui.question_radio(
        "residency", "Can assessment data be processed in a US-hosted cloud instance?", store)


def step_ai(store: dict) -> None:
    st.subheader("AI they build or run")
    store["aiUse"] = ui.question_radio(
        "aiUse", "Is the customer building or running its own AI models, agents or applications?", store)

    if store["aiUse"] == "builds":
        store["scope"] = ui.question_multi("scope", "What do they want tested?", store,
                                           hint="Select all that apply.")
        store["modelType"] = ui.question_radio("modelType", "What model sits underneath?", store)
        store["count"] = ui.question_radio("count", "How many targets?", store, horizontal=True)
        store["stage"] = ui.question_radio("stage", "Where are they today?", store)
        store["endpoint"] = ui.question_radio(
            "endpoint", "Can the test reach an endpoint?", store,
            hint="A model API, agent API or app chat interface, plus credentials.")
        store["prior"] = ui.question_radio("prior", "Has anyone adversarially tested them before?", store)
    else:
        for field in ("modelType", "count", "stage", "endpoint", "prior"):
            store[field] = ""
        store["scope"] = []
        if store["aiUse"]:
            st.markdown(
                '<p class="hint">No more AI questions needed. The AI Red Teaming Assessment needs a '
                "model, agent or app the customer builds or runs.</p>",
                unsafe_allow_html=True,
            )


def step_drivers(store: dict) -> None:
    st.subheader("Drivers and authorisation")
    store["drivers"] = ui.question_multi("drivers", "What's prompting this?", store,
                                         hint="Select all that apply.")
    store["deadline"] = ui.question_radio("deadline", "Is there a date they need answers by?", store)
    store["owner"] = ui.question_radio(
        "owner", "Is someone at the customer named to act on the findings?", store)
    store["attest"] = st.checkbox(CONTENT["attestations"]["attest"], value=bool(store.get("attest")))
    store["consent"] = st.checkbox(CONTENT["attestations"]["consent"], value=bool(store.get("consent")))


STEPS = {1: step_partner, 2: step_customer, 3: step_identity, 4: step_ai, 5: step_drivers}


# ---------- submit ----------
def submit(store: dict) -> None:
    result = score(store)
    note = handoff_note(store, result)
    try:
        reg_id = storage.save_registration(store, result, note)
        st.session_state["current_reg_id"] = reg_id
        st.session_state["save_error"] = ""
    except Exception as exc:  # the recommendation is still worth showing
        st.session_state["current_reg_id"] = None
        st.session_state["save_error"] = f"The registration couldn't be saved: {exc}"
    if notify.enabled():
        sent, message = notify.send_handoff(note, store["partner"]["pamEmail"], store.get("company", ""))
        st.session_state["email_status"] = message if sent else message
    st.session_state["submitted"] = True


def show_result(store: dict) -> None:
    result = score(store)
    st.markdown(ui.reco_box(result), unsafe_allow_html=True)
    columns = st.columns(3, gap="medium")
    for column, track in zip(columns, result.card_order()):
        with column:
            st.markdown(ui.track_card(track, result, store, show_score=False), unsafe_allow_html=True)

    if st.session_state.get("save_error"):
        st.warning(st.session_state["save_error"])
    if st.session_state.get("email_status"):
        st.caption(st.session_state["email_status"])

    pam = store["partner"]["pamName"]
    st.markdown(
        f'<p class="hint">The Qualification page has the score breakdowns, the flags for each call, '
        f"the go/no-go gates and a handoff note for {ui.esc(pam)}.</p>",
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns([1, 2])
    with c1:
        st.page_link("pages/1_Qualification.py", label="Open qualification", icon="📋")
    with c2:
        st.button("Register another customer", on_click=start_another)


# ---------- page ----------
def main() -> None:
    ui.page("Discovery form")
    init_state()
    sign_in_sidebar()
    store = st.session_state.store

    st.caption("Free Cisco security assessments · partner intake")
    st.title("Identity & AI Security Assessments")

    left, right = st.columns([1, 1.45], gap="large")
    with left:
        st.header(CONTENT["intro"]["title"], divider="gray")
        st.markdown(f'<p class="hint">{CONTENT["intro"]["lede"]}</p>', unsafe_allow_html=True)
        ui.assessment_summary()

    with right:
        with st.container(border=True):
            if st.session_state.submitted:
                show_result(store)
                return

            step = st.session_state.step
            st.markdown(ui.steps_bar(step), unsafe_allow_html=True)
            STEPS[step](store)

            if st.session_state.error:
                st.error(st.session_state.error)

            back, _, forward = st.columns([1, 2, 1])
            with back:
                if step > 1 and st.button("Back", use_container_width=True):
                    st.session_state.step = step - 1
                    st.session_state.error = ""
                    st.rerun()
            with forward:
                label = "See the recommendation" if step == 5 else "Continue"
                if st.button(label, type="primary", use_container_width=True):
                    error = validate_step(step, store)
                    st.session_state.error = error
                    if not error:
                        if step == 5:
                            submit(store)
                        else:
                            st.session_state.step = step + 1
                    st.rerun()


if __name__ == "__main__":
    main()
