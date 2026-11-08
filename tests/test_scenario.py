import json
from pathlib import Path

from data.generate_scenario import DUMP_TURNS, NEEDLES, build_scenario

SCEN = build_scenario(seed=7)


def test_forty_turns_numbered_1_to_40():
    assert [t["index"] for t in SCEN["turns"]] == list(range(1, 41))


def test_twelve_needles_in_turns_2_to_13():
    assert len(SCEN["needles"]) == 12
    assert all(2 <= n["turn"] <= 13 for n in SCEN["needles"])


def test_twelve_recall_questions_in_turns_29_to_40():
    assert sorted(r["turn"] for r in SCEN["recall"]) == list(range(29, 41))


def test_needle_keys_unique():
    keys = [n["key"] for n in SCEN["needles"]]
    assert len(keys) == len(set(keys))


def test_no_empty_turns():
    assert all(t["user"].strip() for t in SCEN["turns"])


def test_expected_answers_are_plain_substrings():
    for r in SCEN["recall"]:
        assert r["expected"] == r["expected"].strip() and "," not in r["expected"]


def test_budget_needle_is_updated_and_recall_expects_new_value():
    budget = next(n for n in SCEN["needles"] if n["key"] == "budget_cap")
    assert budget["update_turn"] == 20 and budget["new_value"] == "35k"
    assert next(t for t in SCEN["turns"] if t["index"] == 20)["user"].endswith("35k.")
    recall = next(r for r in SCEN["recall"] if r["needle_key"] == "budget_cap")
    assert recall["expected"] == "35" and recall["stale"] == "40"


def test_tool_outputs_only_on_dump_turns():
    assert tuple(t["index"] for t in SCEN["turns"] if t["tool_output"]) == DUMP_TURNS


def test_dumps_cannot_answer_recall_questions():
    dumps = "\n".join(t["tool_output"] for t in SCEN["turns"] if t["tool_output"])
    for needle in NEEDLES:
        if len(needle["value"]) > 1:
            assert needle["value"] not in dumps


def test_build_is_deterministic():
    assert build_scenario(seed=7) == build_scenario(seed=7)


def test_committed_json_matches_generator():
    committed = json.loads(Path("data/scenario.json").read_text(encoding="utf-8"))
    assert committed == build_scenario(seed=7)
