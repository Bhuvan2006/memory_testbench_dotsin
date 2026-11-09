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

## Skill harness

**What it does.** `src/skills/loader.py` reads only the name and description of each skill at startup and lists them in the prompt. `load_skill(name)` returns a full body when the agent asks. `src/skills/lint.py` checks frontmatter, name against folder, description length, body size and duplicates. There are 4 real skills and 6 generated dummies.

**Three modes compared.** *Eager* puts all bodies in the prompt. *Lazy* is my loader. *Native* is Agno's `Skills(loaders=[LocalSkills(path)])`, which exists in 3.1.12.

**Why this design.** A skill name from the model is only looked up in a dictionary, so it can never become a file path. Starting context is read from the provider's usage on the first model call, so it includes tool definitions.

**What differs in native.** Agno gives three tools (`get_skill_instructions`, `get_skill_reference`, `get_skill_script`) and adds a fixed block of explanatory text to the prompt, so its starting context is larger than my loader's. It validates skills at load, including that the name matches the folder. On a Team, native skills reach only the leader. The comparison uses one Agent per mode so that only the prompt differs.

**Trade-offs.** Lazy loading adds a tool round trip, and it is only cheaper when most skills go unused. If the agent needs many skills in one task, eager can win. The linter's token budget is a word-count estimate, which is fine for a rule of thumb.

## Benchmark

**What it does.** `bench/run_benchmark.py` runs each memory strategy through all 40 turns and each skill mode on two tasks. The default is 3 repetitions, but the reported NVIDIA run used 2 (`--reps 2 --out results/run_b`). One task needs one skill, and the `_all` task needs all 10. It writes `results.csv` after every finished run, every reply and summary to `replies.jsonl`, then `summary.md` and two charts. Tokens come from provider usage metrics. Mock output goes to `results/mock/` so it cannot be confused with real results.

**Fairness.** Same scenario, model, temperature, system prompts and N. For Ollama, `num_ctx` is set high, because Ollama would otherwise silently cut long prompts and make full history look cheap.

**Quality.** Recall is a keyword match on 12 known answers, with commas and spacing normalised and digit boundaries respected, so 7 does not match 17. `Wrong` counts contradicted or incorrect answers. Admitting ignorance ("I do not know", "couldn't find", "not provided", "unable to") counts as incorrect but not wrong. "$35,000" counts as a match for the 35k budget.

**A local-model finding.** On `qwen2.5-coder:3b`, a 2-turn check showed `len(output.member_responses) == 0`. The leader wrote its delegation as plain JSON text instead of a real tool call, so Agno had nothing to execute and no member ran. The zero calendar and writer tokens are therefore real, not a metrics bug, and those rows do not measure a multi-agent system.

**About the mock numbers.** The mock's summariser just keeps the newest 120 words, so `RollingSummary` scores 0% recall in mock mode. That is a property of the fake summariser and says nothing about the strategy.

## Likely interview questions and honest answers

**Why a Team and not a Workflow?** A Workflow fits a fixed order of steps. A Team fits a model deciding who does what. The project measures what memory costs when several agents each make model calls, and model-driven delegation is the realistic case for that. The cost is that the number of calls can vary between runs, which is why the benchmark defaults to 3 repetitions per configuration. The reported run used only 2, so it gives just a rough idea of how much the numbers vary.

**Why not use Agno's built-in memory?** The experiment needs one place where only the memory strategy changes. Agno's history and memory are switched off, and each strategy decides exactly what the model sees.

**What does each memory tier store?** Working memory holds the last 6 turns verbatim with tool output trimmed. Semantic memory holds durable facts as key-value pairs with a source turn. Episodic memory holds summaries of 5-turn chunks and of tool outputs, searched by keyword.

**How do you handle a fact that changes?** A newer value replaces the old one under the same key. The budget cap changes at turn 20 to test this, and a stale answer is counted as wrong.

**How was quality measured?** Twelve recall questions with known answers, checked by keyword match. It is deterministic and free, but it only measures fact recall. It says nothing about tone or helpfulness.

**Are the summarisation costs included?** Yes, as `memory_ops`, and they are part of the totals.

**Why give context to the leader and writer, but not the calendar agent?** The leader needs it to plan and the writer needs it to answer. The calendar agent only reads a tool, so sending it the conversation would add cost and no benefit.

**Where does this break?** Keyword retrieval misses synonyms. A small model may return invalid JSON, which loses that chunk's facts (`parse_failures` in the results counts this). Facts that were never extracted can only be found through episodes. The scenario is one synthetic conversation that I designed myself.

**Why might tiered memory not win?** It pays for extra summarising calls, and a short conversation may never recoup them. It can also lose facts that were never extracted or retrieved, so fewer tokens can come with lower recall.

**Where does lazy loading not help?** When a task needs most or all skills. Each load adds a round trip, and loaded text stays in context for later model calls. The model can also pick the wrong skill. The `_all` benchmark rows measure this.

**What is the prompt-caching caveat?** The benchmark does not enable caching and prices every input token in full. Provider caching discounts a repeated prompt prefix, so a stable eager prompt or append-only history can cost much less than its token count suggests. Tiered memory changes its context often, so it may benefit less. The token savings here are measured, but the real money saved could be smaller.

**How would this change in production?** I would test on real conversation samples with consent, add embedding retrieval if keywords proved too weak, attribute facts to exact turns, and judge quality with more than keyword matching.

**What did you learn about the framework?** Passing a message list to `Team.run` merges user turns and drops assistant turns. I found that by running a fake model and printing what it received, and that is why context goes through `additional_input`. Docs alone would not have shown it.
