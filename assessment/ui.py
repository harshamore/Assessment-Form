"""Presentation helpers: theme CSS, chips, pills, track cards and rubric tables.

No scoring logic here. Wording comes from config/, scores come from
assessment.scoring.
"""
from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

import streamlit as st

from .scoring import AREAS, NAME, POINTS, QUESTIONS, ROUTE_TEXT, SCORING, Result, TrackResult, next_step

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
CONTENT: dict[str, Any] = json.loads((CONFIG_DIR / "content.json").read_text())
EXAMPLE: dict[str, Any] = json.loads((CONFIG_DIR / "example_registration.json").read_text())
TAG = {"isa": "ISA", "ava": "AVA", "rt": "RT"}

CSS = """
<style>
/* Fonts come from [theme] in .streamlit/config.toml, not a font-family
   override here: an override that reaches Streamlit's own elements also hits
   its Material Symbols icons, which then render as their own names. */
:root {
  --line: #e3e6ea; --muted: #5c6672; --surface: #ffffff;
  --accent: #1f5eff; --accent-soft: #eef2ff;
  --good: #137a3f; --good-soft: #e6f4ea;
  --warn: #8a5a00; --warn-soft: #fdf3e0;
  --neutral: #4a5260; --neutral-soft: #eef0f3;
  --bad: #b3261e; --bad-soft: #fdeceb;
  --isa: #6b3fa0; --isa-soft: #f1ebfa;
  --font-mono: 'IBM Plex Mono', ui-monospace, SFMono-Regular, monospace;
}
.mono, dl.answers dd.mono { font-family: var(--font-mono); }
/* Belt and braces: never let a font rule reach an icon ligature. */
[data-testid="stIconMaterial"], span[class*="material-symbols"], .material-icons {
  font-family: 'Material Symbols Rounded' !important;
}
.chip {
  display: inline-block; font-size: 0.7rem; font-weight: 600; letter-spacing: 0.04em;
  padding: 2px 6px; border-radius: 4px; margin-right: 6px; vertical-align: 2px;
}
.chip.isa { background: var(--isa-soft); color: var(--isa); }
.chip.ava { background: var(--warn-soft); color: var(--warn); }
.chip.rt  { background: var(--accent-soft); color: var(--accent); }
.pill {
  display: inline-block; font-size: 0.75rem; font-weight: 600;
  padding: 3px 9px; border-radius: 999px;
}
.pill.fast { background: var(--good-soft); color: var(--good); }
.pill.review { background: var(--warn-soft); color: var(--warn); }
.pill.nurture { background: var(--neutral-soft); color: var(--neutral); }
.pill.notready { background: var(--bad-soft); color: var(--bad); }
.pill.go { background: var(--good-soft); color: var(--good); }
.pill.nogo { background: var(--neutral-soft); color: var(--neutral); }
.reco {
  border-left: 4px solid var(--accent); background: var(--accent-soft);
  padding: 12px 14px; border-radius: 0 8px 8px 0; margin: 4px 0 14px;
}
.reco strong { font-size: 1.05rem; display: block; }
.reco .seq { font-size: 0.9rem; font-weight: 600; margin: 6px 0 4px; }
.reco .why { font-size: 0.9rem; color: #2b313a; }
.tcard {
  border: 1px solid var(--line); border-radius: 8px; padding: 14px; background: var(--surface);
  height: 100%; display: flex; flex-direction: column; gap: 10px;
}
.tcard.primary { border-color: var(--accent); box-shadow: inset 0 0 0 1px var(--accent); }
.tcard.muted { opacity: 0.85; }
.tcard .order {
  font-size: 0.72rem; font-weight: 600; color: var(--accent);
  letter-spacing: 0.04em; text-transform: uppercase;
}
.tcard.muted .order { color: var(--muted); }
.tcard .num {
  font-family: var(--font-mono); font-size: 1.6rem; font-weight: 600; line-height: 1;
}
.tcard .num small { font-size: 0.85rem; color: var(--muted); font-weight: 400; }
.tcard ul { margin: 2px 0 0; padding-left: 1.1em; font-size: 0.85rem; }
.tcard ul li { margin-bottom: 3px; }
.tcard .next { font-size: 0.85rem; margin-top: auto; }
.bar { display: grid; grid-template-columns: 9em 1fr 3.6em; gap: 8px; align-items: center; font-size: 0.78rem; margin-bottom: 5px; }
.bar .track { background: var(--neutral-soft); border-radius: 999px; height: 7px; overflow: hidden; }
.bar .fill { background: var(--accent); height: 100%; }
.bar .val { font-family: var(--font-mono); color: var(--muted); text-align: right; }
ul.flags { list-style: none; margin: 0; padding: 0; font-size: 0.88rem; }
ul.flags li {
  border-left: 3px solid var(--neutral); background: var(--neutral-soft);
  padding: 8px 10px; border-radius: 0 6px 6px 0; margin-bottom: 8px;
}
ul.flags li.crit { border-color: var(--bad); background: var(--bad-soft); }
ul.flags li.warn { border-color: var(--warn); background: var(--warn-soft); }
ul.flags li.none { border-color: var(--good); background: var(--good-soft); }
ol.agenda { margin: 0; padding-left: 0; list-style: none; font-size: 0.86rem; }
ol.agenda li { display: grid; grid-template-columns: 3.4em 1fr; gap: 8px; margin-bottom: 8px; }
ol.agenda .t { font-family: var(--font-mono); color: var(--muted); }
dl.answers { display: grid; grid-template-columns: 11em 1fr; gap: 4px 12px; font-size: 0.86rem; margin: 0; }
dl.answers dt { color: var(--muted); }
dl.answers dd { margin: 0; }
.subhead {
  font-size: 0.76rem; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase;
  color: var(--muted); margin: 18px 0 0;
}
.steps { display: flex; flex-wrap: wrap; gap: 6px; font-size: 0.78rem; margin-bottom: 14px; }
.steps span { padding: 4px 9px; border-radius: 999px; background: var(--neutral-soft); color: var(--muted); }
.steps span.current { background: var(--accent); color: #fff; font-weight: 600; }
.steps span.done { background: var(--accent-soft); color: var(--accent); }
.hint { color: var(--muted); font-size: 0.82rem; }
.tag {
  font-size: 0.76rem; color: var(--muted); background: var(--neutral-soft);
  padding: 3px 8px; border-radius: 4px;
}
</style>
"""


