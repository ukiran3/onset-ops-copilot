"""Grafana MCP connection, shared by every sub-agent that needs it.

We connect to the open-source `grafana/mcp-grafana` server over stdio (via
Docker) rather than the hosted `mcp.grafana.com` endpoint: the hosted server
requires interactive OAuth with no service-account option, so it doesn't
respond to headless clients like this agent. Running the OSS server
ourselves, authenticated with a Grafana service-account token, works the
same way locally and once deployed (see ARCHITECTURE2.md's auth note).
"""

from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from mcp import StdioServerParameters

import config


def make_grafana_toolset(tool_filter: list[str] | None = None) -> McpToolset:
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
    return McpToolset(
        connection_params=StdioConnectionParams(server_params=server_params, timeout=30.0),
        tool_filter=tool_filter,
    )
