import json
from datetime import datetime, timezone

import plotly.graph_objects as go
import streamlit as st

import grafana_client as gc

COLORS = {
    "accent": "#FF7A29",
    "good": "#5FB98C",
    "warn": "#E8B84B",
    "critical": "#E3543F",
    "text_dim": "#A99C87",
    "line": "#3D362A",
    "panel_2": "#29241C",
}


def kpi_strip(tiles: list[dict]) -> None:
    """tiles: [{"label": str, "value": str, "tone": "critical"|"good"|"warn"|None, "sub": str}]"""
    html = ['<div class="kpi-strip">']
    for t in tiles:
        tone_cls = f" {t['tone']}" if t.get("tone") else ""
        html.append(
            f'<div class="kpi-tile"><span class="eyebrow">{t["label"]}</span>'
            f'<div class="big{tone_cls}">{t["value"]}</div>'
            f'<div class="sub">{t.get("sub", "")}</div></div>'
        )
    html.append("</div>")
    st.html("".join(html))


def status_grid(tiles: list[dict]) -> None:
    """tiles: [{"label": str, "value": str, "tone": "critical"|"good"|"warn"}]"""
    html = ['<div class="status-grid">']
    for t in tiles:
        html.append(
            f'<div class="status-tile {t.get("tone", "good")}">'
            f'<div class="lbl">{t["label"]}</div><div class="v">{t["value"]}</div></div>'
        )
    html.append("</div>")
    st.html("".join(html))


def prom_line_chart(title: str, expr: str, unit_suffix: str = "", threshold: float | None = None, lookback_s: int = 5400):
    try:
        series = gc.prom_range(expr, lookback_s=lookback_s)
    except Exception as e:
        st.warning(f"Couldn't load {title}: {e}")
        return

    fig = go.Figure()
    latest_val = None
    for labels, points in series.items():
        name = ", ".join(f"{k}={v}" for k, v in labels) or title
        xs = [datetime.fromtimestamp(ts, tz=timezone.utc) for ts, _ in points]
        ys = [v for _, v in points]
        if ys:
            latest_val = ys[-1]
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                name=name,
                line=dict(color=COLORS["accent"], width=2),
                hovertemplate="%{y:.1f}<extra>%{fullData.name}</extra>",
            )
        )

    if threshold is not None:
        fig.add_hline(
            y=threshold,
            line_dash="dash",
            line_color=COLORS["critical"],
            opacity=0.7,
            annotation_text=f"{threshold}{unit_suffix} threshold",
            annotation_font_color=COLORS["critical"],
            annotation_font_size=10,
        )

    fig.update_layout(
        height=180,
        margin=dict(l=8, r=8, t=8, b=8),
        paper_bgcolor=COLORS["panel_2"],
        plot_bgcolor=COLORS["panel_2"],
        font=dict(color=COLORS["text_dim"], family="IBM Plex Mono", size=10),
        xaxis=dict(gridcolor=COLORS["line"], showgrid=False),
        yaxis=dict(gridcolor=COLORS["line"]),
        showlegend=len(series) > 1,
        legend=dict(font=dict(size=9)),
    )

    tone = "critical" if (threshold is not None and latest_val is not None and latest_val > threshold) else "good"
    val_str = f"{latest_val:.1f}{unit_suffix}" if latest_val is not None else "—"
    st.metric(label=title, value=val_str, delta="over threshold" if tone == "critical" else None, delta_color="inverse")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _format_log_line(entry: dict) -> tuple[str, str, str]:
    job = entry["labels"].get("job", "?")
    try:
        d = json.loads(entry["line"])
    except (json.JSONDecodeError, TypeError):
        return "info", job, entry["line"]

    if job == "incidents":
        sev = d.get("severity", "info")
        tone = "critical" if sev == "critical" else ("warn" if sev == "warning" else "info")
        return tone, job, d.get("message", str(d))
    if job == "schedule":
        if d.get("event") == "schedule_slip":
            return "critical", job, f"schedule_slip → {d.get('scene')} · reason: {d.get('reason')}"
        if d.get("event") == "scene_change":
            return "info", job, f"scene_change → {d.get('scene')}"
    return "info", job, entry["line"]


