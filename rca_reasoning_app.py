"""
RCA Reasoning Scaffolder
Cards = single complete st.markdown calls. No empty boxes. Buttons colored by state.
Run: streamlit run rca_app.py
Requires: rca_reasoning_core.py in same directory
"""

import streamlit as st
import pandas as pd
from rca_reasoning_core import build_example_case

st.set_page_config(
    page_title="RCA Reasoning Scaffolder",
    layout="wide",
    initial_sidebar_state="collapsed",
)

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

rca = st.session_state.rca

STEPS = {
    1: ("Intake",           "Read the deviation and understand what happened before forming any explanation."),
    2: ("Open Hypotheses",  "List all possible explanations. Do not narrow yet — keep everything visible."),
    3: ("Attach Reasoning", "For the focused hypothesis, add factors, evidence, and your notes."),
    4: ("Narrowing",        "Decide which paths to keep, narrow, or drop — after inspecting each one."),
    5: ("Pre-Closure",      "Review what remained visible and what was compressed before you close."),
}

# =========================================================
# Helpers
# =========================================================
def log_event(msg):
    st.session_state.log.insert(0, msg)

def get_selected():
    for h in rca.hypotheses:
        if h.id == st.session_state.selected:
            return h
    return rca.hypotheses[0]

def set_status(hid, status):
    for h in rca.hypotheses:
        if h.id == hid:
            old = h.status
            h.status = status
            log_event(f"{hid}: {old} → {status}")
            break

def counts():
    a = sum(1 for h in rca.hypotheses if h.status == "active")
    n = sum(1 for h in rca.hypotheses if h.status == "narrowed")
    d = sum(1 for h in rca.hypotheses if h.status == "discarded")
    return a, n, d

def closure_info():
    a, _, _ = counts()
    total = len(rca.hypotheses)
    pct = round((1 - a / total) * 100)
    if a >= 3:
        return "Open",      "#16a34a", "#f0fdf4", "#86efac", "Multiple paths still visible.", pct
    elif a == 2:
        return "Narrowing", "#d97706", "#fefce8", "#fde68a", "Two paths remain. Closure pressure building.", pct
    elif a == 1:
        return "At Risk",   "#dc2626", "#fef2f2", "#fca5a5", "Only one path left. Check before closing.", pct
    else:
        return "Collapsed", "#6b7280", "#f9fafb", "#d1d5db", "No active paths.", pct

# ── HTML primitives ───────────────────────────────────────
CARD = ('background:#ffffff;border:1px solid #e5e7eb;border-radius:12px;'
        'padding:22px 24px;margin-bottom:12px;box-shadow:0 1px 3px rgba(0,0,0,.05);')

def badge(status):
    cfg = {
        "active":    ("Active",   "#1a56db", "#e8f0fe", "#c3d8fd"),
        "narrowed":  ("Narrowed", "#92400e", "#fef3c7", "#fde68a"),
        "discarded": ("Dropped",  "#374151", "#f3f4f6", "#d1d5db"),
    }
    label, color, bg, bdr = cfg.get(status, cfg["discarded"])
    return (f'<span style="display:inline-block;padding:4px 10px;border-radius:5px;'
            f'font-size:12px;font-weight:700;background:{bg};color:{color};'
            f'border:1px solid {bdr};">{label}</span>')

def plaus_badge(p):
    cfg = {
        "Plausible": ("#166534", "#dcfce7", "#86efac"),
        "Unclear":   ("#92400e", "#fef3c7", "#fde68a"),
        "Weak":      ("#374151", "#f3f4f6", "#d1d5db"),
    }
    color, bg, bdr = cfg.get(p, cfg["Unclear"])
    return (f'<span style="display:inline-block;padding:4px 10px;border-radius:5px;'
            f'font-size:12px;font-weight:700;background:{bg};color:{color};'
            f'border:1px solid {bdr};">{p}</span>')

def overline(t):
    return (f'<div style="font-size:11px;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:.08em;color:#9ca3af;margin-bottom:8px;">{t}</div>')

def heading(t, size="17px", mb="10px"):
    return (f'<div style="font-size:{size};font-weight:700;color:#111827;'
            f'line-height:1.4;margin-bottom:{mb};">{t}</div>')

