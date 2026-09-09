"""Direct Prometheus/Loki queries for the dashboard's own charts.

Deliberately separate from the agent's path (agent_bridge.py / Grafana MCP):
the charts need fast, cheap, frequent polling, which would be wasteful to
route through an LLM tool-call loop. Goes straight to Grafana's
datasource-proxy API with the same service-account token.
"""

import time

import config  # agent/config.py -- see app.py's sys.path bootstrap
import requests

PROM_UID = "grafanacloud-prom"
LOKI_UID = "grafanacloud-logs"


def _headers() -> dict:
    return {"Authorization": f"Bearer {config.GRAFANA_SERVICE_ACCOUNT_TOKEN}"}


def prom_range(expr: str, lookback_s: int = 5400, step_s: int = 30) -> dict:
    """Returns {label_tuple: [(unix_ts, float_value), ...]} per series."""
    now = int(time.time())
    resp = requests.get(
        f"{config.GRAFANA_STACK_URL}/api/datasources/proxy/uid/{PROM_UID}/api/v1/query_range",
        headers=_headers(),
        params={"query": expr, "start": now - lookback_s, "end": now, "step": step_s},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()["data"]["result"]

    series = {}
    for item in data:
        labels = tuple(sorted((k, v) for k, v in item["metric"].items() if k != "__name__"))
        series[labels] = [(int(ts), float(v)) for ts, v in item["values"]]
    return series


def prom_instant(expr: str) -> dict:
    """Returns {label_tuple: float_value} for the latest value per series."""
    resp = requests.get(
        f"{config.GRAFANA_STACK_URL}/api/datasources/proxy/uid/{PROM_UID}/api/v1/query",
        headers=_headers(),
        params={"query": expr},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()["data"]["result"]

    out = {}
    for item in data:
        labels = tuple(sorted((k, v) for k, v in item["metric"].items() if k != "__name__"))
        out[labels] = float(item["value"][1])
    return out


def loki_range(logql: str, lookback_s: int = 21600, limit: int = 200) -> list[dict]:
    """Returns log lines newest-first: [{"ts_ns": int, "line": str, "labels": dict}, ...]."""
    now_ns = int(time.time() * 1e9)
    resp = requests.get(
        f"{config.GRAFANA_STACK_URL}/api/datasources/proxy/uid/{LOKI_UID}/loki/api/v1/query_range",
        headers=_headers(),
        params={
            "query": logql,
            "start": now_ns - lookback_s * 1_000_000_000,
            "end": now_ns,
            "limit": limit,
            "direction": "backward",
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()["data"]["result"]

    lines = []
    for stream in data:
        for ts_ns, line in stream["values"]:
            lines.append({"ts_ns": int(ts_ns), "line": line, "labels": stream["stream"]})
    lines.sort(key=lambda x: x["ts_ns"], reverse=True)
    return lines


def alerting_firing_count() -> int:
    resp = requests.get(
        f"{config.GRAFANA_STACK_URL}/api/alertmanager/grafana/api/v2/alerts",
        headers=_headers(),
        params={"active": "true"},
        timeout=15,
    )
    resp.raise_for_status()
    return len(resp.json())
