# On-Set Ops & Continuity Copilot — Architecture

## The pitch

A multi-agent Gemini system that gives a 1st AD / UPM a live "mission control" view of a shoot
day — schedule burn, equipment health, incidents — and lets anyone click into a specific
scene/take to pull up the script supervisor's continuity view for that shot: prop/wardrobe/
lighting state, flagged mismatches vs. the previous take, and a generated continuity note. Built
on Google ADK + Vertex AI, grounded in live Grafana Cloud metrics/logs via the Grafana MCP
server.

This targets below-the-line crew (ADs, UPMs, script supervisors) instead of the oversaturated
director/writer tooling space.

## Why this shape

- **Grafana is the spine, not a bolt-on.** Real production data (schedule status, gear
  telemetry, incidents) is naturally time-series + logs. The agent's job is to *investigate* —
  correlate an alert with root cause — which is the demo moment judges want to see.
- **The continuity panel reuses the same data plane.** Continuity notes are structured log lines
  in Loki, tagged by scene/take. No second database.
- **Role-based views share one backend.** The dashboard's four roles (1st AD/UPM, Sound Mixer,
  Gaffer/Electric, Script Supervisor) are different lenses over the same two sub-agents
  (`ops_agent`, `continuity_agent`) — no per-role backend complexity.

## System architecture

```
Synthetic Set Data Generator (Python, data_generator/)
  - schedule burn, equipment telemetry, incidents, continuity records
        |
        | Prometheus remote_write         | Loki push API
        v                                 v
              Grafana Cloud (Mimir + Loki + Dashboards + Alerting)
                             |
                             | Grafana MCP server (grafana/mcp-grafana)
                             v
          Google ADK Agent (agent/) on Vertex AI (Gemini)
            Root Orchestrator
              +-- ops_agent          (schedule, equipment, incidents, alerts)
              +-- continuity_agent   (props/wardrobe/lighting per scene/take)
                             |
                             v
          Streamlit frontend ("Video Village", frontend/)
            - role rail (4 roles -> 2 backend agents)
            - live telemetry charts (direct Prometheus/Loki queries)
            - copilot chat (routes to the agent, shows the tool-call trace)
            - chat history persisted to Loki (job=copilot_chat)
```

## Two Grafana MCP transports, one codebase

`agent/grafana_toolset.py` picks the transport automatically:

- **Local dev** (`MCP_GRAFANA_URL` unset): spawns `docker run grafana/mcp-grafana -t stdio` as a
  subprocess.
- **Deployed** (`MCP_GRAFANA_URL` set): connects over Streamable HTTP to `mcp-grafana` running as
  its own Cloud Run service, authenticated with a Google-issued ID token for that service's
  audience (Cloud Run IAM, not a Grafana credential).

Why two services instead of one: Cloud Run can't spawn nested Docker containers, so the local
`docker run ... -t stdio` approach doesn't work once deployed. `mcp-grafana` is Grafana's own
open-source implementation of the MCP server — not a workaround. We use it (rather than the
hosted `mcp.grafana.com` endpoint) because the hosted endpoint requires interactive OAuth with no
service-account option, so it never responds to a headless agent.

## Data model (synthetic)

**Metrics** (Prometheus, pushed via remote_write):
- `schedule_burn_minutes{scene}` — minutes behind/ahead of schedule
- `generator_load_pct{unit}` — genny-1, genny-2
- `battery_pct{device}` — wireless mic packs
- `rf_channel_conflicts{zone}`

**Logs** (Loki, pushed via push API):
- `{job="incidents"}` — severity-tagged free text
- `{job="schedule"}` — scene changes, schedule slips
- `{job="continuity", scene, take}` — structured continuity notes (props, wardrobe, lighting,
  script supervisor comment)
- `{job="copilot_chat"}` — every question the copilot answers, for audit/history

The generator (`data_generator/generate.py`) backfills ~2 hours of history and then live-pushes
every 10s, including one engineered "problem": scene 12A's schedule burn and genny-1's load both
ramp into crisis together, with a real Grafana alert rule configured to fire on it
(`scripts/setup_grafana_dashboard_and_alert.py`) — the demo moment.
