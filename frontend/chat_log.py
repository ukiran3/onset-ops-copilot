"""Persists every copilot chat exchange to Loki -- the "backend" for chat
history. Reuses the existing Grafana Cloud stack rather than standing up a
separate database: it's already the system of record for everything else
on set, it survives Cloud Run's stateless/ephemeral instances (unlike
st.session_state or a local file), and it's queryable via the exact same
LogQL tools the agent itself uses.
"""

import json
import os
import time

import requests

LOKI_URL = os.environ["GRAFANA_LOKI_URL"]
LOKI_USERNAME = os.environ["GRAFANA_LOKI_USERNAME"]
LOKI_API_KEY = os.environ["GRAFANA_LOKI_API_KEY"]

_session = requests.Session()


def log_chat_turn(role_key: str, agent_key: str, question: str, answer: str, tool_call_count: int) -> None:
    line = json.dumps(
        {
            "role": role_key,
            "agent": agent_key,
            "question": question,
            "answer": answer,
            "tool_calls": tool_call_count,
        },
        default=str,
    )
    payload = {
        "streams": [
            {
                "stream": {"job": "copilot_chat", "role": role_key, "agent": agent_key},
                "values": [[str(int(time.time() * 1e9)), line]],
            }
        ]
    }
    try:
        _session.post(
            LOKI_URL,
            auth=(LOKI_USERNAME, LOKI_API_KEY),
            json=payload,
            timeout=10,
        )
    except requests.RequestException:
        pass  # chat history logging is best-effort; never block the UI on it
