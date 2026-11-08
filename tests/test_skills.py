from pathlib import Path

import pytest

from src.metrics import load_yaml
from src.skills.lint import lint_skills
from src.skills.loader import SkillLoader, read_metadata

SKILLS = Path("skills")
LIMITS = load_yaml("settings.yaml")["skills"]


def write_skill(root, folder, text):
    (root / folder).mkdir()
    (root / folder / "SKILL.md").write_text(text, encoding="utf-8")


def lint(root):
    return lint_skills(root, description_max_chars=40, body_max_tokens=20)


def good(name):
    return f"---\nname: {name}\ndescription: Short.\n---\nBody\n"


def test_repo_has_ten_clean_skills():
    assert len(SkillLoader(SKILLS).index) == 10
    assert lint_skills(SKILLS, LIMITS["description_max_chars"], LIMITS["body_max_tokens"]) == []


def test_catalog_has_descriptions_but_no_bodies():
    catalog = SkillLoader(SKILLS).catalog()
    assert "meeting-notes" in catalog and "Open questions" not in catalog


def test_load_skill_returns_body_without_frontmatter():
    body = SkillLoader(SKILLS).load_skill("meeting-notes")
    assert "Open questions" in body and "description:" not in body


@pytest.mark.parametrize("name", ["nope", "../../.env", "..\\secret"])
def test_load_skill_rejects_unknown_names(name):
    assert SkillLoader(SKILLS).load_skill(name).startswith("Unknown skill")


def test_body_containing_a_delimiter_is_kept_whole(tmp_path):
    write_skill(tmp_path, "a", "---\nname: a\ndescription: b\n---\nfirst\n---\nsecond\n")
    assert read_metadata(tmp_path / "a" / "SKILL.md") == {"name": "a", "description": "b"}
    body = SkillLoader(tmp_path).load_skill("a")
    assert "first" in body and "second" in body


def test_clean_skill_passes(tmp_path):
    write_skill(tmp_path, "fine", good("fine"))
    assert lint(tmp_path) == []


def test_catches_missing_frontmatter(tmp_path):
    write_skill(tmp_path, "broken", "# no frontmatter\n")
    assert "bad frontmatter" in lint(tmp_path)[0]


def test_catches_unclosed_frontmatter(tmp_path):
    write_skill(tmp_path, "broken", "---\nname: broken\n")
    assert "bad frontmatter" in lint(tmp_path)[0]


def test_catches_invalid_yaml(tmp_path):
    write_skill(tmp_path, "broken", "---\nname: [unclosed\n---\nBody\n")
    assert "bad frontmatter" in lint(tmp_path)[0]


def test_catches_name_folder_mismatch(tmp_path):
    write_skill(tmp_path, "folder", good("other"))
    assert "does not match folder" in lint(tmp_path)[0]


def test_catches_long_description(tmp_path):
    write_skill(tmp_path, "wordy", f"---\nname: wordy\ndescription: {'x' * 41}\n---\nBody\n")
    assert "description is over" in lint(tmp_path)[0]


def test_catches_body_over_budget(tmp_path):
    write_skill(tmp_path, "big", "---\nname: big\ndescription: Short.\n---\n" + "word " * 30)
    assert "over the budget" in lint(tmp_path)[0]


def test_catches_duplicate_names(tmp_path):
    write_skill(tmp_path, "aaa", good("aaa"))
    write_skill(tmp_path, "bbb", good("aaa"))
    assert any("duplicate name" in problem for problem in lint(tmp_path))


def test_catches_missing_name_and_description(tmp_path):
    write_skill(tmp_path, "empty", "---\nother: 1\n---\nBody\n")
    problems = lint(tmp_path)
    assert any("no name" in p for p in problems) and any("no description" in p for p in problems)
