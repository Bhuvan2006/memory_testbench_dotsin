# Benchmark summary

Provider: `nvidia`. Model: `nvidia/nemotron-3-ultra-550b-a55b`. Runs per configuration: 2.

## Headlines

- Tokens per task: 546426 (full history) to 221122 (tiered memory), with recall accuracy 100% to 88%.
- Tiered memory used fewer total tokens than full history on this scenario.
- Starting context with 10 skills: 1331 tokens (eager) to 598 tokens (lazy).
- Task needing all 10 skills, total tokens: 2140 (eager) vs 5587 (lazy).

## Memory strategies (mean per run)

| Strategy | Input | Output | Total | Cost USD | Latency s | Recall % | Wrong | Leader | Calendar | Writer | Memory ops | Variance |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| full_history | 510646 | 35780 | 546426 | not measured | 1428.9 | 100 | 0.0 | 475154 | 22395 | 48876 | 0 | low |
| rolling_summary | 295452 | 40690 | 336142 | not measured | 1530.8 | 96 | 0.5 | 252738 | 18724 | 40916 | 23764 | low |
| tiered | 175686 | 45436 | 221122 | not measured | 1853.8 | 88 | 1.0 | 145578 | 29450 | 24350 | 21744 | low |

`Wrong` counts wrong or contradicted answers out of 12. Admitting ignorance is incorrect but not wrong. `Variance` is high when the standard deviation of total tokens is over 15% of the mean.

## Skill modes (mean per run)

| Mode | Starting context | Total tokens | Cost USD | Latency s | Skill loads |
|---|---|---|---|---|---|
| eager | 1331 | 1577 | not measured | 4.4 | 0.0 |
| lazy | 598 | 1651 | not measured | 28.4 | 1.0 |
| native | 1568 | 3660 | not measured | 11.8 | 1.0 |
| eager_all | 1453 | 2140 | not measured | 54.5 | 0.0 |
| lazy_all | 720 | 5587 | not measured | 56.7 | 10.5 |
| native_all | 1690 | 7041 | not measured | 44.7 | 10.0 |

## Limitations

One synthetic scenario, a small sample and keyword-match scoring. Results may differ on real data.
