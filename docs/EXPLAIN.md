# Project explanation

Plain-language notes for each milestone: what it does, why it is built that way, and the trade-offs.

## Scenario and mock model

**What it does.** `data/generate_scenario.py` writes a seeded 40-turn conversation about a fictional person, Rowan. Twelve facts are planted in turns 2-13, and twelve recall questions are asked in turns 29-40. Four turns carry a large fake calendar dump. `src/mock_model.py` is a fake Agno model that can only answer from the messages it receives.

**Why this design.** A seed means every memory strategy faces the same conversation. The expected answers are short strings, so scoring needs no judge model. One fact, the budget cap, changes at turn 20. That tests whether a strategy keeps the newest value instead of the first one.

**Differences from the brief.** Turns 2-12 and 30-40 are each 11 slots for 12 items, so needles run to turn 13 and recall starts at turn 29. Calendar dumps sit on turns that hold no needle, update or recall question.

**Trade-offs.** One scenario with keyword scoring is small and easy to explain, but it says little about real conversations. Mock token counts are word counts. They prove the pipeline runs, and they are never results.

## Team baseline

**What it does.** `src/agents/team.py` builds an Agno `Team` in coordinate mode. The leader plans and delegates. `calendar_agent` calls the calendar tool, and `writer` produces the reply. `run_turn` asks the memory strategy for context, runs the team, adds up tokens per agent, and records the finished turn. `FullHistory` is the baseline and sends everything every turn.

**Why this design.** The brief's example also had a `planner` member. The leader already plans, so a separate planner would only add model calls. Context goes to the leader and `writer`, because those two need the conversation. `calendar_agent` only needs its task.

**Agno facts I checked by running them (version 3.1.12).**
- `Team.run(list_of_messages)` merges the user turns and drops assistant and system messages, so context is passed with `additional_input`.
- Members see only their task unless they get their own `additional_input`.
- `output.metrics` covers the leader only. Each member's tokens are in `output.member_responses`, so `run_turn` adds them up.

**Trade-offs.** A team costs several model calls per turn, which is the reason memory size matters. The leader decides whether to delegate, so calls can vary between runs. A fixed Workflow would be more repeatable, but the brief asks about multi-agent cost under model-driven delegation. The spend guard counts finished runs plus the current one, and refuses to run a paid model that has no price entry.

## Memory strategies

**`RollingSummary`.** Keeps the last 6 turns verbatim. Once 5 older turns pile up, they are folded into one running summary by a model call.

**`TieredMemory`.** Has three stores:
- *Working memory* holds the last 6 turns, the same N as above for fairness. Calendar dumps are cut to 300 characters.
- *Semantic memory* holds durable facts as key-value entries with a source turn. A newer value replaces an older one, and an older value can never overwrite a newer one. Each turn gets a token-capped profile block.
- *Episodic memory* holds chunk summaries and calendar summaries in SQLite FTS5. Only the top 3 keyword matches for the current message are sent. Each episode has an importance and a turn number. When there are more than 8, the one with the lowest `importance * 0.97^age` is evicted.

**Why this design.** Every 5 turns, one model call produces both the episode summary and the facts, which is cheaper than two calls. FTS5 is built into SQLite, so no vector database is needed. User text is quoted before it reaches FTS5, so it cannot be read as query syntax.

**Counting costs honestly.** Summarising and extracting cost tokens too. They are logged under `memory_ops` and included in totals.

**Trade-offs.** Keyword retrieval misses synonyms. Fact keys are chosen by the model, so one fact can end up under two keys. The prompt lists existing keys to reduce that. A fact's source turn is the end of its 5-turn chunk, not its exact turn. If the model returns invalid JSON, the raw text is kept as an episode, but no facts are stored from that chunk.
