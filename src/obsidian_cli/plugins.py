from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


SKILL_BODY = """---
name: "odcli"
description: "Use odcli to read, write, append, search, and patch notes inside a local or remote Obsidian vault."
---

# odcli

Use `odcli` when you need to read or write notes inside an Obsidian vault, either
locally or over SSH on a remote machine.

## What this skill does

- Reads notes from a local or remote Obsidian vault
- Writes or appends Markdown notes
- Replaces specific line ranges in a note
- Searches across Markdown notes in the vault
- Works with either `odcli` or `obsidian-cli`

## Preferred workflow

1. If `OBSIDIAN_VAULT` (or `ODCLI_VAULT`) is set, `odcli` uses it automatically.
2. Otherwise let `odcli` auto-discover the vault from local Obsidian config or
   common default locations.
3. For remote vaults, prefer an SSH config alias (`odcli vm list`) over
   repeating `--ssh-host` / `--ssh-user` flags.

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

## Remote vaults over SSH

If a host is defined in `~/.ssh/config`, use the alias directly:

```bash
odcli vm list
odcli vm read Inbox/today.md
odcli vm write Inbox/today.md --content "# Remote"
```

Environment variables provide defaults so you do not need to repeat flags:

- `ODCLI_VAULT` / `OBSIDIAN_VAULT`: vault path
- `ODCLI_SSH_HOST`, `ODCLI_SSH_USER`, `ODCLI_SSH_PORT`, `ODCLI_SSH_IDENTITY`

If `ODCLI_SSH_IDENTITY` is not set, `odcli` auto-discovers the first existing
key under `~/.ssh` (`id_ed25519`, `id_ecdsa`, `id_rsa`).

## Notes

- `--vault /path/to/vault` overrides auto-discovery and env vars.
- `OBSIDIAN_VAULT` / `ODCLI_VAULT` is used when set.
- Line numbers for `read-lines` and `write-lines` are 1-based and inclusive.
- For SSH mode the vault path is interpreted on the remote machine; if unset,
  an OS-aware default is used.
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
