"""One-time provisioning: create a real Grafana dashboard and a real alert
rule on top of the synthetic on-set metrics, via the Grafana HTTP API.

Without this, `search_dashboards` and `alerting_manage_rules` (MCP tools the
hackathon's Grafana track explicitly calls out) have nothing to find --
we'd only ever pushed raw metrics/logs, never a saved dashboard or alert.

Safe to re-run: dashboard create uses overwrite=true, alert rule create
skips if a rule with the same title already exists.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data_generator"))
import force_ipv4  # noqa: E402  (must patch socket before any HTTP client is used)

import os  # noqa: E402

import requests  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

BASE = os.environ["GRAFANA_STACK_URL"]
TOKEN = os.environ["GRAFANA_SERVICE_ACCOUNT_TOKEN"]
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

PROM_UID = "grafanacloud-prom"
FOLDER_TITLE = "On-Set Ops Copilot"


def get_or_create_folder() -> str:
    r = requests.get(f"{BASE}/api/folders", headers=HEADERS, timeout=20)
    r.raise_for_status()
    for f in r.json():
        if f["title"] == FOLDER_TITLE:
            print(f"Folder already exists: {f['uid']}")
            return f["uid"]

    r = requests.post(f"{BASE}/api/folders", headers=HEADERS, json={"title": FOLDER_TITLE}, timeout=20)
    r.raise_for_status()
    uid = r.json()["uid"]
    print(f"Created folder: {uid}")
    return uid


def create_dashboard(folder_uid: str) -> str:
    def ts_panel(panel_id, title, expr, x, y, unit="short"):
        return {
            "id": panel_id,
            "title": title,
            "type": "timeseries",
            "gridPos": {"h": 8, "w": 12, "x": x, "y": y},
            "datasource": {"type": "prometheus", "uid": PROM_UID},
            "fieldConfig": {"defaults": {"unit": unit}, "overrides": []},
            "targets": [
                {
                    "expr": expr,
                    "legendFormat": "__auto",
                    "refId": "A",
                    "datasource": {"type": "prometheus", "uid": PROM_UID},
                }
            ],
        }

    dashboard = {
        "id": None,
        "uid": "onset-ops-overview",
        "title": "On-Set Ops Overview",
        "tags": ["onset-ops-copilot"],
        "timezone": "browser",
        "schemaVersion": 39,
        "version": 0,
        "refresh": "10s",
        "time": {"from": "now-3h", "to": "now"},
        "panels": [
            ts_panel(1, "Schedule Burn (min)", "schedule_burn_minutes", 0, 0, unit="m"),
            ts_panel(2, "Generator Load (%)", "generator_load_pct", 12, 0, unit="percent"),
            ts_panel(3, "Wireless Mic Battery (%)", "battery_pct", 0, 8, unit="percent"),
            ts_panel(4, "RF Channel Conflicts", "rf_channel_conflicts", 12, 8, unit="short"),
        ],
    }

    r = requests.post(
        f"{BASE}/api/dashboards/db",
        headers=HEADERS,
        json={"dashboard": dashboard, "folderUid": folder_uid, "overwrite": True},
        timeout=20,
    )
    r.raise_for_status()
    resp = r.json()
    print(f"Dashboard created/updated: {resp['url']}")
    return resp["uid"]


def create_alert_rule(folder_uid: str) -> None:
    title = "Schedule burn critical (>10min)"

    r = requests.get(f"{BASE}/api/v1/provisioning/alert-rules", headers=HEADERS, timeout=20)
    r.raise_for_status()
    for rule in r.json():
        if rule["title"] == title:
            print(f"Alert rule already exists: {rule['uid']}")
            return

    body = {
        "title": title,
        "ruleGroup": "onset-ops-alerts",
        "folderUID": folder_uid,
        "condition": "C",
        "data": [
            {
                "refId": "A",
                "queryType": "",
                "relativeTimeRange": {"from": 300, "to": 0},
                "datasourceUid": PROM_UID,
                "model": {
                    "expr": 'max(schedule_burn_minutes{scene="12A"})',
                    "instant": True,
                    "refId": "A",
                },
            },
            {
                "refId": "C",
                "queryType": "",
                "relativeTimeRange": {"from": 300, "to": 0},
                "datasourceUid": "__expr__",
                "model": {
                    "type": "threshold",
                    "expression": "A",
                    "conditions": [
                        {
                            "evaluator": {"type": "gt", "params": [10]},
                            "operator": {"type": "and"},
                            "query": {"params": ["A"]},
                            "reducer": {"type": "last"},
                        }
                    ],
                    "refId": "C",
                },
            },
        ],
        "noDataState": "NoData",
        "execErrState": "Error",
        "for": "1m",
        "orgID": 1,
        "labels": {"severity": "critical", "team": "ops"},
        "annotations": {
            "summary": "Scene 12A schedule burn is above the 10 minute threshold.",
        },
    }

    r = requests.post(f"{BASE}/api/v1/provisioning/alert-rules", headers=HEADERS, json=body, timeout=20)
    if not r.ok:
        print("Alert rule creation failed:", r.status_code, r.text)
        r.raise_for_status()
    print(f"Alert rule created: {r.json()['uid']} (will move pending -> firing within ~1-2 min)")


if __name__ == "__main__":
    folder_uid = get_or_create_folder()
    create_dashboard(folder_uid)
    create_alert_rule(folder_uid)
    print("Done.")
