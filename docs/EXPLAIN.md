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
