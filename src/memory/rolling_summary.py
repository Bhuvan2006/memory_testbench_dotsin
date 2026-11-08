"""Keep the last N turns verbatim and fold older turns into one running summary."""
from agno.models.message import Message

from src.memory.base import MemoryStrategy, turn_messages


class RollingSummary(MemoryStrategy):
    name = "rolling_summary"

    def __init__(self, llm, working_turns: int, chunk_turns: int):
        self.llm = llm
        self.working_turns = working_turns
        self.chunk_turns = chunk_turns
        self.turns = []
        self.summary = ""

    def build_context(self, turn_index, user_message):
        recent = [message for turn in self.turns for message in turn_messages(turn)]
        if not self.summary:
            return recent
        return [Message(role="user", content=f"Summary of the earlier conversation:\n{self.summary}")] + recent

    def update(self, turn_index, user_message, assistant_reply, tool_outputs):
        self.turns.append({"user": user_message, "reply": assistant_reply, "tool_outputs": tool_outputs})
        older = self.turns[:-self.working_turns]
        if len(older) >= self.chunk_turns:
            self._fold(older)
            self.turns = self.turns[-self.working_turns:]

    def _fold(self, older: list[dict]) -> None:
        lines = [message.content for turn in older for message in turn_messages(turn)]
        previous = f"{self.summary}\n" if self.summary else ""
        self.summary = self.llm(
            "SUMMARIZE this into one running summary under 150 words. Keep names, dates, numbers and preferences. "
            "When a value changed, keep only the newest.\n" + previous + "\n".join(lines)
        )
