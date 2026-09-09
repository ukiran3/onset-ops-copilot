import json
from dataclasses import dataclass, field

import requests


@dataclass
class LogLine:
    labels: dict[str, str]
    message: str
    timestamp_ns: int


class LokiClient:
    def __init__(self, url: str, username: str, api_key: str, timeout: float = 30.0):
        self.url = url
        self.auth = (username, api_key)
        self.timeout = timeout
        self.session = requests.Session()

    def push(self, lines: list[LogLine]) -> requests.Response:
        streams_by_labels: dict[tuple, list[list[str]]] = {}
        for line in lines:
            key = tuple(sorted(line.labels.items()))
            streams_by_labels.setdefault(key, []).append(
                [str(line.timestamp_ns), line.message]
            )

        payload = {
            "streams": [
                {"stream": dict(key), "values": values}
                for key, values in streams_by_labels.items()
            ]
        }
        resp = self.session.post(
            self.url,
            data=json.dumps(payload),
            auth=self.auth,
            headers={"Content-Type": "application/json"},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp


def structured_message(**fields) -> str:
    """JSON-encode a structured log line so LogQL `| json` can parse fields."""
    return json.dumps(fields, default=str)
