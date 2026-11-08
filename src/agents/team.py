"""The Agno Team and the code that runs one conversation turn through it."""
from dataclasses import dataclass

from agno.agent import Agent
from agno.run.base import RunStatus
from agno.team import Team
from agno.team.mode import TeamMode

from src.agents.members import build_members, make_model
from src.memory.base import MemoryStrategy
from src.metrics import Usage

LEADER_INSTRUCTIONS = (
    "You never answer the user yourself, even for greetings, simple statements or facts you already know. "
    "Delegate to calendar_agent only when the user asks about their calendar. "
    "On every message, without exception, your last tool call must delegate to writer, "
    "passing the user's message and any calendar findings as the task. "
    "Return the writer's reply unchanged."
)


@dataclass
class TeamSystem:
    team: Team
    writer: Agent
    calendar: dict


def build_team(provider: str, model_id: str, settings: dict) -> TeamSystem:
    calendar = {"current": None}
    calendar_agent, writer = build_members(provider, model_id, settings, calendar)
    team = Team(name="work_week_team", mode=TeamMode.coordinate, members=[calendar_agent, writer],
                model=make_model(provider, model_id, "leader", settings),
                instructions=LEADER_INSTRUCTIONS, telemetry=False)
    return TeamSystem(team=team, writer=writer, calendar=calendar)


def run_turn(system: TeamSystem, strategy: MemoryStrategy, turn_index: int, user_message: str,
             tool_output: str | None, usage: Usage) -> str:
    # additional_input, because Team.run(list) merges user turns and drops assistant turns.
    context = strategy.build_context(turn_index, user_message)
    system.team.additional_input = context
    system.writer.additional_input = context  # members see only their task unless given context
    system.calendar["current"] = tool_output

    output = system.team.run(user_message)
    if output.status != RunStatus.completed:
        raise RuntimeError(f"Team run failed on turn {turn_index}: {output.content}")
    # A failed member leaves the team "completed" with the error text as its reply, so check each one.
    for member_run in output.member_responses or []:
        if member_run.status != RunStatus.completed:
            raise RuntimeError(f"{member_run.agent_name} failed on turn {turn_index}: {member_run.content}")

    usage.add("leader", output.metrics)  # leader metrics exclude members
    tool_outputs = []
    for member_run in output.member_responses or []:
        usage.add(member_run.agent_name, member_run.metrics)
        tool_outputs += [t.result for t in member_run.tools or [] if t.tool_name == "read_calendar" and t.result]

    reply = str(output.content or "")
    strategy.update(turn_index, user_message, reply, tool_outputs)
    return reply
