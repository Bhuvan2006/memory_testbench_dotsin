import pytest

from data.generate_scenario import build_scenario
from src.agents.team import build_team, run_turn
from src.memory.base import MemoryLLM
from src.memory.full_history import FullHistory
from src.memory.rolling_summary import RollingSummary
from src.memory.tiered.episodic import EpisodicMemory, fts_query
from src.memory.tiered.manager import TieredMemory, parse_consolidation
from src.memory.tiered.semantic import SemanticMemory
from src.memory.tiered.working import WorkingMemory
from src.metrics import Usage, load_yaml
from src.mock_model import MockModel

SETTINGS = load_yaml("settings.yaml")
CONFIG = SETTINGS["memory"]


def context_words(messages):
    return sum(len(str(m.content).split()) for m in messages)


def play(strategy, usage):
    system = build_team("mock", "mock", SETTINGS)
    scenario = build_scenario()
    replies = {t["index"]: run_turn(system, strategy, t["index"], t["user"], t["tool_output"], usage)
               for t in scenario["turns"]}
    return replies, scenario


def test_rolling_folds_old_turns_and_keeps_n():
    calls = []
    strategy = RollingSummary(lambda prompt: calls.append(prompt) or "SUMMARY", working_turns=2, chunk_turns=2)
    for i in range(1, 5):
        strategy.update(i, f"u{i}", f"r{i}", [])
    assert len(calls) == 1 and "u1" in calls[0] and "u2" in calls[0]
    assert [t["user"] for t in strategy.turns] == ["u3", "u4"]
    assert "SUMMARY" in strategy.build_context(5, "x")[0].content


def test_working_memory_trims_tool_output_and_caps_turns():
    working = WorkingMemory(turns=2, tool_trim_chars=10)
    for i in range(3):
        working.add(f"u{i}", "r", ["x" * 100])
    assert [t["user"] for t in working.turns] == ["u1", "u2"]
    assert "x" * 11 not in working.messages()[1].content


def test_semantic_newer_value_replaces_and_key_is_deduplicated():
    memory = SemanticMemory(token_cap=50)
    memory.upsert("Budget Cap", "40k", 5)
    memory.upsert("budget_cap", "35k", 20)
    assert memory.facts == {"budget_cap": {"value": "35k", "source_turn": 20}}


def test_semantic_older_value_cannot_overwrite():
    memory = SemanticMemory(token_cap=50)
    memory.upsert("budget", "35k", 20)
    memory.upsert("budget", "40k", 5)
    assert memory.facts["budget"]["value"] == "35k"


def test_profile_respects_token_cap_keeping_newest():
    memory = SemanticMemory(token_cap=5)
    memory.upsert("old", "one two three", 1)
    memory.upsert("new", "value", 2)
    assert memory.profile() == "new: value"


def test_episodic_retrieves_by_keyword():
    memory = EpisodicMemory(cap=5, decay=0.9)
    memory.add("The offsite is in Lisbon", 1.0, 1)
    memory.add("Calendar looked busy", 1.0, 2)
    assert memory.search("Which city is the offsite in?", 1) == ["The offsite is in Lisbon"]


@pytest.mark.parametrize("text", ['" OR (', "NEAR(a b)", "col:*", "'; DROP TABLE episodes; --"])
def test_episodic_query_cannot_inject_fts_syntax(text):
    memory = EpisodicMemory(cap=5, decay=0.9)
    memory.add("something", 1.0, 1)
    memory.search(text, 1)
    assert memory.count() == 1


def test_stopword_only_query_returns_nothing():
    assert fts_query("what is the") == ""
    memory = EpisodicMemory(cap=5, decay=0.9)
    assert memory.search("what is the", 3) == []


def test_eviction_removes_lowest_decayed_score():
    memory = EpisodicMemory(cap=2, decay=0.5)
    memory.add("old important", 3.0, 1)    # at turn 3: 3.0 * 0.25 = 0.75
    memory.add("old minor", 1.0, 2)        # at turn 3: 1.0 * 0.5 = 0.5, evicted
    memory.add("new", 1.0, 3)              # at turn 3: 1.0
    assert memory.count() == 2
    assert memory.search("minor", 1) == []
    assert memory.search("important", 1) == ["old important"]


def test_consolidation_parser_tolerates_prose_and_rejects_garbage():
    assert parse_consolidation('Sure! {"summary": "s", "facts": {"a": "b"}} done') == ("s", {"a": "b"})
    assert parse_consolidation("no json here") is None
    assert parse_consolidation('{"summary": "s", "facts": []}') is None


def test_bad_model_output_keeps_the_text_and_counts_a_failure():
    strategy = TieredMemory(lambda prompt: "not json", {**CONFIG, "chunk_turns": 1})
    strategy.update(1, "hello there", "ok", [])
    assert strategy.parse_failures == 1
    assert strategy.episodic.count() == 1


def test_chunk_larger_than_window_is_rejected():
    with pytest.raises(ValueError):
        TieredMemory(lambda prompt: "{}", {**CONFIG, "chunk_turns": 7, "working_turns": 6})


def test_tiered_end_to_end_keeps_new_budget_and_shrinks_context():
    usage = Usage()
    strategy = TieredMemory(MemoryLLM(MockModel(label="memory"), usage), CONFIG)
    replies, scenario = play(strategy, usage)
    assert strategy.semantic.facts["budget_cap"]["value"] == "35k"
    assert "memory_ops" in usage.per_agent
    assert strategy.episodic.count() <= CONFIG["episode_cap"]
    recall = next(r for r in scenario["recall"] if r["needle_key"] == "budget_cap")
    assert replies[recall["turn"]] == "35k"

    full = FullHistory()
    play(full, Usage())
    assert context_words(strategy.build_context(41, "x")) < context_words(full.build_context(41, "x"))
