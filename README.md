# Identity & AI Assessment Intake (Streamlit)

Cisco partners use this app to run identity and AI discovery with a customer, then get a
recommendation for the Cisco **ISA** (Identity Security Assessment), **AVA** (Agent Visibility
Assessment) and **AI Red Teaming** assessments — which ones fit, in what order, and why.

Requirements live in [SPEC.md](SPEC.md); working notes for Claude Code in [CLAUDE.md](CLAUDE.md).

## Pages

| Page | What it does |
|---|---|
| **Intake Form** (`Intake_Form.py`) | 5-step wizard (Partner, Customer, Identity, AI, Drivers) with per-step validation, then the recommendation |
| **Qualification** | Score breakdowns per area, flags, handoff note (copy + download), the answers, a scoping call and saved go/no-go gate per assessment, ISA vs AVA, and the rubrics |
| **Admin** | Every registration, filters by partner, PAM, country, recommended assessment and route, plus CSV export (needs `admin_password`) |

The intake form is open — there is no partner sign-in. A registration is attributed to whoever the
partner details name, and only the Admin page is gated.

## Run it locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp secrets.example.toml .streamlit/secrets.toml   # optional
streamlit run Intake_Form.py
```

Tests:

```bash
pytest -q
```

## Deploy to Streamlit Community Cloud

1. Push this repo to GitHub.
2. At [share.streamlit.io](https://share.streamlit.io) → **Create app** → **Deploy a public app from
   a GitHub repo**.
3. Repository: this repo. Branch: `main`. Main file path: `Intake_Form.py`.
4. **Advanced settings → Secrets**: paste the contents of `secrets.example.toml` with real values.
   Without `admin_password` the Admin page stays locked.

**Storage caveat:** registrations go to SQLite at `data/registrations.db`, and Streamlit Community
Cloud's filesystem is ephemeral — the file is wiped whenever the app reboots or redeploys. That is
fine for demos and pilots. For anything real, point `db_path` at a mounted volume or move the four
functions in `assessment/storage.py` to a hosted database.

## Configuration

Everything a non-developer might change lives in `config/`, and the UI is built from it:

- `questions.json` — every question's field name, label and value/label options
- `scoring.json` — point values, score areas, thresholds, personal email domains, AVA's supported
  EDRs, and the rubric field map the "How the recommendation works" tables are generated from
- `content.json` — assessment descriptions, scoping call agendas, go/no-go gates, self-serve links,
  attestation wording, country lists and intro copy
- `example_registration.json` — the worked example the Qualification page shows before any real
  registration exists

Fonts are set through `[theme]` in `.streamlit/config.toml` rather than a CSS `font-family`
override. An override that reaches Streamlit's own elements also hits its Material Symbols icons,
which then render as their own names (the sidebar arrow showing `keyboard_double_arrow_right`).

Scoring, routing, flags, next steps and the handoff note all live in `assessment/scoring.py` and are
checked against the original HTML prototype by `tests/test_scoring.py`. The UI never re-implements
any of it.
