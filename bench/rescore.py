"""Re-apply the current scorer to saved replies. No model calls. Example: python bench/rescore.py results"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from bench.report import write_report  # noqa: E402
from data.generate_scenario import build_scenario  # noqa: E402
from src.metrics import score_answer  # noqa: E402

SCORE_COLUMNS = ["config", "rep", "turn", "correct", "wrong"]


def rescore(out_dir: Path) -> list[dict]:
    originals_path = out_dir / "original_scores.csv"
    if originals_path.exists():  # a second run would replace the originals with already-fixed scores
        raise FileExistsError(f"{originals_path} already exists, so these results were already rescored")
    recall = {r["turn"]: r for r in build_scenario()["recall"]}
    replies_path, results_path = out_dir / "replies.jsonl", out_dir / "results.csv"
    entries = [json.loads(line) for line in replies_path.open(encoding="utf-8")]
    scored = [e for e in entries if "correct" in e]
    originals = [{column: e[column] for column in SCORE_COLUMNS} for e in scored]

    changes = []
    for entry in scored:
        question = recall[entry["turn"]]
        correct, wrong = score_answer(entry["text"], question["expected"], question["stale"])
        if (correct, wrong) != (entry["correct"], entry["wrong"]):
            changes.append({"config": entry["config"], "rep": entry["rep"], "turn": entry["turn"], "question": entry["user"],
                            "answer": entry["text"], "old_correct": entry["correct"], "new_correct": correct,
                            "old_wrong": entry["wrong"], "new_wrong": wrong})
        entry["correct"], entry["wrong"] = correct, wrong

    with results_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        mine = [e for e in scored if e["config"] == row["config"] and str(e["rep"]) == row["rep"]]
        if row["kind"] == "memory":
            row["recall_correct"], row["wrong"] = sum(e["correct"] for e in mine), sum(e["wrong"] for e in mine)

    # Originals first, so a failure below cannot lose them.
    _write_csv(originals_path, SCORE_COLUMNS, originals)
    _write_csv(out_dir / "score_changes.csv", list(changes[0]) if changes else ["config"], changes)
    _write_csv(results_path, list(rows[0]), rows)
    with replies_path.open("w", encoding="utf-8") as handle:
        handle.writelines(json.dumps(e, ensure_ascii=False) + "\n" for e in entries)
    write_report(out_dir)
    return changes


def _write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    for change in rescore(Path(sys.argv[1])):
        print(change)
