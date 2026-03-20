"""
RCA Reasoning Scaffolder
Integrated UI + AI Extension Demo
Run:
    streamlit run rca_scaffolder_integrated.py

Optional:
    set ANTHROPIC_API_KEY for AI expansion mode

This version keeps the investigation workspace as the main system
and inserts the AI extension inside the scaffold instead of making it
a separate analysis page.
"""

from __future__ import annotations

import html
import json
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import streamlit as st


# =========================================================
# Page config
# =========================================================
st.set_page_config(
    page_title="RCA Reasoning Scaffolder",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# =========================================================
# Data model
# =========================================================
@dataclass
class Hypothesis:
    id: str
    description: str
    factors: List[str]
    evidence: List[str]
    status: str = "active"   # active / narrowed / discarded


@dataclass
class RCAWorkspace:
    title: str
    summary: str
    hypotheses: List[Hypothesis] = field(default_factory=list)


def build_example_case() -> RCAWorkspace:
    return RCAWorkspace(
        title="Deviation in GMP environmental monitoring record review",
        summary=(
            "During environmental monitoring review, a deviation was identified involving a possible "
            "sampling sequence issue. Initial discussion emphasized operator behavior, but the procedure "
            "required repeated cross-checking across multiple sections. The event also occurred during a "
            "busy handoff period, and room conditions may have shifted during the event window."
        ),
        hypotheses=[
            Hypothesis(
                id="H1",
                description="Sampling sequence may have been misunderstood by the operator.",
                factors=[
                    "Operator interpretation of sequence instructions",
                    "Training completion may not reflect practical interpretability",
                    "Task executed during shift transition",
                ],
                evidence=[
                    "Training record completed",
                    "Operator followed part of the written sequence",
                    "Sequence step order required cross-reference between sections",
                ],
            ),
            Hypothesis(
                id="H2",
                description="Procedure structure may have introduced ambiguity in the required sequence.",
                factors=[
                    "Cross-reference burden across multiple sections",
                    "Sequence instructions distributed across separate document locations",
                    "Ambiguous wording around verification order",
                ],
                evidence=[
                    "Relevant steps split across sections",
                    "Procedure contains repeated wording with unclear ordering",
                    "Multiple readers could plausibly interpret the sequence differently",
                ],
            ),
            Hypothesis(
                id="H3",
                description="Contextual workflow conditions may have shaped how the task was performed.",
                factors=[
                    "Shift handoff timing",
                    "Competing monitoring tasks in the same window",
                    "Room/environmental context may have changed during execution",
                ],
                evidence=[
                    "Event occurred during handoff period",
                    "Multiple concurrent review tasks were active",
                    "Context window overlapped with routine operational pressure",
                ],
            ),
        ],
    )


STEPS = {
    1: ("Intake", "Read the deviation and understand what happened before forming any explanation."),
    2: ("Open Hypotheses", "List all possible explanations. Do not narrow yet — keep everything visible."),
    3: ("Attach Reasoning", "For the selected hypothesis, review factors, evidence, and add your notes."),
    4: ("Narrowing", "Decide which paths to keep, narrow, or drop — after reviewing each one."),
    5: ("Pre-Closure", "Review what remained visible and what was compressed before you close."),
}


# =========================================================
# AI / PAC logic (kept aligned with prior AI extension)
# =========================================================
INDIVIDUAL_BLAME_TERMS = [
    "operator error", "human error", "analyst error",
    "did not follow", "failed to follow", "careless",
    "negligence", "mistake by operator", "employee mistake",
    "technician mistake", "user error", "personnel error",
]

CONTEXT_TERMS = [
    "environment", "temperature", "humidity", "timing", "shift",
    "room", "workflow", "handoff", "context", "condition", "monitoring"
]

TRAINING_TERMS = [
    "training", "qualified", "qualification", "understanding", "interpretation"
]

EQUIPMENT_TERMS = [
    "equipment", "instrument", "machine", "device"
]

RECORD_TERMS = [
    "record", "documentation", "entry", "log"
]


def normalize(text: str) -> str:
    return text.strip().lower()


def contains_any(text: str, terms: List[str]) -> bool:
    return any(t in text for t in terms)


def detect_pac_risk(hypothesis: str) -> Dict:
    h = normalize(hypothesis)
    matches = [t for t in INDIVIDUAL_BLAME_TERMS if t in h]

    if matches:
        return {
            "level": "High",
            "color": "#dc2626",
            "bg": "#fef2f2",
            "border": "#fca5a5",
            "label": "PAC warning signal: high",
            "message": (
                "This hypothesis is converging early on an individual actor. "
                "Procedural, contextual, and organizational contributors may be closing off "
                "before they have been examined."
            ),
            "matched": matches,
        }

    if any(w in h for w in ["operator", "analyst", "personnel", "staff", "technician"]):
        return {
            "level": "Moderate",
            "color": "#d97706",
            "bg": "#fff7ed",
            "border": "#fdba74",
            "label": "PAC warning signal: moderate",
            "message": (
                "The current hypothesis foregrounds an individual actor. "
                "This does not necessarily indicate premature closure, "
                "but systemic contributors should remain explicitly visible."
            ),
            "matched": [],
        }

    return {
        "level": "Low",
        "color": "#16a34a",
        "bg": "#f0fdf4",
        "border": "#86efac",
        "label": "PAC warning signal: low",
        "message": (
            "No strong individual-blame language detected. "
            "Continue checking that multiple causal pathways remain open."
        ),
        "matched": [],
    }


def generate_pathways(summary: str, hypothesis: str) -> List[Dict]:
    text = normalize(summary + " " + hypothesis)
    paths = []

    paths.append({
        "id": "procedural",
        "title": "Procedural / documentation pathway",
        "icon": "📄",
        "desc": (
            "The event may reflect ambiguity, fragmentation, or cross-reference burden "
            "in the procedure itself."
        ),
        "prompt": "What would this event look like if the procedure — not the person — was the primary contributor?",
    })

    if contains_any(text, CONTEXT_TERMS) or "deviation" in text:
        paths.append({
            "id": "contextual",
            "title": "Contextual / workflow pathway",
            "icon": "🌡️",
            "desc": (
                "The deviation may have been shaped by task conditions, environmental instability, "
                "timing pressure, handoff issues, or surrounding workflow constraints."
            ),
            "prompt": "What contextual or environmental conditions were present that could have shaped the outcome?",
        })

    if contains_any(text, TRAINING_TERMS) or "understand" in text or "misunder" in text:
        paths.append({
            "id": "interpretation",
            "title": "Interpretation / training pathway",
            "icon": "🧩",
            "desc": (
                "The issue may involve differences in procedural interpretation, incomplete conceptual "
                "understanding, or a mismatch between formal training completion and practical interpretability."
            ),
            "prompt": "Could different investigators interpret the same procedure differently — and if so, why?",
        })

    if contains_any(text, EQUIPMENT_TERMS):
        paths.append({
            "id": "equipment",
            "title": "Equipment / interface pathway",
            "icon": "⚙️",
            "desc": (
                "The event may involve equipment condition, instrument behavior, or interface design "
                "that shaped how the task was carried out."
            ),
            "prompt": "How did the equipment or interface design constrain or shape the actor's available actions?",
        })

    if contains_any(text, RECORD_TERMS):
        paths.append({
            "id": "documentation",
            "title": "Documentation / recording pathway",
            "icon": "📝",
            "desc": (
                "The apparent issue may partly reflect how the event was documented, compressed, or "
                "later reconstructed, rather than the original action alone."
            ),
            "prompt": "How might the act of documenting this event have shaped how it is now being explained?",
        })

    seen, out = set(), []
    for p in paths:
        if p["id"] not in seen:
            out.append(p)
            seen.add(p["id"])
    return out[:5]


def generate_evidence(summary: str, hypothesis: str) -> List[str]:
    text = normalize(summary + " " + hypothesis)
    ev = [
        "Review the full SOP and all cross-referenced documents relevant to this task.",
        "Identify what evidence would specifically distinguish procedural ambiguity from individual noncompliance.",
        "Check whether alternative explanatory paths were raised and then prematurely narrowed.",
    ]
    if contains_any(text, CONTEXT_TERMS):
        ev.append("Review environmental logs and operating conditions during the event window.")
    if contains_any(text, TRAINING_TERMS) or "operator" in text or "analyst" in text:
        ev.append("Examine training records alongside how the procedure is actually interpreted in practice.")
    if contains_any(text, EQUIPMENT_TERMS):
        ev.append("Check equipment condition, interface usability, alarms, and maintenance history.")
    if contains_any(text, RECORD_TERMS):
        ev.append("Compare the original event with how it was later recorded in the deviation narrative.")

    seen, out = set(), []
    for item in ev:
        if item not in seen:
            out.append(item)
            seen.add(item)
    return out[:6]


def generate_questions() -> List[str]:
    return [
        "What would this event look like if individual blame were temporarily set aside?",
        "Which causal path is currently being treated as most obvious — and why?",
        "What relevant evidence has not yet been examined before narrowing toward closure?",
        "Could documentation structure or workflow conditions have shaped the actor's action?",
        "If a different person had been in the same situation, would the same outcome have occurred?",
    ]


# =========================================================
# Anthropic API
# prompt/model kept aligned with prior version
# =========================================================
def get_anthropic_key():
    secrets_obj = getattr(st, "secrets", {})
    try:
        secret_key = secrets_obj.get("ANTHROPIC_API_KEY", None)
    except Exception:
        secret_key = None
    return os.getenv("ANTHROPIC_API_KEY") or secret_key


def extract_json_object(raw: str) -> Dict:
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def run_claude_expansion(summary: str, hypothesis: str) -> Dict:
    import anthropic

    client = anthropic.Anthropic(api_key=get_anthropic_key())

    prompt = f"""You are a reasoning-space scaffold for Root Cause Analysis (RCA) in regulated environments.

Your job is NOT to determine the final root cause.
Do NOT give a final compliance decision.
Do NOT collapse the explanation into one neat answer.

Your role: preserve reasoning space, identify possible premature accountability convergence (PAC),
and suggest what additional evidence should be examined before closure.

Return ONLY valid JSON with this exact shape:
{{
  "alternative_pathways": [
    {{"title": "short title", "desc": "1-2 sentence description", "question": "one reopening question"}},
    {{"title": "short title", "desc": "1-2 sentence description", "question": "one reopening question"}},
    {{"title": "short title", "desc": "1-2 sentence description", "question": "one reopening question"}}
  ],
  "pac_warning": "2-3 sentence warning about whether responsibility may be converging too early",
  "next_evidence": ["item 1", "item 2", "item 3"],
  "reopening_questions": ["question 1", "question 2", "question 3"]
}}

Case summary:
{summary}

Current hypothesis:
{hypothesis}"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    content_blocks = getattr(message, "content", None)
    if not content_blocks:
        raise ValueError("Claude response did not include content.")

    raw = content_blocks[0].text.strip()
    return extract_json_object(raw)


# =========================================================
# Helpers
# =========================================================
def esc(text: str) -> str:
    return html.escape(text or "").replace("\n", "<br>")


def render(raw_html: str):
    st.markdown(raw_html, unsafe_allow_html=True)


def overline(t: str) -> str:
    return (
        f'<div style="font-size:11px;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:.08em;color:#9ca3af;margin-bottom:8px;">{esc(t)}</div>'
    )


def heading(t: str, size="18px", mb="10px") -> str:
    return (
        f'<div style="font-size:{size};font-weight:700;color:#111827;'
        f'line-height:1.35;margin-bottom:{mb};">{esc(t)}</div>'
    )


def body(t: str) -> str:
    return f'<div style="font-size:14px;color:#4b5563;line-height:1.7;">{t}</div>'


def slabel(t: str, mt="14px") -> str:
    return (
        f'<div style="font-size:11px;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:.07em;color:#9ca3af;margin:{mt} 0 6px;">{esc(t)}</div>'
    )


CARD = (
    "background:#ffffff;border:1px solid #e5e7eb;border-radius:12px;"
    "padding:22px 24px;margin-bottom:12px;box-shadow:0 1px 3px rgba(0,0,0,.05);"
)


def badge(status: str) -> str:
    cfg = {
        "active": ("Active", "#1a56db", "#e8f0fe", "#c3d8fd"),
        "narrowed": ("Narrowed", "#92400e", "#fef3c7", "#fde68a"),
        "discarded": ("Dropped", "#374151", "#f3f4f6", "#d1d5db"),
    }
    label, color, bg, bdr = cfg.get(status, cfg["discarded"])
    return (
        f'<span style="display:inline-block;padding:4px 10px;border-radius:5px;'
        f'font-size:12px;font-weight:700;background:{bg};color:{color};'
        f'border:1px solid {bdr};">{label}</span>'
    )


def pill(text: str, bg="#eff6ff", bdr="#bfdbfe", color="#1d4ed8") -> str:
    return (
        f'<span style="display:inline-block;padding:6px 10px;border-radius:999px;'
        f'font-size:12px;font-weight:600;background:{bg};border:1px solid {bdr};'
        f'color:{color};margin:0 6px 6px 0;">{esc(text)}</span>'
    )


def log_event(msg: str):
    st.session_state.log.insert(0, msg)


def get_selected() -> Hypothesis:
    rca = st.session_state.rca
    for h in rca.hypotheses:
        if h.id == st.session_state.selected:
            return h
    return rca.hypotheses[0]


def set_status(hid: str, status: str):
    for h in st.session_state.rca.hypotheses:
        if h.id == hid:
            old = h.status
            h.status = status
            log_event(f"{hid}: {old} → {status}")
            break


def counts() -> Tuple[int, int, int]:
    rca = st.session_state.rca
    a = sum(1 for h in rca.hypotheses if h.status == "active")
    n = sum(1 for h in rca.hypotheses if h.status == "narrowed")
    d = sum(1 for h in rca.hypotheses if h.status == "discarded")
    return a, n, d


def closure_info() -> Tuple[str, str, str, str, str, int]:
    a, _, _ = counts()
    total = len(st.session_state.rca.hypotheses)
    pct = round((1 - a / total) * 100)
    if a >= 3:
        return "Open", "#16a34a", "#f0fdf4", "#86efac", "Multiple paths still visible.", pct
    elif a == 2:
        return "Narrowing", "#d97706", "#fefce8", "#fde68a", "Two paths remain. Closure pressure building.", pct
    elif a == 1:
        return "At Risk", "#dc2626", "#fef2f2", "#fca5a5", "Only one path left. Check before closing.", pct
    else:
        return "Collapsed", "#6b7280", "#f9fafb", "#d1d5db", "No active paths.", pct


# =========================================================
# CSS
# =========================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"], .stApp {
    background:#f4f5f7 !important;
    font-family:'Inter', sans-serif !important;
}
[data-testid="stHeader"], [data-testid="stDecoration"], [data-testid="stToolbar"], footer {
    display:none !important;
}
.block-container {
    max-width:1440px !important;
    padding:24px 28px 34px !important;
}
div[data-testid="stVerticalBlockBorderWrapper"],
div[data-testid="stVerticalBlockBorderWrapper"] > div {
    border:none !important;
    background:transparent !important;
    box-shadow:none !important;
    padding:0 !important;
    border-radius:0 !important;
    margin:0 !important;
}
div[data-testid="stButton"] > button {
    font-family:'Inter', sans-serif !important;
    font-size:14px !important;
    font-weight:600 !important;
    color:#374151 !important;
    background:#ffffff !important;
    border:1.5px solid #d1d5db !important;
    border-radius:9px !important;
    padding:10px 16px !important;
    min-height:2.7rem !important;
    box-shadow:0 1px 2px rgba(0,0,0,.05) !important;
    transition:all .12s ease !important;
    width:100% !important;
}
div[data-testid="stButton"] > button:hover {
    background:#f3f4f6 !important;
    border-color:#9ca3af !important;
    color:#111827 !important;
}
[data-testid="stRadio"] { padding:8px 0 4px !important; }
[data-testid="stRadio"] label {
    font-size:15px !important;
    font-weight:500 !important;
    color:#374151 !important;
    padding:5px 10px !important;
}
.stTextArea { padding:4px 0 !important; }
.stTextArea label {
    font-size:15px !important;
    font-weight:600 !important;
    color:#374151 !important;
}
textarea {
    font-family:'Inter',sans-serif !important;
    font-size:14px !important;
    color:#1f2937 !important;
    background:#f9fafb !important;
    border:1.5px solid #d1d5db !important;
    border-radius:9px !important;
    padding:14px 16px !important;
    min-height:120px !important;
    line-height:1.7 !important;
}
textarea:focus { border-color:#2563eb !important; outline:none !important; }
[data-testid="stExpander"] {
    border:1px solid #e5e7eb !important;
    border-radius:10px !important;
    background:#f9fafb !important;
}
[data-testid="stExpander"] summary {
    font-size:15px !important;
    font-weight:600 !important;
    color:#374151 !important;
}
p, li { font-size:15px !important; color:#4b5563 !important; line-height:1.7 !important; }
</style>
""", unsafe_allow_html=True)


