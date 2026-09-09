CSS = """
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Big+Shoulders+Display:wght@600;700;800&family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>
:root {
  --ink: #15130F;
  --panel: #1E1B15;
  --panel-2: #29241C;
  --line: #3D362A;
  --text: #F3EFE4;
  --text-dim: #A99C87;
  --accent: #FF7A29;
  --accent-ink: #1A0E00;
  --good: #5FB98C;
  --warn: #E8B84B;
  --critical: #E3543F;
  --good-bg: rgba(95,185,140,0.14);
  --warn-bg: rgba(232,184,75,0.14);
  --critical-bg: rgba(227,84,63,0.16);
}

html, body, [class*="stApp"], [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stMain"] { background: var(--ink) !important; color: var(--text) !important; }

/* Any icon glyph (Streamlit's Material Symbols) must be excluded from the
   font override below, or the browser renders its ligature name as literal
   text (e.g. "keyboard_double_arrow_left") instead of the icon. Exclude by
   both testid and class name since Streamlit versions vary which they set. */
.stApp *:not([data-testid="stIconMaterial"]):not([class*="material-symbols"]):not([class*="material-icons"]) {
  font-family: 'IBM Plex Sans', system-ui, sans-serif !important;
}
[data-testid="stIconMaterial"], [class*="material-symbols"], [class*="material-icons"] {
  font-family: 'Material Symbols Outlined', 'Material Symbols Rounded', 'Material Icons' !important;
}

/* hide collapsed widget labels (e.g. the sidebar role radio's a11y-only label) */
[data-testid="stWidgetLabel"]:has(+ div [aria-hidden="true"]),
div[data-testid="stWidgetLabel"] > label > div[data-testid="stMarkdownContainer"]:empty {
  display: none !important;
}
section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] { display: none !important; }

h1, h2, h3 { font-family: 'Big Shoulders Display', 'Arial Narrow', sans-serif !important; text-transform: uppercase; letter-spacing: 0.02em; }

/* --- native widgets: st.metric --- */
[data-testid="stMetric"] { background: transparent !important; padding: 0 !important; }
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] p {
  font-family: 'IBM Plex Mono', monospace !important; font-size: 11px !important;
  letter-spacing: 0.14em !important; text-transform: uppercase !important; color: var(--text-dim) !important;
}
[data-testid="stMetricValue"], [data-testid="stMetricValue"] div {
  font-family: 'IBM Plex Mono', monospace !important; color: var(--text) !important; font-weight: 700 !important;
}
[data-testid="stMetricDelta"] { font-family: 'IBM Plex Mono', monospace !important; font-size: 11px !important; }
[data-testid="stMetricDeltaIcon-Up"], [data-testid="stMetricDeltaIcon-Down"] { display: none !important; }
[data-testid="stMetricDelta"] > div {
  background: var(--critical-bg) !important; color: var(--critical) !important;
  border-radius: 100px !important; padding: 2px 10px !important; display: inline-block !important;
}

/* --- native widgets: bordered containers act as panels --- */
[data-testid="stVerticalBlockBorderWrapper"] { border-color: var(--line) !important; border-radius: 10px !important; background: var(--panel) !important; }
[data-testid="stVerticalBlockBorderWrapper"] > div { background: transparent !important; }

/* --- native widgets: progress bars (mic battery) --- */
[data-testid="stProgress"] > div > div { background: var(--line) !important; }
[data-testid="stProgress"] > div > div > div { background: var(--accent) !important; }

/* --- native widgets: chat input --- */
[data-testid="stChatInput"] { background: var(--panel-2) !important; border-color: var(--line) !important; }
[data-testid="stChatInput"] textarea { color: var(--text) !important; font-family: 'IBM Plex Mono', monospace !important; }
[data-testid="stChatInputSubmitButton"] { background: var(--accent) !important; color: var(--accent-ink) !important; }

/* generic buttons outside the sidebar (e.g. any stray st.button in main content) */
.stMain button { font-family: 'IBM Plex Mono', monospace !important; font-weight: 700 !important; }

/* --- sidebar: role rail --- */
section[data-testid="stSidebar"] { background: #100E0A !important; border-right: 1px solid var(--line); }
section[data-testid="stSidebar"] *:not([data-testid="stIconMaterial"]):not([class*="material-symbols"]):not([class*="material-icons"]) {
  color: var(--text) !important; font-family: 'IBM Plex Sans', sans-serif !important;
}
section[data-testid="stSidebar"] h3 { font-family: 'Big Shoulders Display', sans-serif !important; }

.rail-mark { display: flex; align-items: center; gap: 8px; padding: 0 0 14px; margin-bottom: 10px; border-bottom: 1px solid var(--line); }
.rail-mark .dot { width: 9px; height: 9px; border-radius: 50%; background: var(--accent); flex: none; }
.rail-mark span { font-family:'IBM Plex Mono',monospace; font-size: 10px; letter-spacing: 0.08em; color: var(--text-dim); line-height: 1.3; }
.rail-group-lbl { font-family:'IBM Plex Mono',monospace; font-size: 9px; letter-spacing:0.1em; text-transform:uppercase; color: var(--text-dim); padding: 10px 2px 4px; opacity:0.7; }
.role-sub { font-family:'IBM Plex Mono',monospace; font-size: 9.5px; color: var(--text-dim); letter-spacing:0.03em; margin: -8px 0 8px 4px; }

/* role buttons: secondary = inactive card, primary = active card */
section[data-testid="stSidebar"] .stButton button {
  font-family: 'IBM Plex Sans', sans-serif !important; font-weight: 600 !important; font-size: 12.5px !important;
  text-align: left !important; justify-content: flex-start !important;
  border-radius: 8px !important; padding: 10px 10px !important; letter-spacing: normal !important;
}
section[data-testid="stSidebar"] .stButton button[kind="secondary"] {
  background: var(--panel-2) !important; border: 1px solid var(--line) !important; color: var(--text-dim) !important;
}
section[data-testid="stSidebar"] .stButton button[kind="secondary"]:hover {
  background: var(--panel) !important; border-color: var(--accent) !important; color: var(--text) !important;
}
section[data-testid="stSidebar"] .stButton button[kind="primary"] {
  background: var(--panel) !important; border: 1px solid var(--line) !important; color: var(--text) !important;
  border-left: 3px solid var(--accent) !important;
}

.eyebrow { font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 0.14em; text-transform: uppercase; color: var(--text-dim); }
.mono { font-family: 'IBM Plex Mono', monospace; font-variant-numeric: tabular-nums; }

.pill { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px 4px 8px; border-radius: 100px; font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 0.06em; text-transform: uppercase; font-weight: 600; white-space: nowrap; }
.pill::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: currentColor; }
.pill.critical { background: var(--critical-bg); color: var(--critical); }
.pill.warn { background: var(--warn-bg); color: var(--warn); }
.pill.good { background: var(--good-bg); color: var(--good); }

.kpi-strip { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 4px 0 20px; }
.kpi-tile { background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 14px 16px; }
.kpi-tile .big { font-family:'IBM Plex Mono',monospace; font-size: 26px; font-weight: 700; line-height:1; }
.kpi-tile .big.critical { color: var(--critical); }
.kpi-tile .big.good { color: var(--good); }
.kpi-tile .big.warn { color: var(--warn); }
.kpi-tile .sub { font-size: 12px; color: var(--text-dim); margin-top: 6px; }

.status-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
.status-tile { background: var(--panel-2); border: 1px solid var(--line); border-left: 3px solid var(--line); border-radius: 6px; padding: 9px 11px; }
.status-tile.critical { border-left-color: var(--critical); }
.status-tile.warn { border-left-color: var(--warn); }
.status-tile.good { border-left-color: var(--good); }
.status-tile .lbl { font-family:'IBM Plex Mono',monospace; font-size: 10px; color: var(--text-dim); }
.status-tile .v { font-family:'IBM Plex Mono',monospace; font-size: 16px; font-weight: 700; margin-top: 3px; }
.status-tile.critical .v { color: var(--critical); }
.status-tile.warn .v { color: var(--warn); }

.log-entry { display: grid; grid-template-columns: 4px 90px 1fr; gap: 10px; padding: 8px 4px; border-bottom: 1px solid var(--line); font-size: 13px; }
.log-entry:last-child { border-bottom: none; }
.log-stripe { border-radius: 2px; align-self: stretch; }
.log-stripe.critical { background: var(--critical); }
.log-stripe.warn { background: var(--warn); }
.log-stripe.info { background: var(--line); }
.log-time { font-family:'IBM Plex Mono',monospace; font-size: 11px; color: var(--text-dim); padding-top:1px; }
.log-job { font-family:'IBM Plex Mono',monospace; font-size: 10px; color: var(--text-dim); text-transform: uppercase; margin-right:6px; }
.log-text.critical { color: var(--critical); font-weight: 600; }
.log-text.warn { color: var(--warn); font-weight: 600; }

.prop-chip { display:inline-flex; align-items:center; gap:5px; background: var(--panel-2); border:1px solid var(--line); border-radius:100px; padding: 3px 10px; font-size:12.5px; margin: 0 6px 6px 0; }
.prop-chip.removed { text-decoration: line-through; color: var(--text-dim); background: var(--critical-bg); border-color: transparent; }
.prop-chip.removed::before { content: "✕ "; }

.callout { display: flex; gap: 10px; align-items: flex-start; padding: 12px 14px; border-radius: 8px; font-size: 13.5px; line-height: 1.5; margin-top: 10px; }
.callout.critical { background: var(--critical-bg); color: var(--critical); }
.callout.ok { background: var(--good-bg); color: var(--good); }

.trace-item { display: grid; grid-template-columns: 20px 1fr; gap: 8px; padding: 5px 10px; font-family: 'IBM Plex Mono', monospace; font-size: 11.5px; border-top: 1px solid var(--line); }
.trace-item .fn { color: var(--accent); }
.trace-item .args { color: var(--text-dim); }

div[data-testid="stChatMessage"] { background: var(--panel-2); border: 1px solid var(--line); border-radius: 8px; }
</style>
"""