def page(title: str, icon: str = "🛡️") -> None:
    """Standard page setup plus the shared stylesheet."""
    st.set_page_config(page_title=f"{title} · Identity & AI Assessments", page_icon=icon, layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)


def esc(text: Any) -> str:
    return html.escape(str(text if text is not None else ""))


def chip(track: str) -> str:
    return f'<span class="chip {track}">{TAG[track]}</span>'


def pill(route: str) -> str:
    return f'<span class="pill {route}">{ROUTE_TEXT[route]}</span>'


def steps_bar(current: int) -> str:
    names = ["1 · Partner", "2 · Customer", "3 · Identity", "4 · AI", "5 · Drivers"]
    out = []
    for i, name in enumerate(names, start=1):
        cls = "current" if i == current else "done" if i < current else ""
        out.append(f'<span class="{cls}">{name}</span>')
    return '<div class="steps">' + "".join(out) + "</div>"


def seq_html(r: Result) -> str:
    if not r.picks:
        return ""
    parts = [chip(k) + esc(NAME[k]) for k in r.picks]
    return '<div class="seq">' + ' <span class="hint">then</span> '.join(parts) + "</div>"


def reco_box(r: Result) -> str:
    return (
        '<div class="reco"><strong>' + esc(r.headline) + "</strong>"
        + seq_html(r)
        + '<span class="why">' + esc(r.why) + "</span></div>"
    )


def score_bars(track: str, t: TrackResult) -> str:
    rows = []
    for area in AREAS[track]:
        val, mx = t.areas[area["key"]], area["max"]
        pct = round(val / mx * 100) if mx else 0
        rows.append(
            f'<div class="bar"><span>{esc(area["label"])}</span>'
            f'<div class="track" role="img" aria-label="{esc(area["label"])} {val} of {mx}">'
            f'<div class="fill" style="width:{pct}%"></div></div>'
            f'<span class="val">{val}/{mx}</span></div>'
        )
    return "".join(rows)


def order_label(position: int) -> str:
    if position == -1:
        return "Not recommended now"
    return {0: "Recommended · start here", 1: "Recommended · second", 2: "Recommended · third"}[position]


def track_card(track: str, r: Result, a: dict, show_score: bool = False) -> str:
    t = r.tracks[track]
    pos = r.picks.index(track) if track in r.picks else -1
    cls = " primary" if pos == 0 else " muted" if pos == -1 else ""
    html_parts = [
        f'<div class="tcard{cls}">',
        f'<span class="order">{order_label(pos)}</span>',
        f"<div>{chip(track)}<strong>{esc(NAME[track])}</strong></div>",
        '<div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">'
        f'<span class="num">{t.total}<small>/100</small></span>{pill(t.route)}</div>',
    ]
    if show_score:
        html_parts.append("<div>" + score_bars(track, t) + "</div>")
    if t.why:
        html_parts.append("<ul>" + "".join(f"<li>{esc(w)}</li>" for w in t.why[:4]) + "</ul>")
    html_parts.append(f'<p class="next"><strong>Next:</strong> {esc(next_step(track, t.route, a))}</p></div>')
    return "".join(html_parts)


def flags_html(r: Result) -> str:
    if not r.flags:
        return '<ul class="flags"><li class="none">No flags. Proceed to scoping.</li></ul>'
    items = []
    for fl in r.flags:
        cls = "crit" if fl.severity == "crit" else "warn"
        chips = "".join(chip(t) for t in fl.tracks)
        items.append(f'<li class="{cls}">{chips}{esc(fl.text)}</li>')
    return '<ul class="flags">' + "".join(items) + "</ul>"


