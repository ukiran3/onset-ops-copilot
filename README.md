# Video Village — On-Set Ops & Continuity Copilot

A multi-agent Gemini system that gives a 1st AD / UPM a live "mission control" view of a shoot
day, and lets any crew role click into a specific scene/take to see continuity status — all
grounded in real, live Grafana Cloud data via the Grafana MCP server.

Built for [Agentic Cinema: The Blockbuster Hackathon](https://agentic-cinema.devpost.com/) —
**Grafana Labs** partner track.

**Live demo:** https://onset-ops-frontend-154756890593.us-central1.run.app
**Demo video:** _[add YouTube/Vimeo link here]_

## What it does

- **Investigates, doesn't just display.** Ask the copilot "why is scene 12A behind schedule?"
  and watch it actually call Grafana MCP tools live — `query_prometheus`, `query_loki_logs`,
  `search_dashboards`, `alerting_manage_rules` — correlate a real firing alert with a metric
  trend and a log line, and answer with the numbers it found, not a canned response.
- **Four crew roles, two agents.** 1st AD/UPM, Sound Mixer, and Gaffer/Electric all talk to
  `ops_agent` through a different lens (schedule/equipment vs. audio vs. power); Script
  Supervisor talks to `continuity_agent`, which flags prop/wardrobe/lighting mismatches between
  takes.
- **Everything is real Grafana, not a mock.** A synthetic data generator stands in for on-set
  telemetry (the one part of the demo that's necessarily fake — no live production to plug into
  for a hackathon), but from the Prometheus/Loki push onward, every dashboard, alert rule, and
  agent tool call is genuine Grafana Cloud.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full system design, including why
Grafana's MCP server runs as its own Cloud Run service rather than a local Docker subprocess once
deployed.

## Tech stack

| Layer | Tech |
|---|---|
| Agents | Google Agent Development Kit (ADK), Gemini 2.5 Flash via Vertex AI |
| Grounding | Grafana Cloud (Mimir, Loki, Dashboards, Alerting) via the Grafana MCP server (`grafana/mcp-grafana`) |
| Frontend | Streamlit |
| Data generation | Python — hand-rolled Prometheus remote_write client + Loki push client |
| Deployment | Google Cloud Run (two services: the frontend, and `mcp-grafana`) |

## Repo layout

```
agent/            ADK agents (root orchestrator, ops_agent, continuity_agent) + Grafana MCP wiring
data_generator/    Synthetic on-set metrics/logs generator (Prometheus + Loki)
frontend/          Streamlit app ("Video Village")
scripts/           One-off setup: Grafana dashboard + alert rule provisioning, smoke tests
docs/              Architecture writeup
Dockerfile         Frontend deployment image
```

## Running it yourself

### 1. Prerequisites

- Python 3.10+
- A Grafana Cloud stack (free tier works) — Prometheus + Loki push credentials, and a service
  account token (Administration → Service accounts)
- A GCP project with Vertex AI enabled, `gcloud` authenticated (`gcloud auth login` +
  `gcloud auth application-default login`)
- Docker Desktop (for local dev only — runs `mcp-grafana` as a subprocess)

### 2. Configure

```bash
cp .env.example .env
# fill in your Grafana Cloud + GCP values
```

### 3. Install

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # data generator + full toolchain
pip install -r frontend/requirements.txt # lighter set, if you only want the app
```

### 4. Seed data + provision Grafana

```bash
python data_generator/generate.py          # backfills history, then live-pushes every 10s
python scripts/setup_grafana_dashboard_and_alert.py  # creates a real dashboard + alert rule
```

### 5. Run the agent from the CLI (proves the MCP loop works)

```bash
python agent/main.py "why is scene 12A behind schedule?"
```

### 6. Run the frontend

```bash
cd frontend && streamlit run app.py
```

## Deploying

Two Cloud Run services:

```bash
# 1. mcp-grafana, as its own HTTP service (Cloud Run can't nest Docker containers)
gcloud run deploy mcp-grafana \
  --image=docker.io/grafana/mcp-grafana:latest \
  --port=8080 --no-allow-unauthenticated \
  --set-env-vars="GRAFANA_URL=...,GRAFANA_SERVICE_ACCOUNT_TOKEN=..." \
  --args="-t=streamable-http,-address=:8080,-allowed-hosts=*,-allowed-origins=*"

# 2. the frontend, pointed at that service
gcloud run deploy onset-ops-frontend \
  --source=. --port=8080 --allow-unauthenticated \
  --service-account=<runtime-sa> \
  --env-vars-file=<your env values, including MCP_GRAFANA_URL from step 1>
```

The runtime service account needs `roles/run.invoker` on `mcp-grafana` and `roles/aiplatform.user`
at the project level.

## License

MIT — see [`LICENSE`](LICENSE).
