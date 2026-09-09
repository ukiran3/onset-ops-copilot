import streamlit as st

import components as c
import grafana_client as gc

SCENES = ["12A", "12B", "14", "15C"]
MICS = ["wireless-mic-1", "wireless-mic-2", "wireless-mic-3"]
RF_ZONES = ["stage-3", "stage-7", "backlot"]
GENERATORS = ["genny-1", "genny-2"]

# The synthetic generator produces one continuous live timeline, not 22
# distinct days of history -- so the day selector is real (it drives what's
# shown), but honest: only CURRENT_DAY has live data to show.
CURRENT_DAY = 4
TOTAL_DAYS = 22


def _instant(expr: str) -> dict:
    try:
        return gc.prom_instant(expr)
    except Exception:
        return {}


def _guard_current_day(desk_name: str) -> bool:
    """Returns True if the view should render normally. If a past/future
    day is selected, shows an honest empty state and returns False -- this
    demo's telemetry only exists for Day {CURRENT_DAY}."""
    day = st.session_state.get("shoot_day", CURRENT_DAY)
    if day == CURRENT_DAY:
        return True
    st.markdown(f"## {desk_name}")
    st.info(
        f"No telemetry recorded for Day {day}. This demo's live data covers "
        f"Day {CURRENT_DAY} only — pick that day to see {desk_name}."
    )
    return False


def view_ad():
    if not _guard_current_day("Mission Control"):
        return
    st.markdown("## Mission Control")
    st.caption("1st AD / UPM · live shoot-day ops")

    burn = _instant('schedule_burn_minutes{scene="12A"}')
    burn_val = next(iter(burn.values()), None)
    load = _instant('generator_load_pct{unit="genny-1"}')
    load_val = next(iter(load.values()), None)
    try:
        firing = gc.alerting_firing_count()
    except Exception:
        firing = 0

    c.kpi_strip(
        [
            {
                "label": "Schedule Burn · 12A",
                "value": f"{burn_val:+.1f} min" if burn_val is not None else "—",
                "tone": "critical" if burn_val and burn_val > 10 else "good",
                "sub": "live from Prometheus",
            },
            {
                "label": "Generator Load · genny-1",
                "value": f"{load_val:.0f}%" if load_val is not None else "—",
                "tone": "critical" if load_val and load_val > 85 else "good",
                "sub": "safe max 85%",
            },
            {
                "label": "Active Alerts",
                "value": str(firing),
                "tone": "critical" if firing else "good",
                "sub": "Grafana alerting",
            },
            {
                "label": "Status",
                "value": "⚠" if firing else "✓",
                "tone": "critical" if firing else "good",
                "sub": "see incident log",
            },
        ]
    )

    col1, col2 = st.columns([1.35, 1])
    with col1:
        with st.container(border=True):
            st.markdown("#### Live Telemetry")
            cc1, cc2 = st.columns(2)
            with cc1:
                c.prom_line_chart("Schedule Burn · 12A", 'schedule_burn_minutes{scene="12A"}', " min", threshold=10)
            with cc2:
                c.prom_line_chart("Generator Load · genny-1", 'generator_load_pct{unit="genny-1"}', "%", threshold=85)

            st.markdown("###### Equipment status")
            tiles = []
            for m in MICS:
                v = _instant(f'battery_pct{{device="{m}"}}')
                val = next(iter(v.values()), None)
                tiles.append({"label": m, "value": f"{val:.0f}%" if val is not None else "—", "tone": "critical" if val and val < 15 else ("warn" if val and val < 40 else "good")})
            for z in RF_ZONES:
                v = _instant(f'rf_channel_conflicts{{zone="{z}"}}')
                val = next(iter(v.values()), None)
                tiles.append({"label": f"rf {z}", "value": f"{val:.0f}" if val is not None else "—", "tone": "critical" if val else "good"})
            c.status_grid(tiles)

        with st.container(border=True):
            st.markdown("#### Incident Log")
            c.incident_log()

    with col2:
        with st.container(border=True):
            st.markdown("#### Copilot · ops_agent")
            c.chat_panel("ops", "why is scene 12A behind schedule?", "chat_ad")


def view_sound():
    if not _guard_current_day("Sound Desk"):
        return
    st.markdown("## Sound Desk")
    st.caption("Sound Mixer · ops_agent, audio lens")

    batteries = {m: next(iter(_instant(f'battery_pct{{device="{m}"}}').values()), None) for m in MICS}
    low = sum(1 for v in batteries.values() if v is not None and v < 40)
    rf = {z: next(iter(_instant(f'rf_channel_conflicts{{zone="{z}"}}').values()), None) for z in RF_ZONES}
    conflicts = sum(1 for v in rf.values() if v)

    c.kpi_strip(
        [
            {"label": "RF Conflicts", "value": str(conflicts), "tone": "critical" if conflicts else "good", "sub": "live"},
            {"label": "Mics Below 40%", "value": str(low), "tone": "warn" if low else "good", "sub": f"of {len(MICS)} tracked"},
            {"label": "Avg Battery", "value": f"{(sum(v for v in batteries.values() if v is not None)/max(1,len([v for v in batteries.values() if v is not None]))):.0f}%" if any(v is not None for v in batteries.values()) else "—", "sub": "wireless packs"},
            {"label": "Zones Monitored", "value": str(len(RF_ZONES)), "sub": "rf_channel_conflicts"},
        ]
    )

    col1, col2 = st.columns([1.35, 1])
    with col1:
        with st.container(border=True):
            st.markdown("#### Wireless Mic Battery")
            for m, v in batteries.items():
                tone = "critical" if v and v < 15 else ("warn" if v and v < 40 else "good")
                st.progress(min(1.0, (v or 0) / 100), text=f"{m} — {v:.0f}%" if v is not None else m)

        with st.container(border=True):
            st.markdown("#### RF Channel Map")
            c.status_grid([{"label": z, "value": f"{v:.0f}" if v is not None else "—", "tone": "critical" if v else "good"} for z, v in rf.items()])

    with col2:
        with st.container(border=True):
            st.markdown("#### Copilot · ops_agent")
            c.chat_panel("ops", "which mics need battery swaps?", "chat_sound")


