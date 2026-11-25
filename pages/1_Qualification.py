"""Qualification: the full picture for one registration.

Scores with breakdowns, flags, the handoff note, the answers, a scoping call and
go/no-go gate per assessment, the ISA vs AVA comparison and the rubrics.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from assessment import storage, ui
from assessment.auth import sign_in_sidebar
from assessment.scoring import NAME, TRACKS, agents_in_use, handoff_note, label, labels, score
from assessment.ui import CONTENT, EXAMPLE


def pick_registration(partner: str):
    """The registration being looked at: the chosen one, the newest, or the example."""
    reg_id = st.session_state.get("current_reg_id")
    if reg_id:
        reg = storage.get_registration(int(reg_id))
        if reg:
            return reg, False
    if partner:
        reg = storage.latest_for_partner(partner)
        if reg:
            return reg, False
    return {"answers": EXAMPLE, "gates": {}, "id": None}, True


def header(answers: dict, is_example: bool) -> None:
    partner = answers.get("partner", {})
    left, right = st.columns([3, 1])
    with left:
        st.markdown(f"**{ui.esc(answers.get('company',''))} · {ui.esc(answers.get('name',''))}**",
                    unsafe_allow_html=True)
        st.markdown(
            f'<span class="hint">Registered by {ui.esc(partner.get("name",""))}, '
            f'{ui.esc(partner.get("org",""))}</span>', unsafe_allow_html=True)
    with right:
        if is_example:
            st.markdown('<span class="tag">Example registration. Submit the discovery form to '
                        "replace it.</span>", unsafe_allow_html=True)


def answers_section(answers: dict) -> None:
    partner = answers.get("partner", {})
    agents = agents_in_use(answers)
    builds = answers.get("aiUse") == "builds"
    left, right = st.columns(2, gap="medium")
    with left:
        with st.container(border=True):
            st.markdown("**Partner**")
            st.markdown(ui.answers_dl([
                ("Organisation", partner.get("org", "")),
                ("Region", partner.get("country", "")),
                ("Contact", partner.get("name", "") + (f", {partner['title']}" if partner.get("title") else "")),
                ("Email", partner.get("email", "")),
                ("Phone", partner.get("phone", "")),
                ("Cisco PAM", f"{partner.get('pamName','')} · {partner.get('pamEmail','')}"),
            ]), unsafe_allow_html=True)
            st.markdown("**Customer**")
            st.markdown(ui.answers_dl([
                ("Customer", answers.get("company", "")),
                ("Country", answers.get("country", "")),
                ("Industry", label("industry", answers.get("industry", ""))),
                ("Size", label("size", answers.get("size", ""))),
                ("Contact", answers.get("name", "") + (f", {answers['ctitle']}" if answers.get("ctitle") else "")),
                ("Email", answers.get("email", "")),
                ("Phone", answers.get("cphone", "")),
                ("Role", label("role", answers.get("role", ""))),
                ("Drivers", labels("drivers", answers.get("drivers"))),
                ("Deadline", label("deadline", answers.get("deadline", ""))),
                ("Findings owner", label("owner", answers.get("owner", ""))),
            ]), unsafe_allow_html=True)
    with right:
        with st.container(border=True):
            st.markdown(f"{ui.chip('isa')}{ui.chip('ava')}**Identity answers**", unsafe_allow_html=True)
            st.markdown(ui.answers_dl([
                ("Identity providers", labels("idps", answers.get("idps"))),
                ("Human identities", label("humans", answers.get("humans", ""))),
                ("Single view", label("singleView", answers.get("singleView", ""))),
                ("MFA", label("mfa", answers.get("mfa", ""))),
                ("Account reviews", label("dormant", answers.get("dormant", ""))),
                ("NHI inventory", label("nhiInv", answers.get("nhiInv", ""))),
                ("Credential rotation", label("nhiRot", answers.get("nhiRot", ""))),
                ("Agents in use", labels("agentsUse", answers.get("agentsUse"))),
                ("Agent auth", label("agentAuth", answers.get("agentAuth", "")) if agents else ""),
                ("Agent visibility", label("agentVis", answers.get("agentVis", "")) if agents else ""),
                ("Read-only access", label("roAccess", answers.get("roAccess", ""))),
                ("EDR", label("edr", answers.get("edr", ""))),
                ("US-hosted processing", label("residency", answers.get("residency", ""))),
            ]), unsafe_allow_html=True)
            st.markdown(f"{ui.chip('rt')}**AI answers**", unsafe_allow_html=True)
            st.markdown(ui.answers_dl([
                ("Own AI", label("aiUse", answers.get("aiUse", ""))),
                ("Scope", labels("scope", answers.get("scope")) if builds else ""),
                ("Underlying model", label("modelType", answers.get("modelType", "")) if builds else ""),
                ("Targets", label("count", answers.get("count", "")) if builds else ""),
                ("Stage", label("stage", answers.get("stage", "")) if builds else ""),
                ("Endpoint", label("endpoint", answers.get("endpoint", "")) if builds else ""),
                ("Prior testing", label("prior", answers.get("prior", "")) if builds else ""),
            ]), unsafe_allow_html=True)


def scoping_calls(reg_id: int | None, gates: dict) -> None:
    """A scoping call and a 5-item go/no-go gate per assessment. Ticks are saved."""
    columns = st.columns(3, gap="medium")
    changed: dict[str, list[int]] = {}
    for column, track in zip(columns, TRACKS):
        call = CONTENT["scoping_calls"][track]
        items = CONTENT["gates"][track]
        ticked = set(gates.get(track, []))
        with column, st.container(border=True):
            st.markdown(f"{ui.chip(track)}**Scoping call · {call['minutes']} min**", unsafe_allow_html=True)
            st.markdown(f'<p class="hint">{ui.esc(call["with"])}</p>', unsafe_allow_html=True)
            st.markdown(ui.agenda_html(track), unsafe_allow_html=True)
            done = [
                index for index, item in enumerate(items)
                if st.checkbox(item, value=index in ticked, key=f"gate_{track}_{index}_{reg_id}")
            ]
            changed[track] = done
            st.markdown(ui.gate_pill(len(done), len(items)), unsafe_allow_html=True)

    if reg_id and changed != {t: sorted(gates.get(t, [])) for t in TRACKS}:
        storage.save_gates(int(reg_id), changed)


def how_it_works() -> None:
    with st.container(border=True):
        st.subheader("How the recommendation works")
        for paragraph in CONTENT["intro"]["how_it_works"]:
            st.markdown(f'<p class="hint">{paragraph}</p>', unsafe_allow_html=True)
        columns = st.columns(3, gap="medium")
        for column, track in zip(columns, TRACKS):
            with column:
                st.markdown(f"{ui.chip(track)}**Rubric**", unsafe_allow_html=True)
                st.dataframe(pd.DataFrame(ui.rubric_rows(track)), hide_index=True,
                             use_container_width=True)


def main() -> None:
    ui.page("Qualification", icon="📋")
    partner = sign_in_sidebar()

    st.title("Qualification")
    st.markdown(
        '<p class="hint">Recommended assessments in order, scores and flags for the latest '
        "registration, a handoff note for your Cisco account manager, and a scoping call with "
        "go/no-go gate for each assessment.</p>", unsafe_allow_html=True)

    registration, is_example = pick_registration(partner)
    answers = registration["answers"]
    result = score(answers)

    with st.container(border=True):
        header(answers, is_example)
        st.markdown(ui.reco_box(result), unsafe_allow_html=True)
        columns = st.columns(3, gap="medium")
        for column, track in zip(columns, result.card_order()):
            with column:
                st.markdown(ui.track_card(track, result, answers, show_score=True),
                            unsafe_allow_html=True)

    left, right = st.columns(2, gap="medium")
    with left, st.container(border=True):
        st.markdown("**Flags for the call**")
        st.markdown(ui.flags_html(result), unsafe_allow_html=True)
    with right, st.container(border=True):
        st.markdown("**Handoff note**")
        note = handoff_note(answers, result)
        st.code(note, language=None)
        customer = (answers.get("company") or "registration").replace(" ", "-").lower()
        st.download_button("Download note (.txt)", note, file_name=f"handoff-{customer}.txt",
                           mime="text/plain")

    answers_section(answers)
    scoping_calls(registration.get("id"), registration.get("gates", {}))

    with st.container(border=True):
        st.subheader("ISA or AVA?")
        st.markdown('<p class="hint">Both run on Cisco Identity Intelligence. They differ in what '
                    "they see, where the data lives and how long they take.</p>",
                    unsafe_allow_html=True)
        table = pd.DataFrame(ui.isa_vs_ava_rows()).rename(
            columns={"ISA": f"ISA · {NAME['isa']}", "AVA": f"AVA · {NAME['ava']}"})
        st.dataframe(table, hide_index=True, use_container_width=True)

    how_it_works()


if __name__ == "__main__":
    main()
