"""Generate the deterministic, fully synthetic 40-turn scenario.

Run from the repo root: python -m data.generate_scenario
"""
import json
import random
from pathlib import Path

SCENARIO_PATH = Path(__file__).parent / "scenario.json"
TURN_COUNT = 40
FIRST_NEEDLE_TURN = 2  # the brief's turns 2-12 are 11 slots for 12 needles, so needles run to 13
FIRST_RECALL_TURN = 29  # the brief's turns 30-40 are 11 slots for 12 questions, so recall starts at 29
DUMP_TURNS = (14, 18, 23, 27)  # chosen to avoid needle, update and recall turns
UPDATE_TURN = 20

# `anchors` lets the mock find a fact in context. `expected` is what the scorer looks for.
NEEDLES = [
    {"key": "manager", "value": "Priya Raman", "sentence": "Quick context: my manager is {value}.",
     "question": "Who is my manager?", "expected": "Priya", "anchors": ["manager"]},
    {"key": "demo_slot", "value": "Thursday 3pm", "sentence": "The demo is on {value}.",
     "question": "When is the demo?", "expected": "Thursday", "anchors": ["demo"]},
    {"key": "deep_work", "value": "morning", "sentence": "I prefer {value} deep work.",
     "question": "What time of day do I prefer for deep work?", "expected": "morning", "anchors": ["deep work", "deep_work"]},
    {"key": "budget_cap", "value": "40k", "sentence": "The budget cap is {value}.",
     "question": "What is the budget cap?", "expected": "35", "anchors": ["budget"],
     "update_turn": UPDATE_TURN, "new_value": "35k", "stale": "40",
     "update_sentence": "Update from finance: the budget cap is now {value}."},
    {"key": "standup_time", "value": "9:45", "sentence": "Our standup is at {value} every day.",
     "question": "What time is our standup?", "expected": "9:45", "anchors": ["standup"]},
    {"key": "sleep_time", "value": "10:30pm", "sentence": "I try to be asleep by {value}.",
     "question": "What time do I try to be asleep by?", "expected": "10:30", "anchors": ["asleep", "sleep_time"]},
    {"key": "step_goal", "value": "8000", "sentence": "My daily step goal is {value} steps.",
     "question": "What is my daily step goal?", "expected": "8000", "anchors": ["step"]},
    {"key": "offsite_city", "value": "Lisbon", "sentence": "The team offsite will be in {value}.",
     "question": "Which city is the team offsite in?", "expected": "Lisbon", "anchors": ["offsite"]},
    {"key": "codename", "value": "Bluefin", "sentence": "The project codename is {value}.",
     "question": "What is the project codename?", "expected": "Bluefin", "anchors": ["codename"]},
    {"key": "review_day", "value": "Tuesday", "sentence": "My performance review is on {value}.",
     "question": "Which day is my performance review?", "expected": "Tuesday", "anchors": ["review"]},
    {"key": "lunch_break", "value": "1pm", "sentence": "I take lunch at {value}.",
     "question": "What time do I take lunch?", "expected": "1pm", "anchors": ["lunch"]},
    {"key": "team_size", "value": "7", "sentence": "There are {value} people on my team.",
     "question": "How many people are on my team?", "expected": "7", "anchors": ["people on my team", "team_size"]},
]

FILLER = [
    "Can you help me tidy my task list for this week?",
    "I moved two errands to the weekend so the week feels lighter.",
    "Draft a short note thanking the design group for their help.",
    "Remind me to look over the slide order before I share it.",
    "The office was quiet today and I got through my inbox.",
    "What is a good way to structure a one page status update?",
    "I want to spend less time in long email threads.",
    "Please suggest a simple agenda for a thirty minute check in.",
    "I finished the first draft of the onboarding checklist.",
    "Give me two tips for keeping meetings on time.",
]
EVENT_TITLES = ["Sync", "Roadmap chat", "Vendor call", "Design crit", "Hiring panel", "Retro", "Office hours", "Planning"]
ROOMS = ["Maple", "Cedar", "Willow", "Aspen", "Birch"]
PEOPLE = ["Alex", "Sam", "Jordan", "Casey", "Morgan", "Taylor", "Drew", "Quinn"]
DAYS = ["Mon", "Wed", "Fri", "Sat", "Sun"]  # excludes needle days so a dump can never answer a question


def calendar_dump(rng: random.Random) -> str:
    lines = []
    for i in range(60):
        attendees = ", ".join(rng.sample(PEOPLE, 3))
        hour = rng.randint(8, 18)
        lines.append(f"event {i:02d} | {rng.choice(DAYS)} {hour}:{rng.choice(['00', '30'])} "
                     f"| {rng.choice(EVENT_TITLES)} | room {rng.choice(ROOMS)} | attendees {attendees}")
    return "\n".join(lines)


def build_scenario(seed: int = 7) -> dict:
    rng = random.Random(seed)
    needles = [
        {"key": n["key"], "turn": FIRST_NEEDLE_TURN + i, "value": n["value"],
         "update_turn": n.get("update_turn"), "new_value": n.get("new_value")}
        for i, n in enumerate(NEEDLES)
    ]
    users = {needle["turn"]: source["sentence"].format(value=source["value"])
             for needle, source in zip(needles, NEEDLES)}
    budget = next(n for n in NEEDLES if n["key"] == "budget_cap")
    users[UPDATE_TURN] = budget["update_sentence"].format(value=budget["new_value"])

    recall = []
    for i, n in enumerate(NEEDLES):
        turn = FIRST_RECALL_TURN + i
        users[turn] = n["question"]
        recall.append({"turn": turn, "needle_key": n["key"], "question": n["question"],
                       "expected": n["expected"], "stale": n.get("stale")})

    turns = []
    for index in range(1, TURN_COUNT + 1):
        tool_output = None
        if index in DUMP_TURNS:
            user = "Please pull my full calendar for this week and tell me how busy it looks."
            tool_output = calendar_dump(rng)
        elif index == 1:
            user = "Hi, I want help planning my work week."
        else:
            user = users.get(index) or rng.choice(FILLER)
        turns.append({"index": index, "user": user, "tool_output": tool_output})
    return {"turns": turns, "recall": recall, "needles": needles}


def main() -> None:
    text = json.dumps(build_scenario(), indent=2, sort_keys=True)
    SCENARIO_PATH.write_text(text + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
