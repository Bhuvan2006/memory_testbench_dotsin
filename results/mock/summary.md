# Benchmark summary

Provider: `mock`. Model: `mock`. Runs per configuration: 3.

**Mock run: token counts are word counts from a fake model. These numbers only prove the pipeline works. Do not quote them.**

## Headlines

- Tokens per task: 280738 (full history) to 62538 (tiered memory), with recall accuracy 100% to 100%.
- Tiered memory used fewer total tokens than full history on this scenario.
- Starting context with 10 skills: 1009 tokens (eager) to 242 tokens (lazy).
- Task needing all 10 skills, total tokens: 1089 (eager) vs 9250 (lazy).

## Memory strategies (mean per run)

| Strategy | Input | Output | Total | Cost USD | Latency s | Recall % | Wrong | Leader | Calendar | Writer | Memory ops | Variance |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| full_history | 279961 | 777 | 280738 | 0.0000 | 1.1 | 100 | 0.0 | 193901 | 4069 | 82768 | 0 | low |
| rolling_summary | 150092 | 1525 | 151617 | 0.0000 | 0.9 | 0 | 0.0 | 103286 | 4069 | 38864 | 5398 | low |
| tiered | 61330 | 1208 | 62538 | 0.0000 | 0.8 | 100 | 0.0 | 43339 | 4069 | 10073 | 5057 | low |

`Wrong` counts wrong or contradicted answers out of 12. Admitting ignorance is incorrect but not wrong. `Variance` is high when the standard deviation of total tokens is over 15% of the mean.

## Skill modes (mean per run)

| Mode | Starting context | Total tokens | Cost USD | Latency s | Skill loads |
|---|---|---|---|---|---|
| eager | 1009 | 1016 | 0.0000 | 0.0 | 0.0 |
| lazy | 242 | 609 | 0.0000 | 0.0 | 1.0 |
| native | 440 | 1023 | 0.0000 | 0.0 | 1.0 |
| eager_all | 1082 | 1089 | 0.0000 | 0.0 | 0.0 |
| lazy_all | 315 | 9250 | 0.0000 | 0.0 | 10.0 |
| native_all | 513 | 12219 | 0.0000 | 0.0 | 10.0 |

## Limitations

One synthetic scenario, a small sample and keyword-match scoring. Results may differ on real data.