def incident_log(logql: str = '{job=~"incidents|schedule"}', limit: int = 12) -> None:
    try:
        lines = gc.loki_range(logql, limit=limit)
    except Exception as e:
        st.warning(f"Couldn't load incident log: {e}")
        return

    if not lines:
        st.caption("No log lines in range yet.")
        return

    html = []
    for entry in lines[:limit]:
        tone, job, text = _format_log_line(entry)
        ts = datetime.fromtimestamp(entry["ts_ns"] / 1e9, tz=timezone.utc).strftime("%H:%M:%S")
        text_cls = f" {tone}" if tone in ("critical", "warn") else ""
        html.append(
            f'<div class="log-entry"><div class="log-stripe {tone}"></div>'
            f'<div class="log-time">{ts}</div>'
            f'<div><span class="log-job">{job}</span><span class="log-text{text_cls}">{text}</span></div></div>'
        )
    st.html("".join(html))


def fetch_continuity_takes(scene: str) -> dict[int, dict]:
    """Returns {take_number: {props, wardrobe, lighting, comment}}, one entry
    per take (earliest logged instance -- the generator loops through takes
    1-6 repeatedly over a long-running session, we only want each once)."""
    try:
        lines = gc.loki_range(f'{{job="continuity", scene="{scene}"}}', limit=500)
    except Exception:
        return {}

    takes = {}
    for entry in lines:  # newest-first; overwrite so the OLDEST wins per take
        try:
            d = json.loads(entry["line"])
        except (json.JSONDecodeError, TypeError):
            continue
        take = d.get("take")
        if take is not None:
            takes[int(take)] = d
    return dict(sorted(takes.items()))


def chat_panel(agent_key: str, placeholder: str, history_key: str) -> None:
    """A blocking agent call can take well over a minute in this environment
    (cold MCP/Docker start + Gemini latency). The 10s telemetry auto-refresh
    (see app.py) would otherwise interrupt and cancel it mid-flight -- so we
    never let the run that submits a new question also make the blocking
    call. Submitting just records a "pending" question and reruns; the
    *next* run (which app.py detects and skips auto-refresh for) is the one
    that actually calls the agent."""
    import agent_bridge

    if history_key not in st.session_state:
        st.session_state[history_key] = []

    for turn in st.session_state[history_key]:
        with st.chat_message("user" if turn["role"] == "user" else "assistant"):
            if turn["role"] == "user":
                st.markdown(turn["text"])
            else:
                if turn.get("tool_calls"):
                    with st.expander(f"{len(turn['tool_calls'])} tool calls", expanded=False):
                        for tc in turn["tool_calls"]:
                            st.html(
                                f'<div class="trace-item"><span></span>'
                                f'<span><span class="fn">{tc["name"]}</span> '
                                f'<span class="args">{tc["args"]}</span></span></div>'
                            )
                st.markdown(turn["text"])

    pending = st.session_state.get("chat_pending")
    if pending and pending["history_key"] == history_key:
        with st.chat_message("user"):
            st.markdown(pending["question"])
        with st.chat_message("assistant"):
            with st.spinner("investigating… (can take up to a minute)"):
                events = agent_bridge.ask(agent_key, pending["question"])

        tool_calls = [e for e in events if e["kind"] == "tool_call"]
        final_texts = [e["text"] for e in events if e["kind"] == "text"]
        answer = final_texts[-1] if final_texts else "(no response)"
        st.session_state[history_key].append({"role": "user", "text": pending["question"]})
        st.session_state[history_key].append(
            {"role": "assistant", "text": answer, "tool_calls": tool_calls}
        )
        st.session_state.chat_pending = None

        import chat_log

        chat_log.log_chat_turn(history_key, agent_key, pending["question"], answer, len(tool_calls))

        st.rerun()
        return

    question = st.chat_input(placeholder)
    if question:
        st.session_state.chat_pending = {"history_key": history_key, "question": question}
        st.rerun()
