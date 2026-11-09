# Memory-tiered multi-agent orchestration with a skill harness

A measured comparison of memory strategies in an Agno multi-agent team, and of eager versus lazy skill loading. All data is synthetic. This is an independent demo with no connection to any company's internal models or user data.

**Agno version: 3.1.12**, pinned in `requirements.txt`. Tested on Python 3.13.

## 60-second quickstart

```bash
uv venv .venv --python 3.13
```

```bash
uv pip install --python .venv/Scripts/python.exe -r requirements.txt
```

```bash
.venv/Scripts/python.exe -m pytest
```

```bash
.venv/Scripts/python.exe bench/run_benchmark.py --provider mock
```

The mock run is free and offline, and writes to `results/mock/`. Those numbers only prove the pipeline works.

## Real runs

Local and free, using a model you have pulled in Ollama:

```bash
.venv/Scripts/python.exe bench/run_benchmark.py --provider ollama
```

Paid, after copying `.env.example` to `.env` and adding `ANTHROPIC_API_KEY`:

```bash
.venv/Scripts/python.exe bench/run_benchmark.py --provider anthropic
```

Hosted on NVIDIA, tokens only, after adding `NVIDIA_API_KEY` to `.env`. Requests are paced to 30 per minute and retried with backoff. Cost is reported as not measured and `max_cost_usd` does not apply, so `cost_usd` in the CSV is a placeholder 0:

```bash
.venv/Scripts/python.exe bench/run_benchmark.py --provider nvidia
```

All of them write `results/results.csv`, `results/summary.md` and two charts. The run overwrites earlier files in `results/`. The default paid model is `claude-haiku-5-5`. The run aborts if estimated spend exceeds `max_cost_usd` in `config/settings.yaml`.

`MODEL_PROVIDER` and `MODEL_ID` can also be set in `.env`.

## Results

Model: `nvidia/nemotron-3-ultra-550b-a55b` (`nemotron-3-ultra`). These numbers come from `results/run_b`: **2 runs per configuration**, made with `--reps 2 --out results/run_b`. Tokens only: cost was not measured.

| Memory strategy, 40 turns | Total tokens, run 1 | Total tokens, run 2 | Mean of 2 | Mean versus full history | Recall, run 1 / run 2 | Wrong, run 1 / run 2 |
|---|---|---|---|---|---|---|
| `FullHistory` | 529,278 | 563,573 | 546,426 | n/a | 12/12, 12/12 | 0, 0 |
| `RollingSummary` | 367,491 | 304,793 | 336,142 | -38.5% | 12/12, 11/12 | 0, 1 |
| `TieredMemory` | 215,998 | 226,245 | 221,122 | -59.5% | 10/12, 11/12 | 1, 1 |

Totals include the tokens spent on summarising (`memory_ops`). Recall differed between the two runs: `TieredMemory` scored 10 of 12 and then 11 of 12. `TieredMemory` used the fewest tokens on average and had the lowest mean recall, 10.5 of 12.

"Variance low" in `results/run_b/summary.md` refers to total tokens only. It says nothing about recall. With 2 runs, it is only a rough indication of spread.

| Skill mode | Starting context | Mean total tokens, 1-skill task | Mean total tokens, all-10 task |
|---|---|---|---|
| Eager | 1,331 | 1,577 | 2,140 |
| Lazy | 598 | 1,651 | 5,587 |
| Agno native | 1,568 | 3,660 | 7,041 |

Lazy loading more than halved starting context, but it saved no total tokens on the 1-skill task and cost more when all 10 skills were needed. The lazy all-10 task varied widely, at 4,111 and 7,063 tokens. Full numbers are in `results/run_b/summary.md`.

The first run, 1 repetition per configuration, is kept in `results/` as an earlier run. It is not averaged with these numbers. In it, `TieredMemory` used 226,637 tokens and scored 11/12 after the rescore described in [Limitations](#limitations), with 0 wrong. Latency is not comparable across the two runs, because the earlier run was paced at 38 requests per minute and `results/run_b` at 30 with longer rate-limit waits.

## What is compared

| Memory strategy | Sends each turn |
|---|---|
| `FullHistory` | The whole conversation |
| `RollingSummary` | Last 6 turns plus one running summary |
| `TieredMemory` | Last 6 turns with trimmed tool output, a capped fact profile, and the top 3 relevant episodes |

Skills are compared in three modes: eager, a hand-written lazy loader, and Agno's native skills.

## Layout

- `src/agents/`: the Team, members and tools
- `src/memory/`: the strategy interface and three strategies
- `src/skills/`: lazy loader and linter
- `src/mock_model.py`, `src/metrics.py`: offline model, tokens, cost, scoring
- `bench/`: benchmark runner and report
- `docs/`: [design](docs/HLD.md), [git history](docs/GIT_DIAGRAM.md), [explanations and interview answers](docs/EXPLAIN.md)

Check skills with `python -m src.skills.lint`.

## Limitations

- One synthetic scenario and a small sample of 2 runs per configuration.
- Scoring is keyword matching on 12 facts, and it does not judge overall reply quality.
- Keyword retrieval misses synonyms, and fact keys are chosen by the model.
- **Prompt caching is not used or measured.** Totals count every input token at full price. Provider prompt caching can make a stable prompt, such as eager skills or an append-only full history, much cheaper than its raw token count suggests, so real cost gaps may be smaller than these token gaps.
- Lazy loading only helps when a task needs few skills. The `_all` rows show the case where a task needs all 10, and each load also adds a model round trip.
- Small local models may not make real tool calls. In a check on `qwen2.5-coder:3b` (2 turns), the leader wrote the delegation as plain JSON text, so no member ran. Ollama rows with zero calendar and writer tokens do not measure a multi-agent system and should not be quoted as such.
- NVIDIA runs report tokens, not money. Output tokens may include the model's reasoning, which would inflate them.
- **The scorer was fixed after the first NVIDIA run.** Time-format matching was too strict: correct answers such as "1:00 pm" and "22:30" were marked wrong. Only time matching changed, an answer that says it lacks the fact gains nothing from it, and all strategies were rescored from the saved replies with no new model calls. Two answers changed, moving recall from 11/12 to 12/12 for `RollingSummary` and from 10/12 to 11/12 for `TieredMemory`. The scorer change was made after seeing those results. The first scores are in `results/original_scores.csv`, and each change is in `results/score_changes.csv`. `results/run_b` used the fixed scorer from the start and was not rescored.
- Every reply and summary is saved to `replies.jsonl` next to `results.csv`, so scores can be audited.
- Results may differ on real data and on other models. See `results/run_b/summary.md` for which model produced the current numbers.
