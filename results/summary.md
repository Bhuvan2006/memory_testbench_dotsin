# Benchmark summary

Provider: `nvidia`. Model: `nvidia/nemotron-3-ultra-550b-a55b`. Runs per configuration: 1.

## Headlines

- Tokens per task: 437448 (full history) to 226637 (tiered memory), with recall accuracy 100% to 92%.
- Tiered memory used fewer total tokens than full history on this scenario.
- Starting context with 10 skills: 1331 tokens (eager) to 598 tokens (lazy).
- Task needing all 10 skills, total tokens: 2266 (eager) vs 4225 (lazy).

## Memory strategies (mean per run)

| Strategy | Input | Output | Total | Cost USD | Latency s | Recall % | Wrong | Leader | Calendar | Writer | Memory ops | Variance |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| full_history | 414976 | 22472 | 437448 | not measured | 516.0 | 100 | 0.0 | 391122 | 16674 | 29652 | 0 | low |
| rolling_summary | 211057 | 31380 | 242437 | not measured | 670.6 | 100 | 0.0 | 179853 | 18793 | 27558 | 16233 | low |
| tiered | 188703 | 37934 | 226637 | not measured | 728.3 | 92 | 0.0 | 155546 | 18138 | 33808 | 19145 | low |

`Wrong` counts wrong or contradicted answers out of 12. Admitting ignorance is incorrect but not wrong. `Variance` is high when the standard deviation of total tokens is over 15% of the mean.

## Skill modes (mean per run)

| Mode | Starting context | Total tokens | Cost USD | Latency s | Skill loads |
|---|---|---|---|---|---|
| eager | 1331 | 1585 | not measured | 4.2 | 0.0 |
| lazy | 598 | 1635 | not measured | 5.0 | 1.0 |
| native | 1568 | 3689 | not measured | 9.8 | 1.0 |
| eager_all | 1453 | 2266 | not measured | 13.6 | 0.0 |
| lazy_all | 720 | 4225 | not measured | 21.0 | 10.0 |
| native_all | 1690 | 7215 | not measured | 26.2 | 10.0 |

## Limitations

One synthetic scenario, a small sample and keyword-match scoring. Results may differ on real data.
