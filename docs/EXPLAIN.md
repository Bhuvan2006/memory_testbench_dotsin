# Project explanation

Plain-language notes for each milestone: what it does, why it is built that way, and the trade-offs.

## Scenario and mock model

**What it does.** `data/generate_scenario.py` writes a seeded 40-turn conversation about a fictional person, Rowan. Twelve facts are planted in turns 2-13, and twelve recall questions are asked in turns 29-40. Four turns carry a large fake calendar dump. `src/mock_model.py` is a fake Agno model that can only answer from the messages it receives.

**Why this design.** A seed means every memory strategy faces the same conversation. The expected answers are short strings, so scoring needs no judge model. One fact, the budget cap, changes at turn 20. That tests whether a strategy keeps the newest value instead of the first one.

**Differences from the brief.** Turns 2-12 and 30-40 are each 11 slots for 12 items, so needles run to turn 13 and recall starts at turn 29. Calendar dumps sit on turns that hold no needle, update or recall question.

**Trade-offs.** One scenario with keyword scoring is small and easy to explain, but it says little about real conversations. Mock token counts are word counts. They prove the pipeline runs, and they are never results.
