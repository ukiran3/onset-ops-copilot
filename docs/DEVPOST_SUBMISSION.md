# Devpost submission draft

Copy-paste into the Devpost form fields. Matches Devpost's standard section headers.

---

## Project name

Video Village — On-Set Ops & Continuity Copilot

## Tagline (one sentence)

A multi-agent Gemini copilot that investigates a shoot day for you — live in Grafana Cloud data,
not a dashboard you have to read yourself.

## Partner track

Grafana Labs

## Links

- **Hosted app:** https://onset-ops-frontend-154756890593.us-central1.run.app
- **Repo:** https://github.com/ukiran3/onset-ops-copilot
- **Video:** _[add once recorded]_

---

## Inspiration

Every hackathon-adjacent AI tool for film seems to target the director or the writer — script
coverage, storyboard generation, shot-list assistants. The below-the-line crew who actually run a
shoot day — 1st ADs, UPMs, script supervisors — get none of it, even though they're the ones
staring at a call sheet trying to figure out why a scene slipped, or flipping through Polaroids to
check if the coffee mug was on the desk in the last take.

We wanted to build for that crew instead, and we wanted the tool to actually *investigate*, not
just display numbers. Grafana already treats "correlate an alert with root cause" as its whole job
— that's exactly the demo moment we wanted the agent to perform live, not simulate.

## What it does

Video Village is a live mission-control dashboard with four crew-role views (1st AD/UPM, Sound
Mixer, Gaffer/Electric, Script Supervisor) sitting on top of two Gemini agents:

- **`ops_agent`** handles schedule, equipment, and incidents — ask it "why is scene 12A behind
  schedule?" and it queries live Prometheus metrics and Loki logs via the Grafana MCP server,
  correlates a real firing alert with a metric trend and a log line, and answers with the actual
  numbers it found.
- **`continuity_agent`** is a digital script supervisor — ask about a scene and it pulls
  structured continuity logs per take (props, wardrobe, lighting) and flags mismatches, like a
  coffee mug that disappeared for one take and came back the next.

Every tool call is real: `query_prometheus`, `query_loki_logs`, `search_dashboards`,
`alerting_manage_rules` all hit a live Grafana Cloud stack through Grafana's own MCP server.

## How we built it

- **Agents:** Google Agent Development Kit (ADK), Gemini 2.5 Flash via Vertex AI. A root
  orchestrator routes to `ops_agent` / `continuity_agent`, each wired to Grafana via `McpToolset`.
- **Grounding:** Grafana Cloud — Mimir (metrics), Loki (logs), a real provisioned dashboard, and a
  real alert rule that fires off the live synthetic data — all reachable through
  `grafana/mcp-grafana`, Grafana's own open-source MCP server implementation.
- **Data:** a Python generator pushes synthetic on-set telemetry (schedule burn, generator load,
  wireless mic battery, RF conflicts) via Prometheus remote_write, and structured continuity/
  incident/schedule logs via the Loki push API, including one engineered "problem" — a generator
  overheating right as a schedule slip fires — so the agent has something real to investigate.
- **Frontend:** Streamlit, with the four role views sharing the two backend agents, live-updating
  charts queried directly from Grafana, and a chat panel that shows the agent's tool-call trace,
  not just its final answer. Every chat exchange is itself persisted back to Loki
  (`job=copilot_chat`) — the app writes to the same data plane it reads from.
- **Deployment:** two Cloud Run services on Google Cloud — the Streamlit frontend, and
  `mcp-grafana` running as its own HTTP service, authenticated service-to-service via Cloud Run's
  own IAM (Google-issued ID tokens).

## Challenges we ran into

- **The hosted `mcp.grafana.com` MCP endpoint requires interactive OAuth with no service-account
  path** — it never responds to a headless agent. We run the identical open-source
  `grafana/mcp-grafana` server ourselves instead, authenticated with a Grafana service-account
  token — Grafana's own implementation, not a workaround.
- **Cloud Run can't spawn nested Docker containers**, so the local "run mcp-grafana as a Docker
  subprocess" approach doesn't work once deployed. We split it into its own Cloud Run service and
  switched the agent to Streamable HTTP, authenticated with Cloud Run's own IAM — one codebase,
  two transports, picked automatically by environment.
- **Grafana Cloud's free-tier metrics ingester rejects samples older than ~105 minutes** — found
  empirically, not documented anywhere we could see. Our "backfill 2 hours of history so the
  dashboard looks alive" step had to clamp metrics to the trailing ~95 minutes (logs have no such
  limit, so continuity/incident history still goes back the full window).
- **Floating dependency version bounds broke a deploy**: a fresh `pip install` on Cloud Build
  resolved brand-new major versions of `mcp` and `google-adk` that don't work together, even
  though the exact same spec had worked fine days earlier locally. Pinned everything exactly once
  we found it.

## Accomplishments that we're proud of

- The agent's investigation is genuinely live, not scripted — same question asked twice can
  produce a different tool-call sequence depending on what it decides to check first.
- A real Grafana alert rule that actually transitions from pending to firing based on live data,
  giving the agent something authentic to find via `alerting_manage_rules`, matching the
  hackathon's own "investigate a firing alert" example almost exactly.
- Four different crew-facing views reusing just two backend agents — no per-role backend
  complexity, and it visibly reinforces the multi-agent architecture rather than hiding it.

## What we learned

Building an agent against a real observability stack surfaces constraints no amount of reading
documentation does — ingestion windows, transport auth quirks, dependency drift between "it
worked when I tested it" and "it worked in a clean environment." Grounding in genuinely live data
is worth the extra friction: the agent's answers cite real timestamps and real numbers because
there was never a mocked path to fall back on.

## What's next

- A config-driven role system so new crew roles/lenses can be added without touching code.
- Swap the synthetic generator for a real on-set telemetry feed and crew-entered call sheet data.
- Wire in Parallel Search as a grounding tool for real-world lookups the telemetry can't answer
  ("what does fault code E44 mean," "nearest steadicam rental").
- Grafana Sift/Asserts investigation tools for deeper automated root-cause analysis.

## Built With

python, google-cloud, vertex-ai, gemini, google-agent-development-kit, grafana, grafana-cloud,
model-context-protocol, mcp, streamlit, google-cloud-run, docker, prometheus, loki, plotly
