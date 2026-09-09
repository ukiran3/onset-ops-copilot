"""Sync bridge between Streamlit and the ADK agents.

Streamlit reruns this script top-to-bottom on every interaction, so agent
construction (which spawns the Grafana MCP Docker container over stdio)
must be cached as a resource -- otherwise every chat message would spin up
a fresh container. One shared runtime per agent role for the life of the
server process is the right tradeoff for a single-demo hackathon app.
"""

import streamlit as st
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

APP_NAME = "onset_ops_copilot"
USER_ID = "demo_user"


@st.cache_resource(show_spinner=False)
def _get_runtime(agent_key: str):
    if agent_key == "ops":
        from ops_agent import build_ops_agent

        agent = build_ops_agent()
    elif agent_key == "continuity":
        from continuity_agent import build_continuity_agent

        agent = build_continuity_agent()
    else:
        raise ValueError(f"Unknown agent_key: {agent_key}")

    session_service = InMemorySessionService()
    session = session_service.create_session_sync(app_name=APP_NAME, user_id=USER_ID)
    runner = Runner(app_name=APP_NAME, agent=agent, session_service=session_service)
    return runner, session.id


def ask(agent_key: str, question: str) -> list[dict]:
    """Runs a question through the given agent role, returns a list of
    render-ready events: {"kind": "tool_call"|"tool_result"|"text", ...}."""
    runner, session_id = _get_runtime(agent_key)
    new_message = types.Content(role="user", parts=[types.Part(text=question)])

    events = []
    for event in runner.run(user_id=USER_ID, session_id=session_id, new_message=new_message):
        if not event.content or not event.content.parts:
            continue
        for part in event.content.parts:
            if part.function_call:
                events.append(
                    {
                        "kind": "tool_call",
                        "author": event.author,
                        "name": part.function_call.name,
                        "args": dict(part.function_call.args or {}),
                    }
                )
            elif part.function_response:
                events.append(
                    {
                        "kind": "tool_result",
                        "author": event.author,
                        "name": part.function_response.name,
                        "response": part.function_response.response,
                    }
                )
            elif part.text:
                events.append({"kind": "text", "author": event.author, "text": part.text})
    return events
