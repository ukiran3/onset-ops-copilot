from google.adk import Agent

import config
from continuity_agent import build_continuity_agent
from ops_agent import build_ops_agent

ROOT_INSTRUCTION = """\
You are the orchestrator for an On-Set Ops & Continuity Copilot, used by \
crew during a live shoot day.

Route requests to the right specialist:
- General set status, schedule slips, equipment/incident questions -> \
ops_agent.
- Questions about a specific scene/take's props, wardrobe, lighting, or \
continuity mismatches -> continuity_agent.

If a request needs both (e.g. "what's going on with scene 12A"), consult \
both and combine their findings into one coherent answer. Never answer \
ops or continuity questions yourself from general knowledge -- always \
delegate so the answer is grounded in live Grafana data.
"""


def build_root_agent() -> Agent:
    return Agent(
        name="onset_ops_copilot",
        model=config.MODEL_NAME,
        description="Root orchestrator for on-set ops and continuity questions.",
        instruction=ROOT_INSTRUCTION,
        sub_agents=[build_ops_agent(), build_continuity_agent()],
    )


root_agent = build_root_agent()
