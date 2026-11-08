"""Token accounting, cost, the spend guard and recall scoring."""
import re
from pathlib import Path

import yaml

CONFIG_DIR = Path(__file__).parent.parent / "config"
FREE_PROVIDERS = ("mock", "ollama")
UNKNOWN_PHRASES = ("do not know", "don't know", "don't have", "do not have", "not sure", "no information", "cannot find",
                   "can't find", "couldn't find", "could not find", "not mentioned", "not provided", "unable to")


def load_yaml(name: str) -> dict:
    return yaml.safe_load((CONFIG_DIR / name).read_text(encoding="utf-8"))


class BudgetExceeded(RuntimeError):
    pass


class Usage:
    """Input and output tokens per agent, taken from provider usage metrics."""

    def __init__(self):
        self.per_agent = {}

    def add(self, agent: str, metrics) -> None:
        tokens = self.per_agent.setdefault(agent, {"input": 0, "output": 0})
        tokens["input"] += metrics.input_tokens or 0
        tokens["output"] += metrics.output_tokens or 0

    @property
    def input_tokens(self) -> int:
        return sum(t["input"] for t in self.per_agent.values())

    @property
    def output_tokens(self) -> int:
        return sum(t["output"] for t in self.per_agent.values())

    def agent_total(self, agent: str) -> int:
        tokens = self.per_agent.get(agent, {"input": 0, "output": 0})
        return tokens["input"] + tokens["output"]


def model_price(provider: str, model_id: str, prices: dict) -> dict:
    if provider in FREE_PROVIDERS:
        return {"input_per_mtok": 0.0, "output_per_mtok": 0.0}
    if model_id not in prices:
        raise ValueError(f"No price for {model_id} in config/prices.yaml, so the spend guard cannot work")
    return prices[model_id]


def cost_usd(usage: Usage, price: dict) -> float:
    return (usage.input_tokens * price["input_per_mtok"] + usage.output_tokens * price["output_per_mtok"]) / 1_000_000


class SpendGuard:
    """Aborts the benchmark once finished runs plus the current run exceed the limit."""

    def __init__(self, max_cost_usd: float, price: dict):
        self.max_cost_usd = max_cost_usd
        self.price = price
        self.finished_cost = 0.0

    def check(self, usage: Usage) -> None:
        spent = self.finished_cost + cost_usd(usage, self.price)
        if spent > self.max_cost_usd:
            raise BudgetExceeded(f"Estimated spend ${spent:.4f} exceeds MAX_COST_USD ${self.max_cost_usd:.2f}")

    def finish_run(self, usage: Usage) -> None:
        self.finished_cost += cost_usd(usage, self.price)


def _contains(text: str, value: str) -> bool:
    # The optional 000 lets "35" (from 35k) also match "35000", which is "$35,000" after commas are removed.
    return re.search(rf"(?<!\d){re.escape(value.lower())}(?:000)?(?!\d)", text) is not None


def score_answer(answer: str, expected: str, stale: str | None = None) -> tuple[bool, bool]:
    """Return (correct, wrong_or_contradicted). Admitting ignorance is incorrect but not wrong."""
    text = re.sub(r"(\d)\s+(am|pm)\b", r"\1\2", (answer or "").lower().replace(",", "").replace("’", "'"))
    correct = _contains(text, expected)
    if correct:
        return True, False
    if stale and _contains(text, stale):
        return False, True
    return False, not any(phrase in text for phrase in UNKNOWN_PHRASES)
