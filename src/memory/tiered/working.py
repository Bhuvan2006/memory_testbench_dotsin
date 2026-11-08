"""Working memory: the last N turns verbatim, with large tool output trimmed."""
from collections import deque

from src.memory.base import turn_messages


def trim(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}\n...[trimmed {len(text) - max_chars} chars, summary kept in episodic memory]"


class WorkingMemory:
    def __init__(self, turns: int, tool_trim_chars: int):
        self.turns = deque(maxlen=turns)
        self.tool_trim_chars = tool_trim_chars

    def add(self, user: str, reply: str, tool_outputs: list[str]) -> None:
        trimmed = [trim(output, self.tool_trim_chars) for output in tool_outputs]
        self.turns.append({"user": user, "reply": reply, "tool_outputs": trimmed})

    def messages(self) -> list:
        return [message for turn in self.turns for message in turn_messages(turn)]
