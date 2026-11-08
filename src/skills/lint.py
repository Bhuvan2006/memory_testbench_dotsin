"""Check every skill folder. Run: python -m src.skills.lint"""
import sys
from pathlib import Path

from yaml import YAMLError as yaml_error

from src.metrics import load_yaml
from src.skills.loader import read_body, read_metadata

TOKENS_PER_WORD = 1.3  # a lint budget is a rule of thumb, so no provider call is needed


def lint_skills(root: Path, description_max_chars: int, body_max_tokens: int) -> list[str]:
    problems, seen = [], {}
    for path in sorted(Path(root).glob("*/SKILL.md")):
        folder = path.parent.name
        try:
            metadata = read_metadata(path)
        except (ValueError, yaml_error) as error:
            problems.append(f"{folder}: bad frontmatter ({error})")
            continue
        name, description = metadata.get("name"), metadata.get("description")
        if not name:
            problems.append(f"{folder}: frontmatter has no name")
        elif name != folder:
            problems.append(f"{folder}: name '{name}' does not match folder")
        if name in seen:
            problems.append(f"{folder}: duplicate name '{name}', also in {seen[name]}")
        seen.setdefault(name, folder)
        if not description:
            problems.append(f"{folder}: frontmatter has no description")
        elif len(description) > description_max_chars:
            problems.append(f"{folder}: description is over {description_max_chars} characters")
        tokens = len(read_body(path).split()) * TOKENS_PER_WORD
        if tokens > body_max_tokens:
            problems.append(f"{folder}: body is about {tokens:.0f} tokens, over the budget of {body_max_tokens}")
    return problems


def main() -> int:
    limits = load_yaml("settings.yaml")["skills"]
    problems = lint_skills(Path("skills"), limits["description_max_chars"], limits["body_max_tokens"])
    print("\n".join(problems) or "All skills passed.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
