# Identity & AI Assessment Intake — Streamlit app spec

## Purpose

Cisco partners use this app to run discovery with a customer and register them for free Cisco assessments. The app scores the answers and recommends which assessments fit, in what order:

| Code | Assessment | Covers | Runs on | Connects to | Duration | Output |
|---|---|---|---|---|---|---|
| ISA | Identity Security Assessment | Human, non-human and AI agent identities (agent and NHI depth is basic) | Sovereign Cisco Identity Intelligence instance | Identity providers, read-only APIs | Up to 14 days for data to stabilise | Findings report and readout |
| AVA | Agent Visibility Assessment | AI agent identities only, in depth | US-hosted Cisco Identity Intelligence instance | CrowdStrike Falcon or Microsoft Defender | One week | PDF readout |
| RT | AI Red Teaming Assessment | Models, agents and AI applications the customer builds or runs | — | The target's endpoint | — | Report mapped to OWASP LLM Top 10 and MITRE ATLAS, and a readout |

**Users:** partner pre-sales engineers (fill in the form), Cisco Partner Account Managers (receive registrations), Cisco admins (see all registrations).

**Reference:** `reference/intake_prototype.html` is a working HTML prototype of the full UX. Open it in a browser. The Streamlit app should reproduce its flow, wording and logic.

## Source of truth

- `config/questions.json`: every question's field name, label and options (value + label).
- `config/scoring.json`: point values, score areas, thresholds, personal email domains, AVA's supported EDRs.
- `config/content.json`: assessment descriptions, scoping call agendas, go/no-go gates, self-serve links, attestation wording.
- `assessment/scoring.py`: scoring, routing, recommendation, flags, next steps and the handoff note. **Pure Python, already tested.** The UI calls `score(answers)`, `next_step(...)` and `handoff_note(...)`. Don't reimplement the logic in the UI.

## Flow

Two pages: **Discovery form** and **Qualification**. Admin pages are listed under Storage below.

### Discovery form: 5 steps

Show a progress indicator (1 · Partner, 2 · Customer, 3 · Identity, 4 · AI, 5 · Drivers) with Back and Continue. Validate each step before moving on, and show the error messages listed below. Keep the answers in `st.session_state` so Back doesn't lose them.

**Step 1 · Partner** (`answers["partner"]`)
- `org` Partner organisation (required)
- `country` Region / country (required). Options: India, Singapore, Australia, New Zealand, Japan, Greater China, ASEAN (other), Korea, Other
- `name` Your name (required), `title` Your role (optional)
- `email` Work email (required, valid), `phone` (optional)
- Cisco Partner Account Manager: `pamName` (required), `pamEmail` (required, valid)

**Step 2 · Customer**
- `company` (required), `country` (required). Options: India, Singapore, Australia, New Zealand, Other Asia Pacific or Japan, Other
- `industry` and `size` (required, options in questions.json)
- Customer contact: `name` (required), `email` (required, valid), `ctitle` (optional), `cphone` (optional)
- `role` Contact's role (required, single choice)

**Step 3 · Identity.** Sub-headings: Human identities, Non-human identities, AI agent identities, Assessment readiness.
- `idps` (multi, required), `humans`, `singleView`, `mfa`, `dormant`
- `nhiInv`, `nhiRot`
- `agentsUse` (multi, required). **"None yet" is exclusive**: choosing it clears the others, and choosing another clears it.
- `agentAuth`, `agentVis`: **only shown and required when agents are in use** (any `agentsUse` value other than `none`)
- `roAccess`, `edr`, `residency`

**Step 4 · AI**
- `aiUse` (required). The next fields are **shown and required only if `aiUse == "builds"`**: `scope` (multi), `modelType`, `count`, `stage`, `endpoint`, `prior`. Otherwise show: "No more AI questions needed. The AI Red Teaming Assessment needs a model, agent or app the customer builds or runs."

**Step 5 · Drivers**
- `drivers` (multi, required), `deadline`, `owner`
- `attest` and `consent` checkboxes (both required). Wording is in content.json.

Hidden fields are sent to `score()` as empty strings or empty lists (see `collect()` in the prototype).

