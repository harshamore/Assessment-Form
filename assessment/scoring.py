"""Scoring and routing for the Identity & AI assessment intake.

Pure functions, no Streamlit imports. Ported from reference/intake_prototype.html
and checked against tests/expected_results.json.

Point values, thresholds and labels live in config/. Change them there, not here.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
QUESTIONS: dict[str, Any] = json.loads((CONFIG_DIR / "questions.json").read_text())
SCORING: dict[str, Any] = json.loads((CONFIG_DIR / "scoring.json").read_text())
POINTS: dict[str, dict[str, dict[str, int]]] = SCORING["points"]
AREAS: dict[str, list[dict[str, Any]]] = SCORING["areas"]
TRACKS = ("isa", "ava", "rt")
NAME = {"isa": "Identity Security Assessment", "ava": "Agent Visibility Assessment", "rt": "AI Red Teaming Assessment"}
SHORT = {"isa": "ISA", "ava": "AVA", "rt": "AI Red Teaming"}
ROUTE_TEXT = {"fast": "Fast-track", "review": "Cisco review", "nurture": "Nurture", "notready": "Not ready"}


# ---------- helpers ----------
def label(key: str, value: str) -> str:
    for opt in QUESTIONS[key]["options"]:
        if opt["value"] == value:
            return opt["label"]
    return "—"


def labels(key: str, values: list[str] | None) -> str:
    return ", ".join(label(key, v) for v in (values or [])) or "—"


def p(track: str, key: str, value: str | None) -> int:
    return POINTS[track].get(key, {}).get(value or "", 0)


def pmax(track: str, key: str, values: list[str] | None) -> int:
    return max([p(track, key, v) for v in (values or [])] + [0])


def agent_list(a: dict) -> list[str]:
    return [x for x in a.get("agentsUse", []) if x != "none"]


def agents_in_use(a: dict) -> bool:
    return len(agent_list(a)) > 0


def edr_fits(a: dict) -> bool:
    return a.get("edr") in SCORING["ava_supported_edr"]


def route_for(total: int, eligible: bool, personal: bool) -> str:
    if not eligible:
        return "notready"
    th = SCORING["thresholds"]
    r = "fast" if total >= th["fast"] else "review" if total >= th["review"] else "nurture"
    if personal and r == "fast":
        r = "review"
    return r


# ---------- result types ----------
@dataclass
class TrackResult:
    areas: dict[str, int]
    total: int
    eligible: bool
    route: str = ""
    why: list[str] = field(default_factory=list)

    @property
    def qualifies(self) -> bool:
        return self.route in ("fast", "review")


@dataclass
class Flag:
    severity: str  # "crit" or "" (warning)
    tracks: list[str]  # subset of TRACKS; empty = applies to all
    text: str


@dataclass
class Result:
    personal_email: bool
    tracks: dict[str, TrackResult]
    picks: list[str]
    why: str
    flags: list[Flag]

    @property
    def headline(self) -> str:
        if not self.picks:
            return "Not ready for any assessment yet"
        return "Recommended: " + ", then ".join(SHORT[k] for k in self.picks)

    def card_order(self) -> list[str]:
        rest = sorted([k for k in TRACKS if k not in self.picks], key=lambda k: -self.tracks[k].total)
        return self.picks + rest


# ---------- scoring ----------
def score(a: dict) -> Result:
    """Score one registration. `a` uses the field names in config/questions.json plus
    name/email/company etc. (see SPEC.md, "Answer model")."""
    domain = (a.get("email", "").split("@") + [""])[1].lower()
    personal = domain in SCORING["personal_email_domains"]
    agents = agents_in_use(a)
    n_agents = len(agent_list(a))
    supported = any(x != "other" for x in a.get("idps", []))
    builds = a.get("aiUse") == "builds"
    agent_gap = agents and (a.get("agentVis") != "yes" or a.get("agentAuth") != "dedicated")
    human_gaps = sum([
        a.get("singleView") != "yes",
        a.get("mfa") in ("partial", "unknown"),
        a.get("dormant") in ("never", "annual"),
        a.get("nhiInv") in ("none", "unknown"),
    ])

    # ISA
    isa = {
        "ready": (SCORING["isa_supported_idp_points"] if supported else 0) + p("isa", "roAccess", a.get("roAccess")),
        "gap": p("isa", "singleView", a.get("singleView")) + p("isa", "mfa", a.get("mfa")) + p("isa", "dormant", a.get("dormant"))
        + p("isa", "nhiInv", a.get("nhiInv"))
        + (p("isa", "agentVis", a.get("agentVis")) if agents else p("isa", "nhiRot", a.get("nhiRot"))),
        "trigger": pmax("isa", "drivers", a.get("drivers")) + p("isa", "deadline", a.get("deadline")),
        "fit": p("isa", "humans", a.get("humans")),
    }
    isa_eligible = supported and a.get("roAccess") != "no"

    # AVA
    ava = {"ready": 0, "gap": 0, "trigger": 0, "fit": 0}
    if agents:
        breadth = SCORING["ava_agent_breadth_points"]
        ava["ready"] = p("ava", "edr", a.get("edr")) + p("ava", "residency", a.get("residency"))
        ava["gap"] = p("ava", "agentVis", a.get("agentVis")) + p("ava", "agentAuth", a.get("agentAuth")) + (
            breadth["3_or_more"] if n_agents >= 3 else breadth["2"] if n_agents == 2 else breadth["1"])
        ava["trigger"] = pmax("ava", "drivers", a.get("drivers")) + p("ava", "deadline", a.get("deadline"))
        ava["fit"] = p("ava", "size", a.get("size"))
    ava_eligible = agents and edr_fits(a) and a.get("residency") != "sovereign"

    # RT
    rt = {"target": 0, "trigger": 0, "authority": 0, "fit": 0}
    if builds:
        rt["target"] = p("rt", "modelType", a.get("modelType")) + p("rt", "count", a.get("count")) + p("rt", "endpoint", a.get("endpoint"))
        rt["trigger"] = p("rt", "stage", a.get("stage")) + p("rt", "deadline", a.get("deadline")) + pmax("rt", "drivers", a.get("drivers"))
        rt["authority"] = p("rt", "role", a.get("role")) + p("rt", "owner", a.get("owner")) + p("rt", "prior", a.get("prior"))
        rt["fit"] = p("rt", "industry", a.get("industry")) + p("rt", "size", a.get("size"))
    rt_eligible = builds and a.get("endpoint") != "no"

    T = {
        "isa": TrackResult(isa, sum(isa.values()), isa_eligible),
        "ava": TrackResult(ava, sum(ava.values()), ava_eligible),
        "rt": TrackResult(rt, sum(rt.values()), rt_eligible),
    }
    for t in T.values():
        t.route = route_for(t.total, t.eligible, personal)

    # Reasons
    edr_name = label("edr", a.get("edr", ""))
    w = T["isa"].why
    if not supported: w.append("No supported identity provider identified yet")
    if a.get("roAccess") == "no": w.append("Read-only access to identity providers isn't possible")
    if a.get("singleView") != "yes": w.append("No single view of identities across directories")
    if a.get("mfa") in ("partial", "unknown"): w.append("MFA coverage is partial or unknown")
    if a.get("dormant") in ("never", "annual"): w.append("Dormant and privileged accounts are rarely reviewed")
    if a.get("nhiInv") in ("none", "unknown"): w.append("No inventory of non-human identities")
    if a.get("residency") == "sovereign": w.append("Data must stay in-region, which the sovereign instance allows")

    w = T["ava"].why
    if not agents:
        w.append("No AI agents in use yet")
    else:
        if not edr_fits(a): w.append("Needs CrowdStrike Falcon or Microsoft Defender. The customer runs " + edr_name)
        if a.get("residency") == "sovereign": w.append("Data must stay in-region, but AVA runs on a US-hosted instance")
        if a.get("agentVis") != "yes": w.append("Can't fully list agents and what they can access")
        auth = a.get("agentAuth")
        if auth in ("shared", "delegated", "unknown"):
            w.append("Agents authenticate with " + {"unknown": "unknown credentials", "shared": "shared service accounts or keys", "delegated": "users' own credentials"}[auth])
        if n_agents >= 2: w.append(f"Agents on {n_agents} different platforms")

    w = T["rt"].why
    if not builds:
        w.append("Only uses SaaS AI tools, so there's nothing of theirs to test" if a.get("aiUse") == "saasonly" else "Not building or running AI yet")
    else:
        if a.get("endpoint") == "no": w.append("No endpoint the test can reach")
        if a.get("stage") == "launch": w.append("Launching within 3 months")
        if a.get("stage") == "prod": w.append("Already in production")
        if a.get("prior") in ("none", "adhoc"): w.append("No external adversarial testing so far")
        if "agents" in a.get("scope", []): w.append("Agents in scope, so tool misuse can be tested")
        if a.get("modelType") == "finetuned": w.append("Fine-tuned model, where safety alignment can weaken")

    # Identity pick
    id_picks: list[str] = []
    id_why = ""
    if T["isa"].qualifies and T["ava"].qualifies:
        if human_gaps >= SCORING["human_gap_threshold_for_both_identity"]:
            id_picks = ["ava", "isa"] if T["ava"].total >= T["isa"].total else ["isa", "ava"]
            id_why = f"Run AVA for deep agent visibility through {edr_name} (one week), and ISA for the human and non-human identity gaps. They can run in parallel."
        else:
            id_picks = ["ava"]
            id_why = f"Agents are the main identity gap and {edr_name} is in place, so AVA gives deep agent visibility in one week. Human identity hygiene looks reasonable, so ISA can wait."
    elif T["ava"].qualifies:
        id_picks = ["ava"]
        id_why = f"AVA gives deep agent visibility through {edr_name} in one week." + ("" if T["isa"].eligible else " ISA isn't possible yet.")
    elif T["isa"].qualifies:
        id_picks = ["isa"]
        id_why = "ISA covers human, non-human and agent identities on the sovereign instance."
        if agents and not T["ava"].eligible:
            id_why += " Agent visibility will be basic, because AVA isn't possible: " + (
                "data must stay in-region." if a.get("residency") == "sovereign" else "it needs CrowdStrike Falcon or Microsoft Defender.")

    # Overall order: identity first when agents lack visible identities, otherwise by score
    picks = list(id_picks)
    if T["rt"].qualifies:
        id_best = max([T[k].total for k in id_picks] + [-1])
        if not id_picks:
            picks = ["rt"]
        elif not agent_gap and T["rt"].total > id_best:
            picks = ["rt"] + id_picks
        else:
            picks = id_picks + ["rt"]

    why: list[str] = []
    if id_why: why.append(id_why)
    if T["rt"].qualifies:
        why.append("Then red team the agents and AI apps once their identities are visible."
                   if agent_gap and id_picks and picks[0] != "rt" else "The AI Red Teaming Assessment fits as well.")
    if not picks: why.append("None of the three assessments is ready. Use the nurture steps and revisit in 30 days.")

    # Flags
    f: list[Flag] = []
    idps = a.get("idps", [])
    if personal: f.append(Flag("crit", [], "Customer contact has a personal email address. Verify the organisation before scheduling."))
    if a.get("owner") == "no": f.append(Flag("crit", [], "No owner for findings. Name one on the call or don't run any assessment."))
    if agents and a.get("agentAuth") == "delegated": f.append(Flag("crit", ["ava", "isa"], "Agents act with users' own credentials, so agent actions can't be told apart from human ones. Make this a headline in the readout."))
    if agents and a.get("residency") == "sovereign": f.append(Flag("", ["isa"], "Data must stay in-region, so AVA (US-hosted) is out. ISA covers agents, but its agent and NHI visibility is basic. Set expectations."))
    if agents and not edr_fits(a): f.append(Flag("", ["ava"], f"AVA needs CrowdStrike Falcon or Microsoft Defender. The customer runs {edr_name}."))
    if T["ava"].eligible and a.get("residency") in ("approval", "unsure"): f.append(Flag("", ["ava"], "AVA runs on a US-hosted instance. Get written approval for US processing before starting."))
    if "isa" in picks and agents and "ava" not in picks and a.get("residency") != "sovereign": f.append(Flag("", ["isa"], "ISA's agent and NHI visibility is basic compared with AVA. Revisit AVA if agents become the main concern."))
    if a.get("roAccess") == "approval": f.append(Flag("", ["isa"], "Read-only access needs approval. Find out who approves it and get them on the scoping call."))
    if "ad" in idps and "entra" not in idps: f.append(Flag("", ["isa"], "On-premises Active Directory only. Confirm how it connects before promising coverage."))
    if "other" in idps: f.append(Flag("", ["isa"], "Unlisted or unknown identity provider. Check it against the supported integrations."))
    if agents and a.get("agentAuth") == "shared": f.append(Flag("", ["ava", "isa"], "Agents share service accounts or keys. Ask who owns those credentials and when they were last rotated."))
    if "mcp" in a.get("agentsUse", []): f.append(Flag("", ["ava", "rt"], "MCP servers in use. Ask which tools they expose and how they authenticate."))
    if builds:
        if a.get("endpoint") == "prod": f.append(Flag("", ["rt"], "Production-only endpoint. Agree a testing window and rate limits, and tell the SOC."))
        if a.get("modelType") == "hosted": f.append(Flag("", ["rt"], "Hosted API model. Check the provider's terms allow adversarial testing. Token costs land on the customer."))
        if "agents" in a.get("scope", []): f.append(Flag("", ["rt"], "Agents in scope. List each agent's tools and data, and confirm tests can't trigger real actions."))
        if a.get("prior") == "recent": f.append(Flag("", ["rt"], "Tested recently. Position this as a re-test after changes."))
    if "regulator" in a.get("drivers", []): f.append(Flag("", [], "Regulatory driver. Ask which framework and what evidence the auditor expects."))

    return Result(personal, T, picks, " ".join(why), f)


def next_step(track: str, route: str, a: dict) -> str:
    pam = a.get("partner", {}).get("pamName", "your Cisco PAM")
    edr_name = label("edr", a.get("edr", ""))
    if route == "fast":
        return {
            "isa": "Book the 15-minute ISA scoping call with the identity owner, and get read-only access approved.",
            "ava": f"Book the 15-minute AVA scoping call, and get the {edr_name} integration and US-hosted processing approved.",
            "rt": "Book the 20-minute RT scoping call with the target owner, and ask for the endpoint details.",
        }[track]
    if route == "review":
        return f"Send the handoff note to {pam}. Cisco replies within 2 business days."
    if route == "nurture":
        return {
            "isa": "Share the identity self-serve link and revisit when there's a driver or date.",
            "ava": "Revisit when the agent rollout has a date or a driver.",
            "rt": "Share the AI red teaming self-serve tool and revisit in 30 days.",
        }[track]
    if track == "isa":
        return "Find out what would allow read-only access, then revisit." if a.get("roAccess") == "no" else "Confirm which identity provider they use, then revisit."
    if track == "ava":
        if not agents_in_use(a):
            return "Revisit when the customer deploys AI agents."
        if a.get("residency") == "sovereign":
            return "Data must stay in-region. Use ISA on the sovereign instance instead."
        return "AVA needs CrowdStrike Falcon or Microsoft Defender. Use ISA instead."
    return "A reachable endpoint is needed. Revisit when one can be arranged." if a.get("aiUse") == "builds" else "Revisit when the customer builds or runs its own AI."


def handoff_note(a: dict, r: Result) -> str:
    """Plain-text note the partner sends to their Cisco PAM. Same layout as the prototype."""
    pt = a.get("partner", {})
    agents = agents_in_use(a)
    b = a.get("aiUse") == "builds"

    def tag(k: str) -> str:
        return "RT" if k == "rt" else k.upper()

    def track_lines(k: str) -> str:
        t = r.tracks[k]
        lines = [f"{tag(k)} ({NAME[k]}): {t.total}/100 → {ROUTE_TEXT[t.route]}"]
        lines += [f"  {ar['label']}: {t.areas[ar['key']]}/{ar['max']}" for ar in AREAS[k]]
        lines += [f"  · {w}" for w in t.why]
        lines.append("  Next: " + next_step(k, t.route, a))
        return "\n".join(lines)

    flags = "\n".join(
        "  - " + (("[" + "+".join(tag(x) for x in fl.tracks) + "] ") if fl.tracks else "") + fl.text for fl in r.flags
    ) or "  - none"

    return "\n".join([
        "IDENTITY & AI ASSESSMENTS · PARTNER REGISTRATION",
        f"Partner: {pt.get('org', '')} ({pt.get('country', '')})",
        f"Registered by: {pt.get('name', '')}" + (f", {pt['title']}" if pt.get("title") else "") + f" · {pt.get('email', '')}" + (f" · {pt['phone']}" if pt.get("phone") else ""),
        f"Cisco PAM: {pt.get('pamName', '')} · {pt.get('pamEmail', '')}",
        "",
        f"Customer: {a.get('company', '')} | {a.get('country', '')} | {label('industry', a.get('industry', ''))} | {label('size', a.get('size', ''))}",
        f"Contact: {a.get('name', '')}" + (f", {a['ctitle']}" if a.get("ctitle") else "") + f" ({label('role', a.get('role', ''))}) · {a.get('email', '')}" + (f" · {a['cphone']}" if a.get("cphone") else ""),
        "",
        r.headline.upper(),
        r.why,
        "",
        "\n\n".join(track_lines(k) for k in r.card_order()),
        "",
        f"Identity: {labels('idps', a.get('idps'))}; {label('humans', a.get('humans', ''))} humans; single view: {label('singleView', a.get('singleView', ''))}; MFA: {label('mfa', a.get('mfa', ''))}",
        f"NHI: inventory {label('nhiInv', a.get('nhiInv', ''))}; rotation {label('nhiRot', a.get('nhiRot', ''))}",
        f"Agents: {labels('agentsUse', a.get('agentsUse'))}" + (f"; auth: {label('agentAuth', a.get('agentAuth', ''))}; visibility: {label('agentVis', a.get('agentVis', ''))}" if agents else ""),
        f"Read-only identity access: {label('roAccess', a.get('roAccess', ''))}; EDR: {label('edr', a.get('edr', ''))}; US-hosted processing: {label('residency', a.get('residency', ''))}",
        f"Own AI: {label('aiUse', a.get('aiUse', ''))}" + (f"; scope: {labels('scope', a.get('scope'))}; {label('modelType', a.get('modelType', ''))}; {label('stage', a.get('stage', ''))}; endpoint: {label('endpoint', a.get('endpoint', ''))}" if b else ""),
        f"Drivers: {labels('drivers', a.get('drivers'))}; deadline: {label('deadline', a.get('deadline', ''))}; findings owner: {label('owner', a.get('owner', ''))}",
        f"Authorisation confirmed: {'yes' if a.get('attest') else 'no'}; consent to share with Cisco: {'yes' if a.get('consent') else 'no'}",
        "",
        "Flags:",
        flags,
    ])
