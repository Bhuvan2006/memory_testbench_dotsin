import csv
import json

from bench.run_benchmark import main


def test_mock_benchmark_runs_end_to_end(tmp_path):
    main(["--provider", "mock", "--reps", "1", "--out", str(tmp_path)])
    with (tmp_path / "results.csv").open(encoding="utf-8") as handle:
        rows = {row["config"]: row for row in csv.DictReader(handle)}
    assert set(rows) == {"full_history", "rolling_summary", "tiered", "eager", "lazy", "native",
                         "eager_all", "lazy_all", "native_all"}
    assert int(rows["lazy_all"]["skill_tool_calls"]) == 10 and int(rows["native_all"]["skill_tool_calls"]) == 10
    logged = [json.loads(line) for line in (tmp_path / "replies.jsonl").open(encoding="utf-8")]
    assert sum(e["config"] == "tiered" and e["kind"] == "reply" for e in logged) == 40
    assert any(e["config"] == "rolling_summary" and e["kind"] == "summary" for e in logged)
    assert int(rows["tiered"]["total_tokens"]) < int(rows["full_history"]["total_tokens"])
    assert int(rows["full_history"]["recall_correct"]) == 12
    assert int(rows["tiered"]["memory_ops_tokens"]) > 0
    assert int(rows["lazy"]["starting_context_tokens"]) < int(rows["eager"]["starting_context_tokens"])
    assert int(rows["lazy"]["skill_tool_calls"]) == 1 and int(rows["native"]["skill_tool_calls"]) == 1
    summary = (tmp_path / "summary.md").read_text(encoding="utf-8")
    assert "Mock run" in summary
    assert (tmp_path / "memory_tokens.png").exists() and (tmp_path / "skills_context.png").exists()
