"""Semantic memory: durable facts as key-value entries, newest value wins."""
import re

TOKENS_PER_WORD = 1.3  # used only to cap the profile size, never reported as usage


def normalise_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", key.lower()).strip("_")


class SemanticMemory:
    def __init__(self, token_cap: int):
        self.token_cap = token_cap
        self.facts = {}

    def upsert(self, key: str, value: str, source_turn: int) -> None:
        key = normalise_key(key)
        existing = self.facts.get(key)
        if key and (existing is None or source_turn >= existing["source_turn"]):
            self.facts[key] = {"value": value, "source_turn": source_turn}

    def profile(self) -> str:
        """Render facts newest first, stopping at the token cap."""
        lines, used = [], 0
        for key, fact in sorted(self.facts.items(), key=lambda item: -item[1]["source_turn"]):
            line = f"{key}: {fact['value']}"
            cost = len(line.split()) * TOKENS_PER_WORD
            if used + cost > self.token_cap:
                break
            lines.append(line)
            used += cost
        return "\n".join(lines)