# =========================================================
# Session state
# =========================================================
if "rca" not in st.session_state:
    st.session_state.rca = build_example_case()
if "step" not in st.session_state:
    st.session_state.step = 1
if "selected" not in st.session_state:
    st.session_state.selected = "H1"
if "plausibility" not in st.session_state:
    st.session_state.plausibility = {"H1": "Plausible", "H2": "Unclear", "H3": "Plausible"}
if "notes" not in st.session_state:
    st.session_state.notes = {"H1": "", "H2": "", "H3": ""}
if "log" not in st.session_state:
    st.session_state.log = ["Session initialized.", "Investigation workspace ready."]
if "toast_msg" not in st.session_state:
    st.session_state.toast_msg = None
if "ai_result_by_hypothesis" not in st.session_state:
    st.session_state.ai_result_by_hypothesis = {}
if "ai_running_for" not in st.session_state:
    st.session_state.ai_running_for = None

if st.session_state.toast_msg:
    st.toast(st.session_state.toast_msg)
    st.session_state.toast_msg = None

rca = st.session_state.rca
step = st.session_state.step
step_name, step_desc = STEPS[step]
sig_name, sig_color, sig_bg, sig_bdr, sig_msg, pressure_pct = closure_info()
active_c, narrowed_c, dropped_c = counts()
selected = get_selected()
selected_ai = st.session_state.ai_result_by_hypothesis.get(selected.id)


