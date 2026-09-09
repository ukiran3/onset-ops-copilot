import os
from pathlib import Path

import force_ipv4  # noqa: F401  (must patch socket before any HTTP client is used)
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

GRAFANA_PROMETHEUS_URL = os.environ["GRAFANA_PROMETHEUS_URL"]
GRAFANA_PROMETHEUS_USERNAME = os.environ["GRAFANA_PROMETHEUS_USERNAME"]
GRAFANA_PROMETHEUS_API_KEY = os.environ["GRAFANA_PROMETHEUS_API_KEY"]

GRAFANA_LOKI_URL = os.environ["GRAFANA_LOKI_URL"]
GRAFANA_LOKI_USERNAME = os.environ["GRAFANA_LOKI_USERNAME"]
GRAFANA_LOKI_API_KEY = os.environ["GRAFANA_LOKI_API_KEY"]
