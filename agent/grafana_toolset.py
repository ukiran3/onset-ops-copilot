"""Grafana MCP connection, shared by every sub-agent that needs it.

We connect to the open-source `grafana/mcp-grafana` server (not the hosted
`mcp.grafana.com` endpoint: that requires interactive OAuth with no
service-account option, so it never responds to a headless client) --
authenticated with a Grafana service-account token either way.

Two transports, picked automatically:
  - MCP_GRAFANA_URL set (deployed): connect over Streamable HTTP to the
    mcp-grafana Cloud Run service, authenticated with a Google-issued ID
    token for that service's audience (Cloud Run's own IAM, not a Grafana
    credential -- see the "auth note" in ARCHITECTURE2.md: Cloud Run can't
    spawn nested Docker containers, so the local stdio approach below
    doesn't work once deployed).
  - otherwise (local dev): spawn `docker run grafana/mcp-grafana -t stdio`
    as a subprocess, exactly as before.
"""

from google.adk.tools.mcp_tool.mcp_session_manager import (
    StdioConnectionParams,
    StreamableHTTPConnectionParams,
)
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from mcp import StdioServerParameters

import config


def _http_headers() -> dict:
    import subprocess

    import google.auth.transport.requests
    import google.oauth2.id_token

    try:
        # Works when actually running as a service account: Cloud Run's
        # metadata server, or a service-account key file.
        token = google.oauth2.id_token.fetch_id_token(
            google.auth.transport.requests.Request(), config.MCP_GRAFANA_URL
        )
    except Exception:
        # Local dev fallback: user ADC (from `gcloud auth login`) can't mint
        # an ID token for an arbitrary audience directly, but it can
        # impersonate the same service account the deployed app runs as
        # (see the onset-ops-frontend SA + serviceAccountTokenCreator grant).
        token = subprocess.run(
            [
                "gcloud",
                "auth",
                "print-identity-token",
                f"--audiences={config.MCP_GRAFANA_URL}",
                f"--impersonate-service-account={config.RUNTIME_SERVICE_ACCOUNT}",
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    return {"Authorization": f"Bearer {token}"}


def make_grafana_toolset(tool_filter: list[str] | None = None) -> McpToolset:
    if config.MCP_GRAFANA_URL:
        connection_params = StreamableHTTPConnectionParams(
            url=f"{config.MCP_GRAFANA_URL}/mcp",
            headers=_http_headers(),
            timeout=30.0,
        )
    else:
        server_params = StdioServerParameters(
            command="docker",
            args=[
                "run",
                "--rm",
                "-i",
                "-e",
                "GRAFANA_URL",
                "-e",
                "GRAFANA_SERVICE_ACCOUNT_TOKEN",
                "grafana/mcp-grafana",
                "-t",
                "stdio",
            ],
            env={
                "GRAFANA_URL": config.GRAFANA_STACK_URL,
                "GRAFANA_SERVICE_ACCOUNT_TOKEN": config.GRAFANA_SERVICE_ACCOUNT_TOKEN,
            },
        )
        connection_params = StdioConnectionParams(server_params=server_params, timeout=30.0)

    return McpToolset(connection_params=connection_params, tool_filter=tool_filter)