# =========================================================
# Header
# =========================================================
render(f"""
<div style="{CARD}margin-bottom:10px;">
  <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:14px;">
    <div>
      {overline("Case study / investigation support / regulated environments")}
      <div style="font-size:22px;font-weight:700;color:#111827;letter-spacing:-.02em;margin-bottom:4px;">
        RCA Reasoning Scaffolder
      </div>
      <div style="font-size:15px;color:#6b7280;">
        Step-by-step reasoning scaffold with an AI extension designed to expand reasoning space rather than produce a final answer.
      </div>
    </div>
    <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center;">
      <div style="text-align:center;">
        <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#9ca3af;">Active</div>
        <div style="font-size:18px;font-weight:700;color:#111827;">{active_c}</div>
      </div>
      <div style="text-align:center;">
        <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#9ca3af;">Narrowed</div>
        <div style="font-size:18px;font-weight:700;color:#111827;">{narrowed_c}</div>
      </div>
      <div style="text-align:center;">
        <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#9ca3af;">Dropped</div>
        <div style="font-size:18px;font-weight:700;color:#111827;">{dropped_c}</div>
      </div>
      <div style="padding:10px 14px;border-radius:10px;background:{sig_bg};border:1px solid {sig_bdr};min-width:170px;">
        <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:{sig_color};margin-bottom:3px;">Closure signal</div>
        <div style="font-size:15px;font-weight:700;color:{sig_color};">{sig_name}</div>
        <div style="font-size:12px;color:#6b7280;margin-top:2px;">{sig_msg}</div>
      </div>
    </div>
  </div>
</div>
""")

