from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


SKILL_BODY = """---
name: "odcli"
description: "Use odcli to read, write, append, search, and patch notes inside a local Obsidian vault."
---

# odcli

Use `odcli` when you need to read or write notes inside a local Obsidian vault.

## What this skill does

- Reads notes from a local Obsidian vault
- Writes or appends Markdown notes
- Replaces specific line ranges in a note
- Searches across Markdown notes in the vault
- Works with either `odcli` or `obsidian-cli`

## Preferred workflow

1. Check whether `OBSIDIAN_VAULT` is set.
2. If it is not set, let `odcli` auto-discover the vault from local Obsidian config or common default locations.
3. Use `odcli` for direct note operations instead of editing vault files manually.

## Common commands

```bash
odcli check
odcli list
odcli read Inbox/today.md
odcli read-lines Inbox/today.md 3 8
odcli write Inbox/today.md --content "# Today"
odcli write-lines Inbox/today.md 3 4 --content "- replaced\\n- lines\\n"
odcli append Inbox/today.md --content "\\n- new item"
odcli search "project alpha"
```

## Notes

- `--vault /path/to/vault` overrides auto-discovery.
- `OBSIDIAN_VAULT` is used when set.
- Line numbers for `read-lines` and `write-lines` are 1-based and inclusive.
"""


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
        skill_file.write_text(SKILL_BODY, encoding="utf-8")
        return InstallResult(target=target, path=skill_file)
