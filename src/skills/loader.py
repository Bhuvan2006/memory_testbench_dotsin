"""Hand-written lazy skill loader: names and descriptions up front, bodies on demand."""
from pathlib import Path

import yaml

DELIMITER = "---"


def read_metadata(path: Path) -> dict:
    """Stop at the closing delimiter, so no body text reaches the catalog."""
    with path.open(encoding="utf-8") as handle:
        if handle.readline().strip() != DELIMITER:
            raise ValueError(f"{path}: missing frontmatter")
        lines = []
        for line in handle:
            if line.strip() == DELIMITER:
                metadata = yaml.safe_load("".join(lines))
                if not isinstance(metadata, dict):
                    raise ValueError(f"{path}: frontmatter is not a mapping")
                return metadata
            lines.append(line)
    raise ValueError(f"{path}: frontmatter is never closed")


def read_body(path: Path) -> str:
    return path.read_text(encoding="utf-8").split(f"\n{DELIMITER}", 1)[-1].strip()


class SkillLoader:
    def __init__(self, root: Path):
        self.index = {}
        for path in sorted(Path(root).glob("*/SKILL.md")):
            metadata = read_metadata(path)
            self.index[metadata["name"]] = {"description": metadata["description"], "path": path}

    def catalog(self) -> str:
        lines = [f"- {name}: {skill['description']}" for name, skill in self.index.items()]
        return "Available skills. Call load_skill(name) to read one before using it:\n" + "\n".join(lines)

    def eager_block(self) -> str:
        return "\n\n".join(f"# Skill: {name}\n{read_body(skill['path'])}" for name, skill in self.index.items())

    def load_skill(self, name: str) -> str:
        """Return the full instructions for a skill.

        Args:
            name: The skill name from the available skills list.
        """
        # Looked up in the index, so a model-supplied name can never become a file path.
        if name not in self.index:
            return f"Unknown skill '{name}'. Available: {', '.join(self.index)}"
        return read_body(self.index[name]["path"])
