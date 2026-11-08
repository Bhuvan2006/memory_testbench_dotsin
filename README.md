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

Both write `results/results.csv`, `results/summary.md` and two charts. The run overwrites earlier files in `results/`. The default paid model is `claude-haiku-5-5`. The run aborts if estimated spend exceeds `max_cost_usd` in `config/settings.yaml`.

`MODEL_PROVIDER` and `MODEL_ID` can also be set in `.env`.

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

- One synthetic scenario and a small sample of 3 runs per configuration.
- Scoring is keyword matching on 12 facts, and it does not judge overall reply quality.
- Keyword retrieval misses synonyms, and fact keys are chosen by the model.
- **Prompt caching is not used or measured.** Totals count every input token at full price. Provider prompt caching can make a stable prompt, such as eager skills or an append-only full history, much cheaper than its raw token count suggests, so real cost gaps may be smaller than these token gaps.
- Lazy loading only helps when a task needs few skills. The `_all` rows show the case where a task needs all 10, and each load also adds a model round trip.
- Small local models may not make real tool calls. In a check on `qwen2.5-coder:3b` (2 turns), the leader wrote the delegation as plain JSON text, so no member ran. Ollama rows with zero calendar and writer tokens do not measure a multi-agent system and should not be quoted as such.
- Every reply and summary is saved to `replies.jsonl` next to `results.csv`, so scores can be audited.
- Results may differ on real data and on other models. See `results/summary.md` for which model produced the current numbers.
