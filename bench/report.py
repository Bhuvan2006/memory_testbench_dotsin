"""Turn results.csv into summary.md and charts."""
import csv
from pathlib import Path
from statistics import mean, pstdev

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HIGH_VARIANCE = 0.15  # coefficient of variation above which a mean is flagged
MEMORY_ORDER = ["full_history", "rolling_summary", "tiered"]
SKILL_ORDER = ["eager", "lazy", "native", "eager_all", "lazy_all", "native_all"]  # _all: task needs all 10 skills


def _load(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _avg(rows: list[dict], column: str) -> float:
    return mean(float(row[column]) for row in rows)


def _high_variance(rows: list[dict], column: str) -> bool:
    values = [float(row[column]) for row in rows]
    average = mean(values)
    return average > 0 and pstdev(values) / average > HIGH_VARIANCE


def _group(rows: list[dict], kind: str, order: list[str]) -> dict:
    return {name: [r for r in rows if r["kind"] == kind and r["config"] == name] for name in order}


def _memory_table(groups: dict) -> list[str]:
    lines = ["| Strategy | Input | Output | Total | Cost USD | Latency s | Recall % | Wrong | Leader | Calendar | Writer | Memory ops | Variance |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for name, rows in groups.items():
        flag = "high" if _high_variance(rows, "total_tokens") else "low"
        lines.append(f"| {name} | {_avg(rows, 'input_tokens'):.0f} | {_avg(rows, 'output_tokens'):.0f} | "
                     f"{_avg(rows, 'total_tokens'):.0f} | {_avg(rows, 'cost_usd'):.4f} | {_avg(rows, 'latency_s'):.1f} | "
                     f"{_avg(rows, 'recall_correct') / 12 * 100:.0f} | {_avg(rows, 'wrong'):.1f} | "
                     f"{_avg(rows, 'leader_tokens'):.0f} | {_avg(rows, 'calendar_tokens'):.0f} | "
                     f"{_avg(rows, 'writer_tokens'):.0f} | {_avg(rows, 'memory_ops_tokens'):.0f} | {flag} |")
    return lines


def _skills_table(groups: dict) -> list[str]:
    lines = ["| Mode | Starting context | Total tokens | Cost USD | Latency s | Skill loads |", "|---|---|---|---|---|---|"]
    for name, rows in groups.items():
        lines.append(f"| {name} | {_avg(rows, 'starting_context_tokens'):.0f} | {_avg(rows, 'total_tokens'):.0f} | "
                     f"{_avg(rows, 'cost_usd'):.4f} | {_avg(rows, 'latency_s'):.1f} | "
                     f"{_avg(rows, 'skill_tool_calls'):.1f} |")
    return lines


def _bar(path: Path, title: str, ylabel: str, values: dict) -> None:
    figure, axis = plt.subplots(figsize=(6, 4))
    bars = axis.bar(list(values), list(values.values()), color="#3b6ea5")
    axis.bar_label(bars, fmt="%.0f")
    axis.set_title(title)
    axis.set_ylabel(ylabel)
    axis.spines[["top", "right"]].set_visible(False)
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def write_report(out_dir: Path) -> None:
    rows = _load(out_dir / "results.csv")
    memory, skills = _group(rows, "memory", MEMORY_ORDER), _group(rows, "skills", SKILL_ORDER)
    provider, model = rows[0]["provider"], rows[0]["model"]
    full, tiered = memory["full_history"], memory["tiered"]
    full_total, tiered_total = _avg(full, "total_tokens"), _avg(tiered, "total_tokens")
    verdict = "used fewer" if tiered_total < full_total else "did NOT use fewer"
    lines = ["# Benchmark summary", "", f"Provider: `{provider}`. Model: `{model}`. Runs per configuration: {len(full)}.", ""]
    if provider == "mock":
        lines += ["**Mock run: token counts are word counts from a fake model. These numbers only prove the pipeline works. Do not quote them.**", ""]
    lines += [
        "## Headlines", "",
        f"- Tokens per task: {full_total:.0f} (full history) to {tiered_total:.0f} (tiered memory), "
        f"with recall accuracy {_avg(full, 'recall_correct') / 12 * 100:.0f}% to {_avg(tiered, 'recall_correct') / 12 * 100:.0f}%.",
        f"- Tiered memory {verdict} total tokens than full history on this scenario.",
        f"- Starting context with 10 skills: {_avg(skills['eager'], 'starting_context_tokens'):.0f} tokens (eager) to "
        f"{_avg(skills['lazy'], 'starting_context_tokens'):.0f} tokens (lazy).",
        f"- Task needing all 10 skills, total tokens: {_avg(skills['eager_all'], 'total_tokens'):.0f} (eager) vs "
        f"{_avg(skills['lazy_all'], 'total_tokens'):.0f} (lazy).", "",
        "## Memory strategies (mean per run)", "", *_memory_table(memory), "",
        "`Wrong` counts wrong or contradicted answers out of 12. Admitting ignorance is incorrect but not wrong. "
        f"`Variance` is high when the standard deviation of total tokens is over {HIGH_VARIANCE:.0%} of the mean.", "",
        "## Skill modes (mean per run)", "", *_skills_table(skills), "",
        "## Limitations", "",
        "One synthetic scenario, a small sample and keyword-match scoring. Results may differ on real data.", "",
    ]
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    _bar(out_dir / "memory_tokens.png", "Total tokens per 40-turn run", "tokens",
         {name: _avg(group, "total_tokens") for name, group in memory.items()})
    _bar(out_dir / "skills_context.png", "Starting context with 10 skills", "tokens",
         {name: _avg(skills[name], "starting_context_tokens") for name in SKILL_ORDER[:3]})
