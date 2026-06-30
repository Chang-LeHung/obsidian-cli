from __future__ import annotations

import importlib.resources
from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, BaseLoader


_TEMPLATE_CONTEXT = {
    "name": "odcli",
    "alt_name": "obsidian-cli",
    "description": (
        "Use odcli to read, write, append, search, and patch notes "
        "inside a local or remote Obsidian vault."
    ),
}


def _render_template(name: str, context: dict[str, str] | None = None) -> str:
    """Load a Jinja2 template bundled with the package and render it."""
    ref = importlib.resources.files("obsidian_cli") / "templates" / name
    source = ref.read_text(encoding="utf-8")
    env = Environment(loader=BaseLoader(), keep_trailing_newline=True)
    template = env.from_string(source)
    return template.render(context or _TEMPLATE_CONTEXT)


@dataclass(frozen=True, slots=True)
class InstallResult:
    target: str
    path: Path


class SkillInstaller:
    def __init__(self, home: Path | None = None) -> None:
        self._home = (home or Path.home()).expanduser()

    def install(self, target: str) -> list[InstallResult]:
        if target == "codex-skill":
            return [
                self._install_skill(
                    "codex-skill", self._home / ".codex" / "skills" / "odcli"
                )
            ]
        if target == "claude-skill":
            return [
                self._install_skill(
                    "claude-skill", self._home / ".claude" / "skills" / "odcli"
                )
            ]
        if target == "all-skills":
            return [
                self._install_skill(
                    "codex-skill", self._home / ".codex" / "skills" / "odcli"
                ),
                self._install_skill(
                    "claude-skill", self._home / ".claude" / "skills" / "odcli"
                ),
            ]
        raise ValueError(f"unsupported plugin install target: {target}")

    def _install_skill(self, target: str, skill_dir: Path) -> InstallResult:
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            _render_template("SKILL.md.j2"), encoding="utf-8"
        )
        return InstallResult(target=target, path=skill_file)
