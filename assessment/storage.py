"""SQLite persistence for registrations and their go/no-go gate state.

One row per registration. Scores and routes are denormalised into columns so the
admin and "my registrations" pages can filter without parsing JSON.
"""
from __future__ import annotations

import csv
import io
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .scoring import NAME, ROUTE_TEXT, TRACKS, Result

DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "registrations.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS registrations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at      TEXT NOT NULL,
    partner_email   TEXT NOT NULL,
    partner_org     TEXT,
    partner_name    TEXT,
    partner_country TEXT,
    pam_name        TEXT,
    pam_email       TEXT,
    customer_company TEXT,
    customer_country TEXT,
    customer_contact TEXT,
    customer_email   TEXT,
    answers_json    TEXT NOT NULL,
    isa_score INTEGER, isa_route TEXT,
    ava_score INTEGER, ava_route TEXT,
    rt_score  INTEGER, rt_route  TEXT,
    picks           TEXT,
    top_route       TEXT,
    note            TEXT,
    gates_json      TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_reg_partner ON registrations(partner_email);
CREATE INDEX IF NOT EXISTS idx_reg_created ON registrations(created_at DESC);
"""

CSV_COLUMNS = [
    "id", "created_at", "partner_org", "partner_name", "partner_email", "partner_country",
    "pam_name", "pam_email", "customer_company", "customer_country", "customer_contact",
    "customer_email", "picks", "top_route",
    "isa_score", "isa_route", "ava_score", "ava_route", "rt_score", "rt_route", "gates_done",
]


def db_path() -> Path:
    """data/registrations.db unless overridden by secrets or ASSESSMENT_DB."""
    override = os.environ.get("ASSESSMENT_DB")
    if not override:
        try:
            import streamlit as st

            override = st.secrets.get("db_path")  # type: ignore[assignment]
        except Exception:
            override = None
    return Path(override).expanduser() if override else DEFAULT_DB


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    target = Path(path) if path else db_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(target, detect_types=sqlite3.PARSE_DECLTYPES)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def save_registration(answers: dict, result: Result, note: str, path: str | Path | None = None) -> int:
    """Insert one registration and return its id."""
    pt = answers.get("partner", {})
    row = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "partner_email": (pt.get("email") or "").strip().lower(),
        "partner_org": pt.get("org", ""),
        "partner_name": pt.get("name", ""),
        "partner_country": pt.get("country", ""),
        "pam_name": pt.get("pamName", ""),
        "pam_email": (pt.get("pamEmail") or "").strip().lower(),
        "customer_company": answers.get("company", ""),
        "customer_country": answers.get("country", ""),
        "customer_contact": answers.get("name", ""),
        "customer_email": (answers.get("email") or "").strip().lower(),
        "answers_json": json.dumps(answers),
        "picks": ",".join(result.picks),
        "top_route": result.tracks[result.picks[0]].route if result.picks else "notready",
        "note": note,
        "gates_json": "{}",
    }
    for t in TRACKS:
        row[f"{t}_score"] = result.tracks[t].total
        row[f"{t}_route"] = result.tracks[t].route

    cols = ", ".join(row)
    marks = ", ".join(f":{c}" for c in row)
    with connect(path) as con:
        cur = con.execute(f"INSERT INTO registrations ({cols}) VALUES ({marks})", row)
        return int(cur.lastrowid)


def _hydrate(row: sqlite3.Row) -> dict[str, Any]:
    reg = dict(row)
    reg["answers"] = json.loads(reg.pop("answers_json"))
    reg["gates"] = json.loads(reg.pop("gates_json") or "{}")
    reg["picks"] = [p for p in (reg.get("picks") or "").split(",") if p]
    reg["gates_done"] = sum(len(v) for v in reg["gates"].values())
    return reg


def get_registration(reg_id: int, path: str | Path | None = None) -> dict[str, Any] | None:
    with connect(path) as con:
        row = con.execute("SELECT * FROM registrations WHERE id = ?", (reg_id,)).fetchone()
    return _hydrate(row) if row else None


def list_registrations(
    partner_email: str | None = None,
    pam_email: str | None = None,
    route: str | None = None,
    customer: str | None = None,
    country: str | None = None,
    recommended: str | None = None,
    limit: int = 500,
    path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Newest first. Every filter is optional; `recommended` matches any pick."""
    where, params = [], {}
    if partner_email:
        where.append("partner_email = :partner_email")
        params["partner_email"] = partner_email.strip().lower()
    if pam_email:
        where.append("pam_email = :pam_email")
        params["pam_email"] = pam_email.strip().lower()
    if route:
        where.append("top_route = :route")
        params["route"] = route
    if customer:
        where.append("customer_company LIKE :customer")
        params["customer"] = f"%{customer.strip()}%"
    if country:
        where.append("customer_country = :country")
        params["country"] = country
    if recommended:
        where.append("(',' || picks || ',') LIKE :recommended")
        params["recommended"] = f"%,{recommended},%"

    sql = "SELECT * FROM registrations"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY id DESC LIMIT :limit"
    params["limit"] = limit
    with connect(path) as con:
        rows = con.execute(sql, params).fetchall()
    return [_hydrate(r) for r in rows]


def save_gates(reg_id: int, gates: dict[str, list[int]], path: str | Path | None = None) -> None:
    """Persist the ticked go/no-go items, as {track: [indexes]}."""
    clean = {t: sorted({int(i) for i in gates.get(t, [])}) for t in TRACKS if gates.get(t)}
    with connect(path) as con:
        con.execute("UPDATE registrations SET gates_json = ? WHERE id = ?", (json.dumps(clean), reg_id))


def get_gates(reg_id: int, path: str | Path | None = None) -> dict[str, list[int]]:
    with connect(path) as con:
        row = con.execute("SELECT gates_json FROM registrations WHERE id = ?", (reg_id,)).fetchone()
    return json.loads(row["gates_json"]) if row and row["gates_json"] else {}


def distinct(column: str, path: str | Path | None = None) -> list[str]:
    """Sorted distinct non-empty values, for the admin filter dropdowns."""
    if column not in {
        "partner_org", "partner_email", "pam_name", "pam_email", "customer_country", "partner_country",
    }:
        raise ValueError(f"not a filterable column: {column}")
    with connect(path) as con:
        rows = con.execute(
            f"SELECT DISTINCT {column} AS v FROM registrations WHERE v IS NOT NULL AND v != '' ORDER BY v"
        ).fetchall()
    return [r["v"] for r in rows]


def registrations_csv(rows: Iterable[dict[str, Any]]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for reg in rows:
        flat = dict(reg)
        flat["picks"] = " > ".join(NAME[p] for p in reg.get("picks", []))
        flat["top_route"] = ROUTE_TEXT.get(reg.get("top_route", ""), "")
        writer.writerow(flat)
    return buf.getvalue()
