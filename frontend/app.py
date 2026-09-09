import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))
import force_ipv4  # noqa: E402,F401  (must patch socket before any HTTP client is used)

import streamlit as st  # noqa: E402

st.set_page_config(page_title="Video Village", page_icon="🎬", layout="wide")

from style import CSS  # noqa: E402

st.html(CSS)

from streamlit_autorefresh import st_autorefresh  # noqa: E402

# Never auto-refresh while a chat request is pending -- an agent call can
# take well over 10s in this environment, and a refresh mid-request would
# cancel it. See components.chat_panel for the other half of this.
if st.session_state.get("chat_pending") is None:
    st_autorefresh(interval=10_000, key="telemetry_refresh")

import views  # noqa: E402

ROLES = [
    {"key": "ad", "badge": "AD", "label": "1st AD / UPM", "sub": "ops_agent", "group": "Ops", "view": views.view_ad},
    {"key": "snd", "badge": "SD", "label": "Sound Mixer", "sub": "ops_agent · audio", "group": "Ops", "view": views.view_sound},
    {"key": "ge", "badge": "GE", "label": "Gaffer / Electric", "sub": "ops_agent · power", "group": "Ops", "view": views.view_electric},
    {"key": "ss", "badge": "SS", "label": "Script Supervisor", "sub": "continuity_agent", "group": "Continuity", "view": views.view_continuity},
]

if "active_role" not in st.session_state:
    st.session_state.active_role = "ad"

with st.sidebar:
    st.html(
        '<div class="rail-mark"><span class="dot"></span>'
        '<span>VIDEO<br>VILLAGE</span></div>'
    )
    st.caption("UNTITLED / DAY 4 OF 22 · UNIT 1")

    last_group = None
    for role in ROLES:
        if role["group"] != last_group:
            st.html(f'<div class="rail-group-lbl">{role["group"]}</div>')
            last_group = role["group"]

        is_active = st.session_state.active_role == role["key"]
        if st.button(
            f'{role["badge"]}   {role["label"]}',
            key=f'rolebtn_{role["key"]}',
            type="primary" if is_active else "secondary",
            use_container_width=True,
        ):
            st.session_state.active_role = role["key"]
            st.rerun()
        st.html(f'<div class="role-sub">{role["sub"]}</div>')

active = next(r for r in ROLES if r["key"] == st.session_state.active_role)
active["view"]()
