"""TieredMemory combines working, semantic and episodic memory behind one interface."""
import json

from agno.models.message import Message

from src.memory.base import MemoryStrategy
from src.memory.tiered.episodic import EpisodicMemory
from src.memory.tiered.semantic import SemanticMemory
from src.memory.tiered.working import WorkingMemory

TOOL_EPISODE_IMPORTANCE = 0.5  # calendar dumps are the most replaceable thing stored


def parse_consolidation(text: str) -> tuple[str, dict] | None:
    """Pull summary and facts from model output. Returns None if it is not valid."""
    try:
        data = json.loads(text[text.index("{"):text.rindex("}") + 1])
        summary, facts = data["summary"], data["facts"]
    except (ValueError, KeyError, TypeError):
        return None
    return (str(summary), facts) if isinstance(facts, dict) else None


class TieredMemory(MemoryStrategy):
    name = "tiered"

    def __init__(self, llm, config: dict):
        if config["chunk_turns"] > config["working_turns"]:
            raise ValueError("chunk_turns must be <= working_turns, or turns would leave working memory unconsolidated")
        self.llm = llm
        self.config = config
        self.working = WorkingMemory(config["working_turns"], config["tool_trim_chars"])
        self.semantic = SemanticMemory(config["profile_token_cap"])
        self.episodic = EpisodicMemory(config["episode_cap"], config["episode_decay"])
        self.chunk = []
        self.parse_failures = 0

    def build_context(self, turn_index, user_message):
        sections = []
        if profile := self.semantic.profile():
            sections.append(f"Known facts about the user:\n{profile}")
        if episodes := self.episodic.search(user_message, self.config["episodes_top_k"]):
            sections.append("Relevant past episodes:\n" + "\n---\n".join(episodes))
        notes = [Message(role="user", content="\n\n".join(sections))] if sections else []
        return notes + self.working.messages()

    def update(self, turn_index, user_message, assistant_reply, tool_outputs):
        self.working.add(user_message, assistant_reply, tool_outputs)
        for output in tool_outputs:
            if len(output) > self.config["tool_trim_chars"]:
                summary = self.llm(f"SUMMARIZE this calendar tool output in two sentences.\n{output}")
                self.episodic.add(summary, TOOL_EPISODE_IMPORTANCE, turn_index)
        self.chunk.append(f"User: {user_message}\nAssistant: {assistant_reply}")
        if len(self.chunk) >= self.config["chunk_turns"]:
            self._consolidate(turn_index)

    def _consolidate(self, turn_index: int) -> None:
        keys = ", ".join(self.semantic.facts) or "none"
        reply = self.llm(
            'CONSOLIDATE the conversation below. Return only JSON: {"summary": "under 60 words", "facts": {"key": "value"}}. '
            "Facts are durable details the user stated (names, dates, numbers, preferences); use the newest value. "
            f"Reuse an existing key when it is the same fact. Existing keys: {keys}.\n" + "\n".join(self.chunk)
        )
        self.chunk = []
        parsed = parse_consolidation(reply)
        if parsed is None:
            self.parse_failures += 1
            self.episodic.add(reply, 1.0, turn_index)  # keep the text so the chunk is not lost
            return
        summary, facts = parsed
        for key, value in facts.items():
            # shortcut: source turn is the end of the chunk, per-turn attribution would need a bigger prompt.
            self.semantic.upsert(key, str(value), turn_index)
        self.episodic.add(summary, 1.0 + 0.5 * min(len(facts), 4), turn_index)
