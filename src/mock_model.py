"""Deterministic offline model, so tests and the mock benchmark are free.

It only knows what is in the context it receives. Token counts are word counts,
so mock numbers prove the pipeline works and must never be presented as results.
"""
import json
import re
from dataclasses import dataclass

from agno.metrics import MessageMetrics
from agno.models.base import Model
from agno.models.response import ModelResponse

from data.generate_scenario import NEEDLES

TOOL_MARKER = "[Tool output]"  # memory strategies put tool dumps after this marker
SUMMARY_WORD_CAP = 120
UNKNOWN = "I do not know."


def _has_value(line: str, value: str) -> bool:
    return re.search(rf"(?<!\d){re.escape(value)}(?!\d)", line) is not None


def answer_from_context(texts: list[str], question: str) -> str:
    """Answer a known question from the newest matching line, or admit not knowing."""
    needle = next((n for n in NEEDLES if n["question"] == question.strip()), None)
    if needle is None:
        return UNKNOWN
    for text in reversed(texts):
        for line in reversed(text.split(TOOL_MARKER)[0].splitlines()):
            if any(anchor in line for anchor in needle["anchors"]):
                for value in filter(None, (needle.get("new_value"), needle["value"])):
                    if _has_value(line, value):
                        return value
    return UNKNOWN


def extract_facts(text: str) -> dict:
    """Find planted facts in free text. Later lines overwrite earlier ones."""
    facts = {}
    for line in text.splitlines():
        for needle in NEEDLES:
            if any(anchor in line for anchor in needle["anchors"]):
                for value in filter(None, (needle.get("new_value"), needle["value"])):
                    if _has_value(line, value):
                        facts[needle["key"]] = value
                        break
    return facts


def summarise(text: str) -> str:
    """shortcut: keeps the newest words only, real models summarise by meaning."""
    lines = [line for line in text.splitlines() if line.strip() and not line.startswith("event ")]
    words = "\n".join(lines).split(" ")
    return " ".join(words[-SUMMARY_WORD_CAP:])


@dataclass
class MockModel(Model):
    id: str = "mock"
    name: str = "Mock"
    provider: str = "Mock"
    label: str = "writer"  # leader, calendar, writer, memory or skills

    def _decide(self, messages, tools) -> str | dict:
        last_user = max(i for i, m in enumerate(messages) if m.role == "user")
        current = str(messages[last_user].content)
        results = [str(m.content) for m in messages[last_user + 1:] if m.role == "tool"]
        if self.label == "leader":
            wants_calendar = "calendar" in current.lower()
            if wants_calendar and not results:
                return {"name": "delegate_task_to_member", "args": {"member_id": "calendar", "task": current}}
            if len(results) < (2 if wants_calendar else 1):
                return {"name": "delegate_task_to_member", "args": {"member_id": "writer", "task": current}}
            return results[-1]
        if self.label == "calendar":
            return f"The calendar has {results[0].count('event')} events." if results else {"name": "read_calendar", "args": {}}
        if self.label == "writer":
            context = [str(m.content) for m in messages[:last_user] if m.role in ("user", "assistant")]
            if any(n["question"] == current.strip() for n in NEEDLES):
                return answer_from_context(context, current)
            return "Noted."
        if self.label == "memory":
            body = current.split("\n", 1)[-1]
            if current.startswith("CONSOLIDATE"):
                return json.dumps({"summary": summarise(body), "facts": extract_facts(body)})
            return summarise(body)
        names = [t.get("function", t).get("name") for t in (tools or [])]
        loader = next((n for n in names if n in ("load_skill", "get_skill_instructions")), None)
        if loader and not results:
            key = "name" if loader == "load_skill" else "skill_name"
            return {"name": loader, "args": {key: "meeting-notes"}}
        return "Summary, decisions and action items are ready."

    def invoke(self, messages, assistant_message, response_format=None, tools=None, tool_choice=None,
               run_response=None, compress_tool_results=False, **kwargs):
        step = self._decide(messages, tools)
        input_tokens = sum(len(str(m.content).split()) for m in messages)
        output_tokens = len(str(step).split())
        response = ModelResponse(role="assistant", response_usage=MessageMetrics(
            input_tokens=input_tokens, output_tokens=output_tokens, total_tokens=input_tokens + output_tokens))
        if isinstance(step, dict):
            response.content = ""
            response.tool_calls = [{"id": f"call_{len(messages)}", "type": "function",
                                    "function": {"name": step["name"], "arguments": json.dumps(step["args"])}}]
        else:
            response.content = step
        return response

    def ainvoke(self, *args, **kwargs):
        raise NotImplementedError("the benchmark is synchronous")

    def invoke_stream(self, *args, **kwargs):
        raise NotImplementedError("the benchmark does not stream")

    def ainvoke_stream(self, *args, **kwargs):
        raise NotImplementedError("the benchmark does not stream")

    def _parse_provider_response(self, response, **kwargs):
        return response

    def _parse_provider_response_delta(self, response):
        return response
