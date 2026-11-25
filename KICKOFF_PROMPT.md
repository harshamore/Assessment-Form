# Kickoff prompt for Claude Code

Open this folder in Claude Code and paste the prompt below.

---

Read CLAUDE.md and SPEC.md, then open reference/intake_prototype.html to see the UX I want reproduced.

Build the Streamlit app described in SPEC.md. Work in this order, running `pytest -q` after each stage:

1. Set up: requirements, `.streamlit/config.toml` theme, `secrets.example.toml`, `.gitignore`, and a small CSS helper for chips and pills.
2. `assessment/storage.py`: SQLite storage for registrations and gate state, with tests.
3. Discovery form: the 5-step wizard with session state, conditional fields, the exact validation messages from SPEC.md, and a result screen. Use `assessment/scoring.py` for everything to do with scoring.
4. Qualification page: recommendation, cards with score bars, flags, handoff note (copy and download), answers, scoping calls with saved go/no-go gates, the ISA vs AVA table and rubrics.
5. My registrations and Admin pages, with CSV export.
6. A form-validation test module, and a smoke test that runs the example from `tests/expected_results.json` through the result screen using `streamlit.testing.v1.AppTest`.

Before writing code, give me a short plan with the files you'll create. Ask me if anything in SPEC.md is ambiguous rather than guessing.
