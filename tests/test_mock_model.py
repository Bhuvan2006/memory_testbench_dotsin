from agno.models.message import Message

from data.generate_scenario import build_scenario
from src.mock_model import TOOL_MARKER, UNKNOWN, MockModel, answer_from_context, extract_facts

SCEN = build_scenario(seed=7)
QUESTION = next(r for r in SCEN["recall"] if r["needle_key"] == "manager")
BUDGET_Q = next(r for r in SCEN["recall"] if r["needle_key"] == "budget_cap")


def test_answers_from_context_when_fact_present():
    fact = next(t["user"] for t in SCEN["turns"] if t["index"] == 2)
    assert QUESTION["expected"] in answer_from_context([fact], QUESTION["question"])


def test_missing_fact_returns_unknown():
    assert answer_from_context(["hello"], QUESTION["question"]) == UNKNOWN


def test_tool_output_does_not_answer():
    text = f"Noted.\n\n{TOOL_MARKER}\nmanager 1:1 with Priya Raman"
    assert answer_from_context([text], QUESTION["question"]) == UNKNOWN


def test_newest_value_wins_after_update():
    texts = ["The budget cap is 40k.", "Update from finance: the budget cap is now 35k."]
    assert answer_from_context(texts, BUDGET_Q["question"]) == "35k"


def test_stale_context_gives_stale_answer():
    assert answer_from_context(["The budget cap is 40k."], BUDGET_Q["question"]) == "40k"


def test_extract_facts_prefers_later_lines():
    text = "The budget cap is 40k.\nUpdate from finance: the budget cap is now 35k."
    assert extract_facts(text) == {"budget_cap": "35k"}


def test_usage_is_word_count():
    model = MockModel(label="writer")
    response = model.invoke([Message(role="user", content="one two three")], Message(role="assistant"))
    assert response.response_usage.input_tokens == 3
    assert response.content == "Noted."
