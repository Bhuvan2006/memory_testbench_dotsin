"""Model selection and the two team members."""
import functools
import random
import threading
import time

import httpx
from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.models.base import Model
from agno.models.nvidia import Nvidia
from agno.models.ollama import Ollama

from src.agents.tools import make_read_calendar
from src.mock_model import MockModel

CALENDAR_INSTRUCTIONS = "Call read_calendar, then give a two sentence summary of how busy the week looks."
WRITER_INSTRUCTIONS = (
    "You write the final reply to the user in one or two short sentences. "
    "Use the earlier conversation and memory you were given. "
    "When asked about a fact, state its most recent value. If it is not in your context, say you do not know."
)


class Pacer:
    """httpx request hook that spaces out every HTTP request, including SDK retries."""

    def __init__(self, requests_per_minute: float):
        self.interval = 60 / requests_per_minute
        self.next_slot = 0.0
        self.lock = threading.Lock()

    def __call__(self, request=None) -> None:
        with self.lock:
            now = time.monotonic()
            slot = max(now, self.next_slot)
            self.next_slot = slot + self.interval
        time.sleep(slot - now)


class RateLimitBackoff:
    """httpx response hook that waits 15-120 s with jitter on a 429, because the SDK's own backoff stops near 8 s."""

    def __init__(self, base: float = 15.0, cap: float = 120.0):
        self.base = base
        self.cap = cap
        self.consecutive = 0

    def __call__(self, response: httpx.Response) -> None:
        if response.status_code != 429:
            self.consecutive = 0
            return
        wait = min(self.cap, self.base * 2 ** self.consecutive)
        self.consecutive += 1
        time.sleep(wait * random.uniform(0.5, 1.0))


@functools.cache
def _paced_client(requests_per_minute: float) -> httpx.Client:
    # One shared client, because the rate limit covers the leader, members and memory calls together.
    return httpx.Client(event_hooks={"request": [Pacer(requests_per_minute)], "response": [RateLimitBackoff()]})


def make_model(provider: str, model_id: str, label: str, settings: dict) -> Model:
    """`label` only matters to the mock, which uses it to act out each role."""
    if provider == "mock":
        return MockModel(label=label)
    if provider == "anthropic":
        return Claude(id=model_id, temperature=settings["temperature"])
    if provider == "ollama":
        return Ollama(id=model_id, options={"temperature": settings["temperature"], "seed": settings["seed"],
                                            "num_ctx": settings["ollama_num_ctx"]})
    if provider == "nvidia":  # OpenAI-compatible; Agno's class reads NVIDIA_API_KEY from the environment
        # max_retries is the OpenAI SDK's exponential backoff on 429, 5xx and connection errors.
        return Nvidia(id=model_id, temperature=settings["temperature"], seed=settings["seed"],
                      max_retries=settings["nvidia_max_retries"],
                      http_client=_paced_client(settings["nvidia_requests_per_minute"]))
    raise ValueError(f"Unknown provider: {provider}")


def build_members(provider: str, model_id: str, settings: dict, calendar: dict) -> tuple[Agent, Agent]:
    calendar_agent = Agent(id="calendar", name="calendar_agent", role="Reads and summarises the user's calendar",
                           model=make_model(provider, model_id, "calendar", settings),
                           tools=[make_read_calendar(calendar)], instructions=CALENDAR_INSTRUCTIONS, telemetry=False)
    writer = Agent(id="writer", name="writer", role="Writes the final reply to the user",
                   model=make_model(provider, model_id, "writer", settings),
                   instructions=WRITER_INSTRUCTIONS, telemetry=False)
    return calendar_agent, writer
