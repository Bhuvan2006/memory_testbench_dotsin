"""Model selection and the two team members."""
from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.models.base import Model
from agno.models.ollama import Ollama

from src.agents.tools import make_read_calendar
from src.mock_model import MockModel

CALENDAR_INSTRUCTIONS = "Call read_calendar, then give a two sentence summary of how busy the week looks."
WRITER_INSTRUCTIONS = (
    "You write the final reply to the user in one or two short sentences. "
    "Use the earlier conversation and memory you were given. "
    "When asked about a fact, state its most recent value. If it is not in your context, say you do not know."
)


def make_model(provider: str, model_id: str, label: str, settings: dict) -> Model:
    """`label` only matters to the mock, which uses it to act out each role."""
    if provider == "mock":
        return MockModel(label=label)
    if provider == "anthropic":
        return Claude(id=model_id, temperature=settings["temperature"])
    if provider == "ollama":
        return Ollama(id=model_id, options={"temperature": settings["temperature"], "seed": settings["seed"],
                                            "num_ctx": settings["ollama_num_ctx"]})
    raise ValueError(f"Unknown provider: {provider}")


def build_members(provider: str, model_id: str, settings: dict, calendar: dict) -> tuple[Agent, Agent]:
    calendar_agent = Agent(id="calendar", name="calendar_agent", role="Reads and summarises the user's calendar",
                           model=make_model(provider, model_id, "calendar", settings),
                           tools=[make_read_calendar(calendar)], instructions=CALENDAR_INSTRUCTIONS, telemetry=False)
    writer = Agent(id="writer", name="writer", role="Writes the final reply to the user",
                   model=make_model(provider, model_id, "writer", settings),
                   instructions=WRITER_INSTRUCTIONS, telemetry=False)
    return calendar_agent, writer