render(f"""
<div style="{CARD}padding:16px 18px;">
  <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;">
    <div>
      {overline(f"Step {step} of 5")}
      <div style="font-size:18px;font-weight:700;color:#111827;">{esc(step_name)}</div>
      <div style="font-size:14px;color:#6b7280;margin-top:4px;">{esc(step_desc)}</div>
    </div>
    <div style="padding:8px 12px;background:#faf5ff;border:1px solid #ddd6fe;border-radius:999px;font-size:12px;font-weight:700;color:#6d28d9;">
      AI Extension — Counter-PAC Design
    </div>
  </div>
</div>
""")


# =========================================================
# Main layout
# =========================================================
left, center, right = st.columns([1.02, 1.45, 0.95], gap="large")


# =========================================================
# LEFT — Hypothesis list
# =========================================================
with left:
    render(f"""
    <div style="{CARD}">
      {overline("Hypotheses")}
      {heading("Keep multiple paths visible", size="17px")}
    </div>
    """)

    for h in rca.hypotheses:
        bg = "#eff6ff" if h.id == selected.id else "#ffffff"
        border = "#93c5fd" if h.id == selected.id else "#e5e7eb"
        render(f"""
        <div style="background:{bg};border:1px solid {border};border-radius:10px;padding:14px 14px 12px;margin-bottom:10px;">
          <div style="display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:6px;">
            <div style="font-size:13px;font-weight:700;color:#9ca3af;">{h.id}</div>
            {badge(h.status)}
          </div>
          <div style="font-size:14px;font-weight:600;color:#111827;line-height:1.5;margin-bottom:10px;">
            {esc(h.description)}
          </div>
        </div>
        """)

        c1, c2, c3, c4 = st.columns([1, 1, 1, 1], gap="small")
        with c1:
            if st.button("View", key=f"view_{h.id}", use_container_width=True):
                st.session_state.selected = h.id
                st.session_state.toast_msg = f"Viewing {h.id}"
                st.rerun()
        with c2:
            if st.button("Active", key=f"ba_{h.id}", use_container_width=True):
                set_status(h.id, "active")
                st.session_state.selected = h.id
                st.session_state.toast_msg = f"{h.id} → Active"
                st.rerun()
        with c3:
            if st.button("Narrow", key=f"bn_{h.id}", use_container_width=True):
                set_status(h.id, "narrowed")
                st.session_state.selected = h.id
                st.session_state.toast_msg = f"{h.id} → Narrowed"
                st.rerun()
        with c4:
            if st.button("Drop", key=f"bd_{h.id}", use_container_width=True):
                set_status(h.id, "discarded")
                st.session_state.selected = h.id
                st.session_state.toast_msg = f"{h.id} → Dropped"
                st.rerun()

        render('<div style="height:6px;"></div>')


