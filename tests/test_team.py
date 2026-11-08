import pytest
from agno.exceptions import ModelRateLimitError

from data.generate_scenario import build_scenario
from src.agents.team import build_team, run_turn
from src.memory.full_history import FullHistory
from src.metrics import BudgetExceeded, SpendGuard, Usage, cost_usd, load_yaml, model_price, score_answer
from src.mock_model import MockModel

SETTINGS = load_yaml("settings.yaml")
SCEN = build_scenario()


def run(turn_indexes):
    system, strategy, usage = build_team("mock", "mock", SETTINGS), FullHistory(), Usage()
    replies = {}
    for turn in SCEN["turns"]:
        if turn["index"] in turn_indexes:
            replies[turn["index"]] = run_turn(system, strategy, turn["index"], turn["user"], turn["tool_output"], usage)
    return replies, strategy, usage


def test_writer_recalls_a_fact_through_the_team():
    replies, _, _ = run({2, 29})
    assert "Priya" in replies[29]


def test_tool_output_reaches_memory_and_tokens_are_per_agent():
    _, strategy, usage = run({14})
    assert "event 59" in strategy.turns[0]["tool_outputs"][0]
    assert set(usage.per_agent) == {"leader", "calendar_agent", "writer"}


def test_context_changes_between_turns():
    _, strategy, _ = run({1, 3})
    assert len(strategy.build_context(4, "x")) == 4


def test_failed_member_fails_the_turn_and_records_nothing(monkeypatch):
    real_invoke = MockModel.invoke

    def invoke(self, *args, **kwargs):
        if self.label == "writer":
            raise ModelRateLimitError("429 simulated", model_name="mock")
        return real_invoke(self, *args, **kwargs)

    monkeypatch.setattr(MockModel, "invoke", invoke)
    strategy = FullHistory()
    with pytest.raises(RuntimeError, match="writer failed on turn 2: 429 simulated"):
        run_turn(build_team("mock", "mock", load_yaml("settings.yaml")), strategy, 2, "hello", None, Usage())
    assert strategy.build_context(3, "next") == []


def test_scoring():
    assert score_answer("It is 35k now", "35", "40") == (True, False)
    assert score_answer("It is 40k", "35", "40") == (False, True)
    assert score_answer("I do not know.", "35", "40") == (False, False)
    assert score_answer("About 135", "35", "40") == (False, True)
    assert score_answer("Lunch is at 1 PM", "1pm") == (True, False)
    assert score_answer("8,000 steps", "8000") == (True, False)
    for reply in ("At 1:00 pm", "At 1:00 pm", "At **1:00 PM**", "At 13:00"):
        assert score_answer(reply, "1pm") == (True, False)
    assert score_answer("By 22:30", "10:30") == (True, False)
    assert score_answer("At 09:45", "9:45") == (True, False)
    assert score_answer("At 2:00 pm", "1pm") == (False, True)
    assert score_answer("Only 1:00 PM on Tuesday. I don't have a regular daily lunch time recorded.", "1pm") == (False, False)
    assert score_answer("We meet at 19:00", "7") == (False, True)  # time rewriting only applies to time answers
    assert score_answer("It is $35,000", "35", "40") == (True, False)
    assert score_answer("It is $40,000", "35", "40") == (False, True)
    for reply in ("I don’t have that", "I couldn't find it", "That was not provided", "I am unable to say"):
        assert score_answer(reply, "35", "40") == (False, False)


def test_unknown_paid_model_has_no_price():
    with pytest.raises(ValueError):
        model_price("anthropic", "not-a-model", load_yaml("prices.yaml"))


def test_spend_guard_aborts_including_finished_runs():
    usage = Usage()
    usage.per_agent["writer"] = {"input": 1_000_000, "output": 0}
    price = {"input_per_mtok": 1.0, "output_per_mtok": 1.0}
    assert cost_usd(usage, price) == 1.0
    guard = SpendGuard(1.5, price)
    guard.check(usage)
    guard.finish_run(usage)
    with pytest.raises(BudgetExceeded):
        guard.check(usage)
