# CLAUDE.md

Streamlit app that Cisco partners use to run identity and AI discovery with a customer, then get a recommendation for the Cisco ISA, AVA and/or AI Red Teaming assessments. Full requirements: **SPEC.md**.

## Layout
- `Intake_Form.py`: Streamlit entry point — the 5-step intake form and the result screen.
  The filename is the sidebar nav label, so renaming it renames the page.
- `pages/`: Qualification, Admin
- `assessment/scoring.py`: scoring, routing, recommendation, flags, handoff note. **Done and tested.**
- `assessment/storage.py`: SQLite persistence for registrations and gate state
- `assessment/validate.py`: per-step form validation, with SPEC.md's exact messages
- `assessment/ui.py`: theme CSS, chips, pills, cards, question widgets, generated rubrics
- `assessment/auth.py`: secrets access and the admin gate (there is no partner sign-in)
- `assessment/notify.py`: optional SMTP handoff email, off by default
- `config/*.json`: questions, points, content. The single source of truth.
- `reference/intake_prototype.html`: working HTML prototype. Match its flow and wording.
- `tests/`: pytest. The `test_scoring.py` parity tests were generated from the prototype;
  `test_validate.py`, `test_storage.py` and `test_app.py` (AppTest) cover the app.

## Commands
- Install: `pip install -r requirements.txt`
- Run: `streamlit run Intake_Form.py`
- Test: `pytest -q`

## Rules
- Never put scoring or routing logic in UI code. Call `score()`, `next_step()` and `handoff_note()` from `assessment/scoring.py`.
- Don't change point values, thresholds or wording in code. They live in `config/`. If a config change breaks `tests/expected_results.json`, stop and ask before regenerating it.
- Build form options from `config/questions.json` (value/label pairs). Store values, display labels.
- Form widgets are keyless and seeded from `st.session_state.store`. Streamlit drops the state of
  widgets it doesn't render, so the wizard would otherwise lose answers between steps.
- Set fonts via `[theme]` in `.streamlit/config.toml`, never a CSS `font-family` override: an
  override that reaches Streamlit's elements also hits its Material Symbols icons, which then
  render as their own names (e.g. `keyboard_double_arrow_right`).
- All tests must pass before finishing a task. Add tests for storage and validation.
- Keep secrets in `.streamlit/secrets.toml` (gitignored). Commit a `secrets.example.toml`.
- British English in UI text (organisation, authorisation), matching the prototype.