**Validation messages** (use these exact texts):
- Step 1: "Enter your organisation and region or country." / "Enter your name." / "Enter a valid work email address for yourself." / "Enter your Cisco Partner Account Manager's name and a valid email address."
- Step 2: "Enter the customer's organisation and country." / "Choose the customer's industry and company size." / "Enter the customer contact's name." / "Enter a valid work email address for the customer contact." / "Choose the customer contact's role."
- Step 3: 'Choose at least one identity provider, or "Other or not sure".' / "Answer each human identity question." / "Answer both non-human identity questions." / 'Choose which AI agents are in use, or "None yet".' / "Answer how agents authenticate and whether they can be listed." / "Answer the three assessment readiness questions."
- Step 4: "Answer whether the customer builds or runs its own AI." / "Choose at least one thing to test." / "Answer each AI question to continue."
- Step 5: "Choose at least one reason." / "Answer the deadline and findings-owner questions." / "Confirm the authorisation statement." / "Confirm the customer has agreed to share these details and be contacted."

### Result (after step 5)

- A recommendation box: `result.headline`, the sequence of picks with chips (ISA, AVA, RT), and `result.why`.
- One card per assessment, in `result.card_order()`. Each card shows its order label ("Recommended · start here", "Recommended · second", "Recommended · third" or "Not recommended now"), name, score out of 100, route pill, up to 4 reasons (`track.why`) and `next_step(...)`.
- A "Register another customer" button. It keeps the partner details and returns to step 2.
- Save the registration (see Storage).

### Qualification page

For the latest registration, or one picked from the partner's saved registrations:
1. Customer and partner header, recommendation box, and three cards with **score breakdown bars** per area (`AREAS` in scoring.json).
2. Flags list. Critical flags in red, warnings in amber, each with its track chips (an empty `tracks` list means it applies to all).
3. Handoff note in a code block with a copy button, plus a download button for a `.txt` file.
4. The answers, grouped as Partner / Customer / Identity / AI.
5. Three columns (ISA, AVA, RT): the scoping call agenda and a go/no-go checklist with 5 items. Status reads "Go" when all are ticked, otherwise "Not ready · n of 5". **Save the gate state with the registration.**
6. An ISA vs AVA comparison table (as above).
7. "How the recommendation works": explanation text plus the three rubric tables, generated from scoring.json.

## Rules (implemented in scoring.py, summarised here)

- Each track scores 0–100 across four areas.
- **Entry checks:** ISA needs any listed identity provider (not "other") and `roAccess != "no"`. AVA needs agents in use, `edr` in CrowdStrike or Defender, and `residency != "sovereign"`. RT needs `aiUse == "builds"` and `endpoint != "no"`.
- **Route:** fails entry check → Not ready. ≥70 → Fast-track. 40–69 → Cisco review. <40 → Nurture. A personal email domain for the customer contact caps Fast-track at Cisco review.
- **Identity pick:** if ISA and AVA both qualify, recommend both when there are ≥2 human/NHI gaps, otherwise AVA only. If only one qualifies, recommend that one.
- **Order:** when agents are in use without clear identities (`agentVis != "yes"` or `agentAuth != "dedicated"`), identity goes before RT. Otherwise RT goes first only if it outscores the best identity pick.

## Storage

The HTML prototype couldn't save anything. The app must:
- Save every registration to SQLite (`data/registrations.db`): id, created_at, partner email, partner org, PAM email, customer company, full answers JSON, scores and routes per track, picks, the handoff note, and the gate checklist state.
- **My registrations** page: the logged-in partner's registrations, filterable by route and customer. Opening one shows its Qualification page.
- **Admin** page (behind an admin password in `st.secrets`): every registration, filters (partner, PAM, country, recommended assessment, route), CSV export.
- Optional, behind a config flag: send the handoff note by email to the PAM (SMTP settings in `st.secrets`). Off by default.

**Identifying the partner:** ~~a simple partner email + access code from `st.secrets`~~. Removed
after v1: the intake form is open and a registration is attributed to whoever the partner details
name. Only the Admin page is gated, by `admin_password`.

## Non-goals for v1

- No real Cisco system integrations (no Identity Intelligence, EDR or AI Defense API calls).
- No customer-facing access. Only partners and Cisco use the app.

## Visual

Follow the prototype: clean and utilitarian, IBM Plex Sans, a blue accent, chips for ISA (purple), AVA (amber) and RT (blue), and pills for routes (green Fast-track, amber Cisco review, grey Nurture, red Not ready). Use `.streamlit/config.toml` for the theme, plus a small CSS block via `st.markdown(unsafe_allow_html=True)` for chips and pills. Works on a laptop screen. Mobile is nice to have.

## To confirm before release (not code tasks)

- AVA details (EDR list, US hosting, one week, PDF readout) against official Cisco material.
- The supported identity provider list for ISA against the Cisco Identity Intelligence integration list.
- Whether ISA covers agent identities beyond the lab's Entra Agent ID and OpenAI sources.
