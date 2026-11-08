"""Write the 6 dummy skills that bring the benchmark to 10. Run: python -m data.generate_dummy_skills"""
from pathlib import Path

SKILLS_DIR = Path(__file__).parent.parent / "skills"

DUMMIES = {
    "expense-report": ("Group listed expenses by category and flag items over a stated limit.", "expenses", "category totals"),
    "travel-plan": ("Build a simple day-by-day trip outline from dates and a destination.", "trip details", "a daily outline"),
    "inbox-triage": ("Sort a list of email subjects into reply, read later and ignore.", "email subjects", "three groups"),
    "goal-review": ("Compare stated goals with recent progress and name the biggest gap.", "goals and progress", "a gap analysis"),
    "status-update": ("Write a short weekly status from a list of finished and planned work.", "work items", "a brief status"),
    "habit-check": ("Summarise how often a simple routine was kept during the week.", "routine logs", "a weekly count"),
}

TEMPLATE = """---
name: {name}
description: {description}
---
# {title}

This is a dummy skill used to measure prompt size.

## Steps
1. Read the {source} the user provided.
2. Remove duplicates and anything unrelated.
3. Group what remains in the most natural way.
4. Produce {output} that a busy person can scan quickly.

## Rules
- Use only the information provided.
- Keep the result under 100 words.
- Ask one question if something essential is missing.
"""


def main() -> None:
    for name, (description, source, output) in DUMMIES.items():
        folder = SKILLS_DIR / name
        folder.mkdir(parents=True, exist_ok=True)
        text = TEMPLATE.format(name=name, description=description, title=name.replace("-", " ").capitalize(),
                               source=source, output=output)
        (folder / "SKILL.md").write_text(text, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