# =========================================================
# CENTER — Step content
# =========================================================
with center:
    if step == 1:
        render(f"""
        <div style="{CARD}">
          {overline("Deviation")}
          {heading(rca.title, size="19px")}
          {body(
              "Root cause analysis (RCA) is the process of finding <strong>why something failed</strong> "
              "— not just the most visible cause, but the real one.<br><br>"
              "Investigators often settle on the first plausible explanation, closing off other possibilities "
              "too early. This scaffold keeps multiple causal paths visible before you commit to a final answer."
          )}
        </div>
        """)

        render(f"""
        <div style="{CARD}">
          {overline("Case summary")}
          <div style="font-size:14px;color:#374151;line-height:1.75;">{esc(rca.summary)}</div>
        </div>
        """)

        steps_rows = ""
        for n, (title, desc) in STEPS.items():
            act = n == step
            bg2 = "#eff6ff" if act else "#f9fafb"
            bl = "3px solid #2563eb" if act else "3px solid #e5e7eb"
            tc = "#1e40af" if act else "#374151"
            dc = "#3b82f6" if act else "#6b7280"
            steps_rows += (
                f'<div style="border-left:{bl};padding:10px 14px;border-radius:0 8px 8px 0;'
                f'background:{bg2};margin-bottom:6px;">'
                f'<div style="font-size:13px;font-weight:700;color:{tc};">Step {n} — {title}</div>'
                f'<div style="font-size:13px;color:{dc};margin-top:3px;line-height:1.55;">{html.escape(desc)}</div>'
                f'</div>'
            )

        render(f"""
        <div style="{CARD}">
          {overline("Workflow")}
          {heading("Five-step reasoning scaffold", size="17px")}
          {steps_rows}
        </div>
        """)

    elif step == 2:
        rows = ""
        for h in rca.hypotheses:
            rows += (
                f'<div style="display:flex;align-items:start;justify-content:space-between;gap:12px;'
                f'padding:12px 14px;background:#f9fafb;border-radius:9px;margin-bottom:8px;">'
                f'<div><div style="font-size:13px;font-weight:700;color:#9ca3af;margin-bottom:3px;">{h.id}</div>'
                f'<div style="font-size:14px;color:#374151;line-height:1.6;">{html.escape(h.description)}</div></div>'
                f'{badge(h.status)}</div>'
            )

        render(f"""
        <div style="{CARD}">
          {overline("Open hypotheses")}
          {heading("List all possible explanations", size="19px")}
          {body("Do not narrow yet. At this stage, the goal is visibility rather than closure.")}
          <div style="margin-top:12px;">{rows}</div>
        </div>
        """)

    elif step == 3:
        factors_rows = "".join(pill(f) for f in selected.factors)
        evidence_rows = "".join(
            pill(e, bg="#f0fdf4", bdr="#86efac", color="#166534")
            for e in selected.evidence
        )

        render(f"""
        <div style="{CARD}">
          {overline("Selected hypothesis")}
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
            <span style="font-size:13px;font-weight:700;color:#9ca3af;">{selected.id}</span>
            {badge(selected.status)}
          </div>
          {heading(selected.description)}
          {body("Review the contributing factors and evidence below. Then rate plausibility and add your note.")}
          {slabel("Contributing factors")}
          <div>{factors_rows}</div>
          {slabel("Evidence")}
          <div>{evidence_rows}</div>
        </div>
        """)

        plaus_val = st.radio(
            "How plausible is this explanation?",
            ["Plausible", "Unclear", "Weak"],
            horizontal=True,
            index=["Plausible", "Unclear", "Weak"].index(
                st.session_state.plausibility.get(selected.id, "Unclear")
            ),
            key=f"plaus_{selected.id}",
        )
        st.session_state.plausibility[selected.id] = plaus_val

        note = st.text_area(
            "Your investigation note",
            value=st.session_state.notes.get(selected.id, ""),
            placeholder="Write down any ambiguity, missing information, or observations.",
            key=f"note_{selected.id}",
        )
        st.session_state.notes[selected.id] = note

        a1, a2 = st.columns([1, 1], gap="small")
        with a1:
            if st.button("💾 Save note", use_container_width=True, key="save_note"):
                log_event(f"Note saved for {selected.id}")
                st.session_state.toast_msg = f"Note saved for {selected.id}"
                st.rerun()

        with a2:
            if st.button(
                "✨ Run AI reopening support",
                use_container_width=True,
                key=f"run_ai_{selected.id}",
                disabled=(get_anthropic_key() is None),
            ):
                with st.spinner("Running AI extension..."):
                    try:
                        ai_result = run_claude_expansion(rca.summary, selected.description)
                        st.session_state.ai_result_by_hypothesis[selected.id] = ai_result
                        log_event(f"AI extension run for {selected.id}")
                        st.session_state.toast_msg = f"AI extension complete for {selected.id}"
                        st.rerun()
                    except Exception as e:
                        st.error(f"AI extension failed: {e}")

        render(f"""
        <div style="background:#faf5ff;border:1px solid #ddd6fe;border-radius:12px;padding:18px 20px;margin-top:10px;margin-bottom:12px;">
          {overline("AI extension for selected hypothesis")}
          <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px;flex-wrap:wrap;">
            <div style="max-width:680px;">
              {heading("Reasoning-space expansion", size="17px")}
              <div style="font-size:14px;color:#6d28d9;line-height:1.7;">
                The AI layer does not output a final answer. It surfaces alternative pathways, flags possible PAC pressure,
                and generates reopening questions for the currently selected hypothesis.
              </div>
            </div>
            <div style="padding:6px 10px;background:#ffffff;border:1px solid #c4b5fd;border-radius:999px;font-size:12px;font-weight:700;color:#6d28d9;">
              No final answer output
            </div>
          </div>
        </div>
        """)

        if selected_ai:
            pac = selected_ai.get("pac_warning", "")
            alt = selected_ai.get("alternative_pathways", [])
            rq = selected_ai.get("reopening_questions", [])

            if pac:
                render(f"""
                <div style="background:#fef2f2;border:1px solid #fca5a5;border-left:4px solid #dc2626;border-radius:12px;padding:16px 18px;margin-bottom:10px;">
                  {overline("AI extension")}
                  {heading("PAC warning signal", size="16px")}
                  <div style="font-size:14px;color:#374151;line-height:1.7;">{esc(pac)}</div>
                </div>
                """)

            render(f"""
            <div style="{CARD}">
              {overline("AI extension")}
              {heading("Alternative causal pathways", size="16px")}
            """)
            for i, p in enumerate(alt):
                colors = ["#7c3aed", "#0891b2", "#059669"]
                bgs = ["#f5f3ff", "#ecfeff", "#ecfdf5"]
                bdrs = ["#ddd6fe", "#a5f3fc", "#a7f3d0"]
                c = colors[i % 3]
                bg = bgs[i % 3]
                bdr = bdrs[i % 3]
                render(f"""
                <div style="background:{bg};border:1px solid {bdr};border-left:4px solid {c};border-radius:10px;padding:14px 16px;margin-bottom:8px;">
                  <div style="font-size:14px;font-weight:700;color:#111827;margin-bottom:6px;">{esc(p.get("title", ""))}</div>
                  <div style="font-size:14px;color:#374151;line-height:1.65;margin-bottom:8px;">{esc(p.get("desc", ""))}</div>
                  <div style="padding:10px 12px;background:rgba(255,255,255,.72);border:1px solid {bdr};border-radius:8px;font-size:13px;color:#374151;font-style:italic;">
                    {esc(p.get("question", ""))}
                  </div>
                </div>
                """)
            render("</div>")

            if rq:
                render(f"""
                <div style="{CARD}">
                  {overline("AI extension")}
                  {heading("Reopening questions", size="16px")}
                """)
                for q in rq:
                    render(f"""
                    <div style="display:flex;gap:10px;padding:9px 0;border-bottom:1px solid #f3f4f6;">
                      <span style="color:#d97706;font-weight:700;flex-shrink:0;">?</span>
                      <span style="font-size:14px;color:#374151;line-height:1.6;">{esc(q)}</span>
                    </div>
                    """)
                render("</div>")
        else:
            render(f"""
            <div style="{CARD}background:#fcfcff;border-color:#e9d5ff;">
              {overline("AI extension")}
              {heading("Ready for selected hypothesis", size="16px")}
              <div style="font-size:14px;color:#6b7280;line-height:1.7;">
                Run the AI extension to attach reopening questions and alternative pathways to {esc(selected.id)}.
              </div>
            </div>
            """)

    elif step == 4:
        status_rows = ""
        for h in rca.hypotheses:
            bg2 = "#eff6ff" if h.id == selected.id else "#f9fafb"
            status_rows += (
                f'<div style="display:flex;align-items:center;justify-content:space-between;'
                f'padding:12px 14px;background:{bg2};border-radius:8px;margin-bottom:6px;">'
                f'<div><span style="font-size:13px;font-weight:700;color:#9ca3af;margin-right:10px;">{h.id}</span>'
                f'<span style="font-size:14px;color:#374151;">{html.escape(h.description)}</span></div>'
                f'{badge(h.status)}</div>'
            )

        render(f"""
        <div style="{CARD}">
          {overline("Narrowing")}
          {heading("Review status across hypotheses", size="19px")}
          {body("Only narrow after reviewing each path. This stage makes closure pressure visible rather than invisible.")}
          <div style="margin-top:12px;">{status_rows}</div>
        </div>
        """)

        qlist = generate_questions()
        render(f"""
        <div style="background:#faf5ff;border:1px solid #ddd6fe;border-radius:12px;padding:18px 20px;margin-bottom:12px;">
          {overline("AI extension")}
          {heading("Reopening questions before further narrowing", size="16px")}
        """)
        for q in qlist:
            render(f"""
            <div style="display:flex;gap:10px;padding:9px 0;border-bottom:1px solid #ede9fe;">
              <span style="color:#7c3aed;font-weight:700;flex-shrink:0;">?</span>
              <span style="font-size:14px;color:#374151;line-height:1.6;">{esc(q)}</span>
            </div>
            """)
        render("</div>")

    elif step == 5:
        ev = generate_evidence(rca.summary, selected.description)
        render(f"""
        <div style="{CARD}">
          {overline("Pre-closure review")}
          {heading("What remained visible before closing?", size="19px")}
          {body("This final review surfaces what may have been compressed as the investigation moved toward a stable narrative.")}
        </div>
        """)

        render(f"""
        <div style="{CARD}">
          {overline("Selected hypothesis")}
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
            <span style="font-size:13px;font-weight:700;color:#9ca3af;">{selected.id}</span>
            {badge(selected.status)}
          </div>
          {heading(selected.description)}
          {slabel("Evidence to examine before closure")}
        """)
        for item in ev:
            render(f"""
            <div style="display:flex;gap:10px;padding:9px 0;border-bottom:1px solid #f3f4f6;">
              <span style="color:#2563eb;font-weight:700;flex-shrink:0;">→</span>
              <span style="font-size:14px;color:#374151;line-height:1.6;">{esc(item)}</span>
            </div>
            """)
        render("</div>")

        if selected_ai and selected_ai.get("next_evidence"):
            render(f"""
            <div style="background:#faf5ff;border:1px solid #ddd6fe;border-radius:12px;padding:18px 20px;margin-bottom:12px;">
              {overline("AI extension")}
              {heading("Evidence to examine before closure", size="16px")}
            """)
            for item in selected_ai["next_evidence"]:
                render(f"""
                <div style="display:flex;gap:10px;padding:9px 0;border-bottom:1px solid #ede9fe;">
                  <span style="color:#7c3aed;font-weight:700;flex-shrink:0;">→</span>
                  <span style="font-size:14px;color:#374151;line-height:1.6;">{esc(item)}</span>
                </div>
                """)
            render("</div>")

        render(f"""
        <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:18px 20px;margin-top:8px;">
          {overline("Note")}
          <div style="font-size:13px;color:#64748b;line-height:1.7;">
            AI is constrained to expand reasoning space rather than produce a single-cause explanation.
          </div>
        </div>
        """)