def body(t):
    return f'<div style="font-size:15px;color:#4b5563;line-height:1.7;">{t}</div>'

def slabel(t, mt="14px"):
    return (f'<div style="font-size:12px;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:.07em;color:#9ca3af;margin:{mt} 0 8px;">{t}</div>')

def pill(t, bg="#f9fafb", bdr="#e5e7eb", color="#374151"):
    return (f'<div style="padding:10px 14px;background:{bg};border:1px solid {bdr};'
            f'border-radius:8px;margin-bottom:6px;font-size:14px;color:{color};">{t}</div>')

def render(html):
    st.markdown(html, unsafe_allow_html=True)

# =========================================================
# Toast — render after rerun
# =========================================================
if st.session_state.toast_msg:
    st.toast(st.session_state.toast_msg)
    st.session_state.toast_msg = None

# =========================================================
# CSS
# =========================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"], .stApp {
    background: #eef0f4 !important;
    font-family: 'Inter', sans-serif !important;
}
[data-testid="stHeader"],[data-testid="stDecoration"],
[data-testid="stToolbar"],footer { display:none !important; }

.block-container {
    max-width:1480px !important;
    padding:20px 28px 32px !important;
}
[data-testid="stVerticalBlock"] > div:empty { display:none !important; }

/* Kill ALL Streamlit container chrome */
div[data-testid="stVerticalBlockBorderWrapper"],
div[data-testid="stVerticalBlockBorderWrapper"] > div {
    border:none !important;
    background:transparent !important;
    box-shadow:none !important;
    padding:0 !important;
    border-radius:0 !important;
    margin:0 !important;
}

