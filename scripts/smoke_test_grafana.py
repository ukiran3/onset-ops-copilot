"""One-off connectivity check: push a single metric + log line to Grafana Cloud
and confirm both succeed. Run once after filling in .env, before trusting the
real data generator.
"""

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data_generator"))
import force_ipv4  # noqa: E402,F401  (must patch socket before any HTTP client is used)
from prom_remote_write import Metric, PrometheusRemoteWriter  # noqa: E402

load_dotenv()


def check_prometheus() -> None:
    writer = PrometheusRemoteWriter(
        url=os.environ["GRAFANA_PROMETHEUS_URL"],
        username=os.environ["GRAFANA_PROMETHEUS_USERNAME"],
        api_key=os.environ["GRAFANA_PROMETHEUS_API_KEY"],
    )
    metric = Metric(
        name="onset_ops_smoketest",
        value=1.0,
        labels={"source": "setup-smoke-test"},
    )
    resp = writer.push([metric])
    print(f"Prometheus push: HTTP {resp.status_code}")


def check_loki() -> None:
    import requests

    now_ns = str(int(time.time() * 1e9))
    resp = requests.post(
        os.environ["GRAFANA_LOKI_URL"],
        auth=(os.environ["GRAFANA_LOKI_USERNAME"], os.environ["GRAFANA_LOKI_API_KEY"]),
        json={
            "streams": [
                {
                    "stream": {"job": "smoketest"},
                    "values": [[now_ns, "hello from onset-ops setup smoke test (python)"]],
                }
            ]
        },
        timeout=10,
    )
    resp.raise_for_status()
    print(f"Loki push: HTTP {resp.status_code}")


if __name__ == "__main__":
    check_prometheus()
    check_loki()
    print("Both pushes succeeded.")