# =========================================================
# RIGHT — Inspector / AI summary / Log
# =========================================================
with right:
    render(f"""
    <div style="{CARD}">
      {overline("Inspector")}
      {heading("Current workspace state", size="17px")}
      <div style="padding:12px 14px;background:{sig_bg};border:1px solid {sig_bdr};border-radius:10px;margin-bottom:12px;">
        <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:{sig_color};margin-bottom:4px;">Closure signal</div>
        <div style="font-size:16px;font-weight:700;color:{sig_color};margin-bottom:4px;">{sig_name}</div>
        <div style="font-size:13px;color:#4b5563;line-height:1.6;">{sig_msg}</div>
        <div style="background:rgba(255,255,255,.55);border-radius:999px;height:10px;overflow:hidden;margin-top:12px;">
          <div style="height:100%;width:{pressure_pct}%;background:{sig_color};border-radius:999px;"></div>
        </div>
      </div>

      <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#9ca3af;margin-bottom:6px;">Currently viewing</div>
      <div style="font-size:13px;font-weight:700;color:#9ca3af;margin-bottom:4px;">{selected.id}</div>
      <div style="font-size:14px;color:#374151;line-height:1.65;margin-bottom:10px;">{esc(selected.description)}</div>
      {badge(selected.status)}
    </div>
    """)

    pac = detect_pac_risk(selected.description)
    matched_html = ""
    if pac["matched"]:
        tags = "".join(
            f'<span style="display:inline-block;padding:3px 8px;background:#fee2e2;color:#991b1b;border-radius:6px;'
            f'font-size:12px;font-weight:600;margin:2px 4px 0 0;">{esc(t)}</span>'
            for t in pac["matched"]
        )
        matched_html = f"""
        <div style="margin-top:10px;">
          <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:#9ca3af;margin-bottom:6px;">Flagged language</div>
          {tags}
        </div>
        """

    render(f"""
    <div style="background:{pac['bg']};border:1px solid {pac['border']};border-radius:12px;padding:18px 20px;margin-bottom:12px;">
      {overline("AI extension")}
      {heading("PAC warning signal", size="16px")}
      <div style="font-size:14px;font-weight:700;color:{pac['color']};margin-bottom:8px;">{esc(pac['label'])}</div>
      <div style="font-size:14px;color:#374151;line-height:1.7;">{esc(pac['message'])}</div>
      {matched_html}
    </div>
    """)

    render(f"""
    <div style="background:#faf5ff;border:1px solid #ddd6fe;border-radius:12px;padding:18px 20px;margin-bottom:12px;">
      {overline("AI extension")}
      {heading("Tool note", size="16px")}
      <div style="font-size:14px;color:#6d28d9;line-height:1.7;margin-bottom:10px;">
        This extension is built to widen the reasoning field, not narrow it.
      </div>
      <div style="padding:6px 10px;background:#ffffff;border:1px solid #c4b5fd;border-radius:999px;font-size:12px;font-weight:700;color:#6d28d9;display:inline-block;">
        No final answer output
      </div>
    </div>
    """)

    with st.expander("Event log", expanded=True):
        for item in st.session_state.log[:20]:
            st.write(f"• {item}")


# =========================================================
# Footer navigation
# =========================================================
nav1, nav2, nav3 = st.columns([1, 1, 1], gap="small")
with nav1:
    if st.button("← Back", use_container_width=True, disabled=(step == 1)):
        st.session_state.step -= 1
        st.rerun()
with nav2:
    if st.button("Reset demo", use_container_width=True):
        st.session_state.rca = build_example_case()
        st.session_state.step = 1
        st.session_state.selected = "H1"
        st.session_state.plausibility = {"H1": "Plausible", "H2": "Unclear", "H3": "Plausible"}
        st.session_state.notes = {"H1": "", "H2": "", "H3": ""}
        st.session_state.log = ["Session initialized.", "Investigation workspace ready."]
        st.session_state.ai_result_by_hypothesis = {}
        st.session_state.toast_msg = "Demo reset"
        st.rerun()
with nav3:
    if st.button("Next →", use_container_width=True, disabled=(step == 5)):
        st.session_state.step += 1
        st.rerun()