/* Buttons - base */
div[data-testid="stButton"] > button {
    font-family:'Inter',sans-serif !important;
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

/* Radio */
[data-testid="stRadio"] { padding:8px 0 4px !important; }
[data-testid="stRadio"] label {
    font-size:15px !important;
    font-weight:500 !important;
    color:#374151 !important;
    padding:5px 10px !important;
}

/* Textarea */
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

[data-testid="stDataFrame"] { border-radius:9px !important; overflow:hidden; }
[data-testid="stExpander"] {
    border:1px solid #e5e7eb !important;
    border-radius:10px !important;
    background:#f9fafb !important;
}
[data-testid="stExpander"] summary {
    font-size:15px !important; font-weight:600 !important; color:#374151 !important;
}
p, li { font-size:15px !important; color:#4b5563 !important; line-height:1.7 !important; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# Derived state
# =========================================================
step = st.session_state.step
step_name, step_desc = STEPS[step]
sig_name, sig_color, sig_bg, sig_bdr, sig_msg, pressure_pct = closure_info()
active_c, narrowed_c, dropped_c = counts()
selected = get_selected()

# =========================================================
# Header — pure HTML, single render call
# =========================================================
render(f"""
<div style="{CARD}margin-bottom:10px;">
  <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:14px;">
    <div>
      {overline("GMP Investigation Tool · Prototype")}
      <div style="font-size:22px;font-weight:700;color:#111827;letter-spacing:-.02em;margin-bottom:4px;">
        RCA Reasoning Scaffolder
      </div>
      <div style="font-size:15px;color:#6b7280;">
        Keep multiple causal paths visible before committing to a final explanation.
      </div>
    </div>
    <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center;">
      <div style="text-align:center;padding:12px 22px;background:#f0fdf4;border:1px solid #86efac;border-radius:10px;">
        <div style="font-size:26px;font-weight:700;color:#16a34a;">{active_c}</div>
        <div style="font-size:12px;font-weight:600;color:#16a34a;">Active</div>
      </div>
      <div style="text-align:center;padding:12px 22px;background:#fefce8;border:1px solid #fde68a;border-radius:10px;">
        <div style="font-size:26px;font-weight:700;color:#d97706;">{narrowed_c}</div>
        <div style="font-size:12px;font-weight:600;color:#d97706;">Narrowed</div>
      </div>
      <div style="text-align:center;padding:12px 22px;background:#f9fafb;border:1px solid #d1d5db;border-radius:10px;">
        <div style="font-size:26px;font-weight:700;color:#6b7280;">{dropped_c}</div>
        <div style="font-size:12px;font-weight:600;color:#6b7280;">Dropped</div>
      </div>
      <div style="text-align:center;padding:12px 22px;background:{sig_bg};border:1px solid {sig_bdr};border-radius:10px;">
        <div style="font-size:26px;font-weight:700;color:{sig_color};">{sig_name}</div>
        <div style="font-size:12px;font-weight:600;color:{sig_color};">Signal</div>
      </div>
    </div>
  </div>
</div>
""")

# =========================================================
# Step nav — label above, buttons in columns
# =========================================================
render(f"""
<div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;
    color:#9ca3af;margin-bottom:8px;">Investigation Workflow</div>
""")

step_cols = st.columns(5)
for i, (n, (title, _)) in enumerate(STEPS.items()):
    with step_cols[i]:
        if step == n:
            render(f"""
            <div style="background:#eff6ff;border:2px solid #2563eb;border-radius:9px;
                padding:10px 14px;text-align:center;margin-bottom:2px;">
              <div style="font-size:12px;font-weight:700;color:#1d4ed8;">Step {n}</div>
              <div style="font-size:14px;font-weight:700;color:#1e40af;">{title}</div>
            </div>""")
        else:
            if st.button(f"Step {n}  {title}", key=f"step_{n}", use_container_width=True):
                st.session_state.step = n
                log_event(f"Moved to step {n}: {title}")
                st.rerun()

render(f"""
<div style="margin:10px 0 16px;padding:12px 16px;background:#eff6ff;
    border-radius:9px;border-left:4px solid #2563eb;">
  <span style="font-size:14px;font-weight:700;color:#1d4ed8;">Step {step} — {step_name}: </span>
  <span style="font-size:14px;color:#3b82f6;">{step_desc}</span>
</div>
""")

# =========================================================
# Main columns
# =========================================================
left, center, right = st.columns([1.1, 1.75, 1.1], gap="large")

# ─────────────────────────────────────────────────────────
# LEFT — Hypothesis list
# Each card = pure HTML. Buttons = separate widget rows below each card.
# ─────────────────────────────────────────────────────────
with left:
    render(f'<div style="font-size:13px;font-weight:700;text-transform:uppercase;'
           f'letter-spacing:.07em;color:#6b7280;margin-bottom:12px;">Hypotheses</div>')

    for h in rca.hypotheses:
        is_sel  = h.id == st.session_state.selected
        card_bg = "#eff6ff" if is_sel else "#ffffff"
        card_bd = "#2563eb" if is_sel else "#e5e7eb"
        card_bw = "2px"     if is_sel else "1px"

        # 카드 클릭 = Select. 버튼 3개 = 상태 변경
        render(f"""
        <div style="background:{card_bg};border:{card_bw} solid {card_bd};border-radius:12px;
            padding:20px 22px 16px;margin-bottom:4px;box-shadow:0 1px 4px rgba(0,0,0,.05);">
          <div style="display:flex;align-items:center;justify-content:space-between;
              margin-bottom:8px;">
            <span style="font-size:13px;font-weight:700;color:#9ca3af;
                letter-spacing:.05em;">{h.id}</span>
            {badge(h.status)}
          </div>
          <div style="font-size:15px;font-weight:600;color:#111827;
              line-height:1.5;margin-bottom:10px;">{h.description}</div>
          <div style="font-size:14px;color:#6b7280;padding:8px 12px;
              background:rgba(0,0,0,.03);border-radius:7px;">
            Plausibility: <strong style="color:#374151;">
              {st.session_state.plausibility.get(h.id, "Unclear")}
            </strong>
          </div>
        </div>
        """)

        # 선택 버튼 — primary=파란색, secondary=기본
        if st.button(
            f"{'✓ Viewing ' if is_sel else 'Select '}{h.id}",
            key=f"sel_{h.id}",
            use_container_width=True,
            type="primary" if is_sel else "secondary"
        ):
            st.session_state.selected = h.id
            log_event(f"Selected {h.id}")
            st.session_state.toast_msg = f"🔍 Now viewing {h.id}"
            st.rerun()

        # 상태 변경 버튼 3개 — 현재 status인 것만 primary
        b1, b2, b3 = st.columns(3)
        with b1:
            if st.button(
                "✅ Active" if h.status == "active" else "Active",
                key=f"ba_{h.id}",
                use_container_width=True,
                type="primary" if h.status == "active" else "secondary"
            ):
                set_status(h.id, "active")
                st.session_state.selected = h.id
                st.session_state.toast_msg = f"✅ {h.id} → Active"
                st.rerun()
        with b2:
            if st.button(
                "⚠️ Narrowed" if h.status == "narrowed" else "Narrow",
                key=f"bn_{h.id}",
                use_container_width=True,
                type="primary" if h.status == "narrowed" else "secondary"
            ):
                set_status(h.id, "narrowed")
                st.session_state.selected = h.id
                st.session_state.toast_msg = f"⚠️ {h.id} → Narrowed"
                st.rerun()
        with b3:
            if st.button(
                "❌ Dropped" if h.status == "discarded" else "Drop",
                key=f"bd_{h.id}",
                use_container_width=True,
                type="primary" if h.status == "discarded" else "secondary"
            ):
                set_status(h.id, "discarded")
                st.session_state.selected = h.id
                st.session_state.toast_msg = f"❌ {h.id} → Dropped"
                st.rerun()

        render('<div style="height:8px;"></div>')

# ─────────────────────────────────────────────────────────
# CENTER — Step content
# Pure HTML for display, widgets after
# ─────────────────────────────────────────────────────────
with center:

    # ── Step 1: Intake ──
    if step == 1:
        render(f"""
        <div style="{CARD}">
          {overline("Deviation")}
          {heading("Deviation in GMP environmental monitoring record review", size="19px")}
          {body("Root cause analysis (RCA) is the process of finding <strong>why something "
                "failed on the manufacturing floor</strong> — not just the most visible cause, "
                "but the real one.<br><br>Investigators often settle on the first plausible "
                "explanation, closing off other possibilities too early. This scaffold keeps "
                "multiple causal paths visible before you commit to a final answer.")}
        </div>
        """)

        steps_rows = ""
        for n, (title, desc) in STEPS.items():
            act  = n == step
            bg2  = "#eff6ff" if act else "#f9fafb"
            bl   = "3px solid #2563eb" if act else "3px solid #e5e7eb"
            tc   = "#1e40af" if act else "#374151"
            dc   = "#3b82f6" if act else "#6b7280"
            steps_rows += (f'<div style="border-left:{bl};padding:10px 14px;'
                           f'border-radius:0 8px 8px 0;background:{bg2};margin-bottom:6px;">'
                           f'<div style="font-size:13px;font-weight:700;color:{tc};">'
                           f'Step {n} — {title}</div>'
                           f'<div style="font-size:13px;color:{dc};margin-top:3px;">{desc}</div>'
                           f'</div>')

        render(f"""
        <div style="{CARD}">
          {overline("What to do in each step")}
          {steps_rows}
        </div>
        """)

    # ── Step 2: Open Hypotheses ──
    elif step == 2:
        render(f"""
        <div style="{CARD}">
          {overline("Instructions")}
          {heading("Review all possible explanations — do not narrow yet")}
          {body("At this stage, every hypothesis should remain visible. "
                "Inspect each one before deciding to narrow or drop it.")}
        </div>
        """)

        for h in rca.hypotheses:
            render(f"""
            <div style="{CARD}margin-bottom:8px;">
              <div style="display:flex;align-items:center;justify-content:space-between;
                  margin-bottom:8px;">
                <span style="font-size:13px;font-weight:700;color:#9ca3af;">{h.id}</span>
                {badge(h.status)}
              </div>
              <div style="font-size:16px;font-weight:600;color:#111827;
                  line-height:1.45;margin-bottom:8px;">{h.description}</div>
              <div style="font-size:14px;color:#6b7280;">
                Inspect this path and confirm it's visible before moving to narrowing.
              </div>
            </div>
            """)

            is_focused = h.id == st.session_state.selected
            is_active  = h.status == "active"
            c1, c2 = st.columns(2)
            with c1:
                if st.button(f"Inspect {h.id}", key=f"insp_{h.id}", use_container_width=True):
                    st.session_state.selected = h.id
                    log_event(f"Inspecting {h.id}")
                    st.session_state.toast_msg = f"🔍 Inspecting {h.id} — check the right panel"
                    st.rerun()
                if is_focused:
                    render(f'<style>div[data-testid="stButton"]:has(button[key="insp_{h.id}"]) button'
                           f'{{background:#eff6ff !important;border-color:#2563eb !important;'
                           f'color:#1d4ed8 !important;}}</style>')
            with c2:
                if st.button("Mark Visible", key=f"vis_{h.id}", use_container_width=True):
                    set_status(h.id, "active")
                    st.session_state.selected = h.id
                    st.session_state.toast_msg = f"👁 {h.id} marked as visible"
                    st.rerun()
                if is_active:
                    render(f'<style>div[data-testid="stButton"]:has(button[key="vis_{h.id}"]) button'
                           f'{{background:#f0fdf4 !important;border-color:#16a34a !important;'
                           f'color:#16a34a !important;}}</style>')

            render('<div style="height:4px;"></div>')

    # ── Step 3: Attach Reasoning ──
    elif step == 3:
        factors_rows = "".join(
            pill(f, bg="#f9fafb", bdr="#e5e7eb", color="#374151")
            for f in selected.factors
        )
        evidence_rows = "".join(
            pill(e, bg="#f0fdf4", bdr="#86efac", color="#166534")
            for e in selected.evidence
        )

        render(f"""
        <div style="{CARD}">
          {overline("Attach Reasoning")}
          <div style="display:flex;align-items:center;justify-content:space-between;
              margin-bottom:8px;">
            <span style="font-size:13px;font-weight:700;color:#9ca3af;">{selected.id}</span>
            {badge(selected.status)}
          </div>
          {heading(selected.description)}
          {body("Inspect contributing factors, evidence, and ambiguity before narrowing this path.")}
          {slabel("Contributing Factors")}
          {factors_rows}
          {slabel("Evidence")}
          {evidence_rows}
        </div>
        """)

        # Widgets outside HTML card
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
            placeholder="Write down any ambiguity, missing information, or observations...",
            key=f"note_{selected.id}",
        )
        st.session_state.notes[selected.id] = note

        if st.button("💾  Save Note", use_container_width=True, key="save_note"):
            log_event(f"Note saved for {selected.id}")
            st.session_state.toast_msg = f"💾 Note saved for {selected.id}"
            st.rerun()

    # ── Step 4: Narrowing ──
    elif step == 4:
        status_rows = ""
        for h in rca.hypotheses:
            bg2 = "#eff6ff" if h.id == selected.id else "#f9fafb"
            status_rows += (
                f'<div style="display:flex;align-items:center;justify-content:space-between;'
                f'padding:12px 14px;background:{bg2};border-radius:8px;margin-bottom:6px;">'
                f'<div><span style="font-size:13px;font-weight:700;color:#9ca3af;'
                f'margin-right:10px;">{h.id}</span>'
                f'<span style="font-size:14px;color:#374151;">{h.description}</span></div>'
                f'{badge(h.status)}</div>'
            )

        render(f"""
        <div style="{CARD}">
          {overline("Narrowing Controls")}
          <div style="display:flex;align-items:center;justify-content:space-between;
              margin-bottom:8px;">
            <span style="font-size:13px;font-weight:700;color:#9ca3af;">{selected.id}</span>
            {badge(selected.status)}
          </div>
          {heading(selected.description)}
          {body("Only narrow after inspecting. Each path you drop makes the investigation "
                "look neater — but that is not the same as making it stronger.")}
        </div>
        """)

        # Status buttons — type=primary highlights current state
        n1, n2, n3 = st.columns(3)
        with n1:
            if st.button(
                "✅ Active" if selected.status == "active" else "Set Active",
                use_container_width=True, key="s_active",
                type="primary" if selected.status == "active" else "secondary"
            ):
                set_status(selected.id, "active")
                st.session_state.toast_msg = f"✅ {selected.id} → Active"
                st.rerun()
        with n2:
            if st.button(
                "⚠️ Narrowed" if selected.status == "narrowed" else "Set Narrowed",
                use_container_width=True, key="s_narrowed",
                type="primary" if selected.status == "narrowed" else "secondary"
            ):
                set_status(selected.id, "narrowed")
                st.session_state.toast_msg = f"⚠️ {selected.id} → Narrowed"
                st.rerun()
        with n3:
            if st.button(
                "❌ Dropped" if selected.status == "discarded" else "Set Dropped",
                use_container_width=True, key="s_dropped",
                type="primary" if selected.status == "discarded" else "secondary"
            ):
                set_status(selected.id, "discarded")
                st.session_state.toast_msg = f"❌ {selected.id} → Dropped"
                st.rerun()

        render('<div style="height:8px;"></div>')

        render(f"""
        <div style="{CARD}">
          {overline("Current Status of All Hypotheses")}
          {status_rows}
        </div>
        """)

    # ── Step 5: Pre-Closure ──
    elif step == 5:
        active_hs   = [h for h in rca.hypotheses if h.status == "active"]
        narrowed_hs = [h for h in rca.hypotheses if h.status == "narrowed"]
        dropped_hs  = [h for h in rca.hypotheses if h.status == "discarded"]

        render(f"""
        <div style="background:{sig_bg};border:1px solid {sig_bdr};border-radius:12px;
            padding:22px 24px;margin-bottom:12px;">
          {overline("Closure Signal")}
          <div style="font-size:26px;font-weight:800;color:{sig_color};margin-bottom:6px;">{sig_name}</div>
          {body(sig_msg)}
        </div>
        """)

        ca, cn, cd = st.columns(3)
        for col, label, items, color, bg2, bdr in [
            (ca, "Still Active",  active_hs,   "#16a34a", "#f0fdf4", "#86efac"),
            (cn, "Narrowed",      narrowed_hs, "#d97706", "#fefce8", "#fde68a"),
            (cd, "Dropped",       dropped_hs,  "#6b7280", "#f9fafb", "#d1d5db"),
        ]:
            with col:
                items_html = "".join(
                    f'<div style="font-size:14px;color:#374151;padding:6px 0;'
                    f'border-bottom:1px solid #f3f4f6;">'
                    f'<strong>{h.id}</strong> — {h.description}</div>'
                    for h in items
                ) or '<div style="font-size:14px;color:#9ca3af;">None</div>'
                render(f"""
                <div style="background:{bg2};border:1px solid {bdr};border-radius:12px;
                    padding:18px 20px 14px;margin-bottom:8px;">
                  <div style="font-size:13px;font-weight:700;text-transform:uppercase;
                      letter-spacing:.06em;color:{color};margin-bottom:10px;">{label}</div>
                  {items_html}
                </div>""")

        prompts = "".join(
            f'<div style="display:flex;gap:12px;padding:12px 14px;background:#fffbeb;'
            f'border:1px solid #fde68a;border-radius:8px;margin-bottom:8px;">'
            f'<span style="color:#d97706;font-weight:700;font-size:16px;flex-shrink:0;">?</span>'
            f'<span style="font-size:14px;color:#374151;line-height:1.6;">{q}</span></div>'
            for q in [
                "Did the investigation become cleaner by becoming narrower?",
                "Which explanations lost visibility before closure?",
                "Is the final reasoning state genuinely stronger, or just neater?",
            ]
        )
        render(f"""
        <div style="{CARD}">
          {overline("Before You Close")}
          {prompts}
        </div>
        """)

        with st.expander("Full investigation summary"):
            rows = []
            for h in rca.hypotheses:
                rows.append({
                    "ID": h.id, "Description": h.description, "Status": h.status,
                    "Plausibility": st.session_state.plausibility.get(h.id, ""),
                    "Note": st.session_state.notes.get(h.id, ""),
                    "Factors": " | ".join(h.factors),
                    "Evidence": " | ".join(h.evidence),
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────────────────
# RIGHT — Inspector (pure HTML)
# ─────────────────────────────────────────────────────────
with right:
    render(f"""
    <div style="{CARD}">
      {overline("Closure Signal")}
      <div style="font-size:28px;font-weight:800;color:{sig_color};margin-bottom:6px;">{sig_name}</div>
      <div style="font-size:14px;color:#4b5563;margin-bottom:16px;line-height:1.6;">{sig_msg}</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
        <div style="text-align:center;padding:10px 8px;background:#f0fdf4;
            border:1px solid #86efac;border-radius:9px;">
          <div style="font-size:22px;font-weight:700;color:#16a34a;">{active_c}</div>
          <div style="font-size:12px;font-weight:600;color:#16a34a;">Active</div>
        </div>
        <div style="text-align:center;padding:10px 8px;background:#fefce8;
            border:1px solid #fde68a;border-radius:9px;">
          <div style="font-size:22px;font-weight:700;color:#d97706;">{narrowed_c}</div>
          <div style="font-size:12px;font-weight:600;color:#d97706;">Narrowed</div>
        </div>
        <div style="text-align:center;padding:10px 8px;background:#f9fafb;
            border:1px solid #d1d5db;border-radius:9px;">
          <div style="font-size:22px;font-weight:700;color:#6b7280;">{dropped_c}</div>
          <div style="font-size:12px;font-weight:600;color:#6b7280;">Dropped</div>
        </div>
        <div style="text-align:center;padding:10px 8px;background:{sig_bg};
            border:1px solid {sig_bdr};border-radius:9px;">
          <div style="font-size:22px;font-weight:700;color:{sig_color};">{pressure_pct}%</div>
          <div style="font-size:12px;font-weight:600;color:{sig_color};">Pressure</div>
        </div>
      </div>
    </div>
    """)

    render(f"""
    <div style="{CARD}">
      {overline("Focused Hypothesis")}
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
        <span style="font-size:13px;font-weight:700;color:#9ca3af;">{selected.id}</span>
        {badge(selected.status)}
      </div>
      <div style="font-size:15px;font-weight:600;color:#111827;line-height:1.45;margin-bottom:14px;">
        {selected.description}
      </div>
      {slabel("Plausibility", mt="0")}
      <div style="margin-bottom:12px;">
        {plaus_badge(st.session_state.plausibility.get(selected.id, "Unclear"))}
      </div>
      {slabel("Note", mt="0")}
      <div style="font-size:14px;color:#4b5563;line-height:1.6;font-style:italic;">
        {st.session_state.notes.get(selected.id, "") or "No note yet."}
      </div>
    </div>
    """)

    render(f"""
    <div style="{CARD}">
      {overline("About")}
      <div style="font-size:14px;color:#6b7280;line-height:1.65;">
        This tool does not find the correct root cause for you.
        It makes <strong>reasoning compression visible</strong> before
        the investigation locks in.
      </div>
    </div>
    """)

# =========================================================
# Bottom — log + nav
# =========================================================
render('<div style="height:10px;"></div>')
bot_l, bot_r = st.columns([2.5, 1], gap="large")

with bot_l:
    log_rows = "".join(
        f'<div style="display:flex;gap:10px;padding:7px 0;border-bottom:1px solid #f3f4f6;">'
        f'<span style="color:#9ca3af;flex-shrink:0;">›</span>'
        f'<span style="font-size:14px;color:#4b5563;">{line}</span></div>'
        for line in st.session_state.log[:6]
    )
    render(f"""
    <div style="{CARD}margin-bottom:0;">
      {overline("Event Log")}
      {log_rows}
    </div>
    """)

with bot_r:
    render(f'<div style="font-size:11px;font-weight:700;text-transform:uppercase;'
           f'letter-spacing:.08em;color:#9ca3af;margin-bottom:8px;">Navigation</div>')
    nav1, nav2 = st.columns(2)
    with nav1:
        if st.button("← Back", use_container_width=True, key="nav_back"):
            if st.session_state.step > 1:
                st.session_state.step -= 1
                log_event(f"Step {st.session_state.step}: {STEPS[st.session_state.step][0]}")
                st.session_state.toast_msg = f"← Step {st.session_state.step}: {STEPS[st.session_state.step][0]}"
            st.rerun()
    with nav2:
        if st.button("Next →", use_container_width=True, key="nav_next"):
            if st.session_state.step < 5:
                st.session_state.step += 1
                log_event(f"Step {st.session_state.step}: {STEPS[st.session_state.step][0]}")
                st.session_state.toast_msg = f"→ Step {st.session_state.step}: {STEPS[st.session_state.step][0]}"
            st.rerun()