def view_electric():
    if not _guard_current_day("Electric Desk"):
        return
    st.markdown("## Electric Desk")
    st.caption("Gaffer / Electric · ops_agent, power lens")

    loads = {g: next(iter(_instant(f'generator_load_pct{{unit="{g}"}}').values()), None) for g in GENERATORS}
    avg = sum(v for v in loads.values() if v is not None) / max(1, len([v for v in loads.values() if v is not None])) if any(v is not None for v in loads.values()) else None

    c.kpi_strip(
        [
            {"label": "Generators Active", "value": str(len(GENERATORS)), "sub": ", ".join(GENERATORS)},
            {"label": "Avg Load", "value": f"{avg:.0f}%" if avg is not None else "—", "tone": "critical" if avg and avg > 85 else "good", "sub": "safe max 85%"},
            {"label": "genny-1", "value": f"{loads.get('genny-1'):.0f}%" if loads.get("genny-1") is not None else "—", "tone": "critical" if loads.get("genny-1") and loads["genny-1"] > 85 else "good", "sub": "primary unit"},
            {"label": "genny-2", "value": f"{loads.get('genny-2'):.0f}%" if loads.get("genny-2") is not None else "—", "tone": "good", "sub": "backup unit"},
        ]
    )

    col1, col2 = st.columns([1.35, 1])
    with col1:
        with st.container(border=True):
            st.markdown("#### Generator Load")
            cc1, cc2 = st.columns(2)
            with cc1:
                c.prom_line_chart("genny-1", 'generator_load_pct{unit="genny-1"}', "%", threshold=85)
            with cc2:
                c.prom_line_chart("genny-2", 'generator_load_pct{unit="genny-2"}', "%", threshold=85)

        with st.container(border=True):
            st.markdown("#### Lighting Setups Today")
            st.caption("cross-referenced from continuity notes")
            for scene in SCENES:
                takes = c.fetch_continuity_takes(scene)
                if takes:
                    first = next(iter(takes.values()))
                    st.markdown(f"**{scene}** &nbsp; {first.get('lighting', '—')}")

        with st.container(border=True):
            st.markdown("#### Incident Log")
            c.incident_log(logql='{job=~"incidents|schedule"}')

    with col2:
        with st.container(border=True):
            st.markdown("#### Copilot · ops_agent")
            c.chat_panel("ops", "is genny-1 going to hold for the rest of the day?", "chat_electric")


def view_continuity():
    if not _guard_current_day("Continuity Desk"):
        return
    st.markdown("## Continuity Desk")
    st.caption("Script Supervisor · continuity_agent")

    scene = st.selectbox("Scene", SCENES, key="cont_scene")
    takes = c.fetch_continuity_takes(scene)

    flagged = sum(1 for t in takes.values() if "NOTE" in (t.get("comment") or "").upper())
    c.kpi_strip(
        [
            {"label": "Takes Logged", "value": str(len(takes)), "sub": f"scene {scene}"},
            {"label": "Mismatches Flagged", "value": str(flagged), "tone": "critical" if flagged else "good", "sub": "this scene"},
            {"label": "Scenes Available", "value": str(len(SCENES)), "sub": ", ".join(SCENES)},
            {"label": "Data Source", "value": "Loki", "sub": 'job="continuity"'},
        ]
    )

    col1, col2 = st.columns([1.35, 1])
    with col1:
        with st.container(border=True):
            st.markdown(f"#### Scene {scene} — Takes")
            if not takes:
                st.caption("No continuity notes logged for this scene yet.")
            else:
                take_num = st.radio("Take", list(takes.keys()), horizontal=True, key=f"take_{scene}")
                t = takes[take_num]
                flagged_take = "NOTE" in (t.get("comment") or "").upper()

                props = t.get("props", [])
                st.html(
                    " ".join(f'<span class="prop-chip">{p}</span>' for p in props) or "<i>none logged</i>"
                )
                st.markdown(f"**Wardrobe:** {t.get('wardrobe', '—')}")
                st.markdown(f"**Lighting:** {t.get('lighting', '—')}")
                tone = "critical" if flagged_take else "ok"
                icon = "⚠" if flagged_take else "✓"
                st.html(
                    f'<div class="callout {tone}"><span>{icon}</span>'
                    f'<span><b>Script supervisor\'s note:</b> {t.get("comment", "—")}</span></div>'
                )

    with col2:
        with st.container(border=True):
            st.markdown("#### Copilot · continuity_agent")
            c.chat_panel("continuity", f"check continuity for scene {scene}", "chat_continuity")