def answers_dl(rows: list[tuple[str, str]]) -> str:
    cells = "".join(f"<dt>{esc(k)}</dt><dd>{esc(v)}</dd>" for k, v in rows if v)
    return f'<dl class="answers">{cells}</dl>'


def agenda_html(track: str) -> str:
    items = "".join(
        f'<li><span class="t">{esc(slot)}</span><span><strong>{esc(head)}.</strong> {esc(body)}</span></li>'
        for slot, head, body in CONTENT["scoping_calls"][track]["agenda"]
    )
    return f'<ol class="agenda">{items}</ol>'


def gate_pill(done: int, total: int) -> str:
    if done >= total:
        return '<span class="pill go">Go</span>'
    return f'<span class="pill nogo">Not ready · {done} of {total}</span>'


# ---------- rubrics, generated from config/scoring.json ----------
def _scale_text(track: str, field: str) -> str:
    pts = POINTS[track].get(field, {})
    groups: dict[int, list[str]] = {}
    for opt in QUESTIONS[field]["options"]:
        if opt["value"] in pts:
            groups.setdefault(pts[opt["value"]], []).append(opt["label"])
    return " · ".join(
        f"{' or '.join(ls)} {val}" for val, ls in sorted(groups.items(), key=lambda kv: -kv[0])
    )


def rubric_rows(track: str) -> list[dict[str, Any]]:
    """Area / question / scale / max for each scored field, from scoring.json."""
    area_label = {a["key"]: a["label"] for a in AREAS[track]}
    rows = []
    for spec in SCORING["rubric_fields"][track]:
        field = spec["field"]
        pts = POINTS[track].get(field, {})
        rows.append(
            {
                "Area": area_label[spec["area"]],
                "Question": spec.get("label") or QUESTIONS[field]["label"],
                "Points": spec.get("scale") or _scale_text(track, field),
                "Max": spec.get("max", max(pts.values()) if pts else 0),
            }
        )
    return rows


def isa_vs_ava_rows() -> list[dict[str, str]]:
    return [
        {"": "Identities covered", "ISA": "Human, non-human and AI agents", "AVA": "AI agents only"},
        {"": "Agent and NHI depth", "ISA": "Basic", "AVA": "Deep (agents)"},
        {"": "Instance", "ISA": "Sovereign Cisco Identity Intelligence instance", "AVA": "US-hosted Cisco Identity Intelligence instance"},
        {"": "Connects to", "ISA": "Identity providers, read-only APIs", "AVA": "CrowdStrike Falcon or Microsoft Defender"},
        {"": "Duration", "ISA": "Up to 14 days for data to stabilise", "AVA": "One week"},
        {"": "Output", "ISA": "Findings report and readout", "AVA": "PDF readout"},
        {"": "Pick when", "ISA": "Human identity gaps matter, or data must stay in-region", "AVA": "Agents are the main concern, the EDR fits and US hosting is acceptable"},
    ]


# ---------- question widgets ----------
# Widgets are deliberately keyless and seeded from `store`, so values survive the
# step-by-step wizard (Streamlit drops the state of widgets it doesn't render).
def question_radio(field: str, question: str, store: dict, hint: str | None = None,
                   horizontal: bool = False) -> str:
    from .scoring import label

    opts = [o["value"] for o in QUESTIONS[field]["options"]]
    current = store.get(field) or ""
    value = st.radio(
        question,
        opts,
        index=opts.index(current) if current in opts else None,
        format_func=lambda v: label(field, v),
        horizontal=horizontal,
        help=hint,
    )
    return value or ""


def question_multi(field: str, question: str, store: dict, hint: str | None = None) -> list[str]:
    from .scoring import label

    opts = [o["value"] for o in QUESTIONS[field]["options"]]
    default = [v for v in (store.get(field) or []) if v in opts]
    return list(st.multiselect(question, opts, default=default, format_func=lambda v: label(field, v), help=hint))


def resolve_exclusive(selection: list[str], previous: list[str], exclusive: str) -> list[str]:
    """"None yet" and the real options cancel each other out."""
    if exclusive in selection and exclusive not in previous:
        return [exclusive]
    if exclusive in selection and len(selection) > 1:
        return [v for v in selection if v != exclusive]
    return list(selection)


def select(label_text: str, options: list[str], store: dict, field: str) -> str:
    current = store.get(field) or ""
    return st.selectbox(
        label_text,
        options,
        index=options.index(current) if current in options else None,
        placeholder="Select…",
    ) or ""


def text(label_text: str, store: dict, field: str, optional: bool = False,
         placeholder: str = "") -> str:
    return st.text_input(
        label_text + (" (optional)" if optional else ""),
        value=store.get(field) or "",
        placeholder=placeholder,
    ).strip()


def assessment_summary() -> None:
    """The three assessment explainers from content.json."""
    for track, info in CONTENT["assessments"].items():
        st.markdown(f"{chip(track)}**{esc(info['name'])}**", unsafe_allow_html=True)
        st.markdown("\n".join(f"- {b}" for b in info["bullets"]))
