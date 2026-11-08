"""The interface every memory strategy implements, plus shared helpers."""
from abc import ABC, abstractmethod

from agno.agent import Agent
from agno.models.base import Model
from agno.models.message import Message
from agno.run.base import RunStatus

from src.metrics import Usage

TOOL_MARKER = "[Tool output]"


class MemoryStrategy(ABC):
    name = "base"

    @abstractmethod
    def build_context(self, turn_index: int, user_message: str) -> list[Message]:
        """Return the prior context to send with this turn."""

    @abstractmethod
    def update(self, turn_index: int, user_message: str, assistant_reply: str, tool_outputs: list[str]) -> None:
        """Record a finished turn."""


def turn_messages(turn: dict) -> list[Message]:
    """Render a stored turn. Tool output follows a marker in the assistant message."""
    reply = turn["reply"]
    if turn["tool_outputs"]:
        reply += f"\n\n{TOOL_MARKER}\n" + "\n".join(turn["tool_outputs"])
    return [Message(role="user", content=turn["user"]), Message(role="assistant", content=reply)]


class MemoryLLM:
    """Model calls made by the memory system, counted under 'memory_ops' so savings are not overstated."""

    def __init__(self, model: Model, usage: Usage):
        self.agent = Agent(name="memory_ops", model=model, telemetry=False)
        self.usage = usage

    def __call__(self, prompt: str) -> str:
        output = self.agent.run(prompt)
        if output.status != RunStatus.completed:
            raise RuntimeError(f"Memory model call failed: {output.content}")
        self.usage.add("memory_ops", output.metrics)
        return str(output.content or "")
