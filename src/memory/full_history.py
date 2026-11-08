"""Baseline: send the entire conversation every turn."""
from src.memory.base import MemoryStrategy, turn_messages


class FullHistory(MemoryStrategy):
    name = "full_history"

    def __init__(self):
        self.turns = []

    def build_context(self, turn_index, user_message):
        return [message for turn in self.turns for message in turn_messages(turn)]

    def update(self, turn_index, user_message, assistant_reply, tool_outputs):
        self.turns.append({"user": user_message, "reply": assistant_reply, "tool_outputs": tool_outputs})
