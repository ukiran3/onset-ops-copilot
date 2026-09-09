"""CLI proof-of-loop: ask the root agent a question and print every tool
call it makes along the way, so it's visible (not just the final answer)
that Grafana MCP tools are actually being invoked at runtime.

Usage:
    python main.py "why is scene 12A behind schedule?"
"""

import sys

import force_ipv4  # noqa: F401  (must patch socket before any HTTP client is used)

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from root_agent import build_root_agent

APP_NAME = "onset_ops_copilot"
USER_ID = "demo_user"


def main():
    question = " ".join(sys.argv[1:]) or "why is scene 12A behind schedule?"

    agent = build_root_agent()
    session_service = InMemorySessionService()
    session = session_service.create_session_sync(app_name=APP_NAME, user_id=USER_ID)
    runner = Runner(app_name=APP_NAME, agent=agent, session_service=session_service)

    print(f"> {question}\n")

    new_message = types.Content(role="user", parts=[types.Part(text=question)])
    for event in runner.run(user_id=USER_ID, session_id=session.id, new_message=new_message):
        author = event.author
        if not event.content or not event.content.parts:
            continue
        for part in event.content.parts:
            if part.function_call:
                print(f"[{author}] TOOL CALL: {part.function_call.name}({part.function_call.args})")
            elif part.function_response:
                resp = str(part.function_response.response)
                print(f"[{author}] TOOL RESULT ({part.function_response.name}): {resp[:400]}")
            elif part.text:
                print(f"[{author}]: {part.text}")


if __name__ == "__main__":
    main()
