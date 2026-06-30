from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from obsidian_cli.vault import VaultError


@dataclass(frozen=True, slots=True)
class SshAliasConfig:
    """Resolved SSH configuration for a single alias from ~/.ssh/config."""

    alias: str
    host_name: str | None = None
    user: str | None = None
    port: int | None = None
    identity_file: str | None = None


class SshConfigLocator:
    """Reads ``~/.ssh/config`` and resolves host aliases the way ssh does."""

    def __init__(self, config_path: Path | None = None) -> None:
        self._config_path = config_path or (Path.home() / ".ssh" / "config")

    @property
    def config_path(self) -> Path:
        return self._config_path

    def resolve_alias(self, alias: str) -> SshAliasConfig | None:
        if not self._config_path.is_file():
            return None
        try:
            text = self._config_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None

        merged: dict[str, str] = {}
        matched = False
        for entry in self._parse(text):
            hosts = entry.get("host", "").split()
            if not any(self._pattern_matches(name, alias) for name in hosts):
                continue
            # Skip entries that are only negative matches.
            if all(name.startswith("!") for name in hosts):
                continue
            matched = True
            for key, value in entry.items():
                if key == "host":
                    continue
                if key not in merged:
                    merged[key] = value

        if not matched:
            return None

        identity = merged.get("identityfile")
        if identity:
            identity = str(Path(identity).expanduser())

        port_raw = merged.get("port")
        port = int(port_raw) if port_raw and port_raw.isdigit() else None

        return SshAliasConfig(
            alias=alias,
            host_name=merged.get("hostname"),
            user=merged.get("user"),
            port=port,
            identity_file=identity,
        )

    @staticmethod
    def _parse(text: str) -> list[dict[str, str]]:
        entries: list[dict[str, str]] = []
        current: dict[str, str] = {}
        for raw_line in text.splitlines():
            line = raw_line.split("#", 1)[0].strip()
            if not line:
                continue
            parts = line.split(None, 1)
            if len(parts) != 2:
                continue
            key, value = parts
            key_lower = key.lower()
            if key_lower == "host":
                if current:
                    entries.append(current)
                current = {"host": value}
            else:
                current[key_lower] = value
        if current:
            entries.append(current)
        return entries

    @staticmethod
    def _pattern_matches(pattern: str, name: str) -> bool:
        if pattern.startswith("!"):
            negated = SshConfigLocator._pattern_matches(pattern[1:], name)
            # Negative patterns filter out matches; handled by caller via skip.
            return negated
        regex = re.escape(pattern).replace(r"\*", ".*").replace(r"\?", ".")
        return re.fullmatch(regex, name) is not None


def default_identity_file(home: Path | None = None) -> str | None:
    """Pick the first existing default SSH private key under ~/.ssh."""
    ssh_dir = (home or Path.home()) / ".ssh"
    for name in ("id_ed25519", "id_ecdsa", "id_rsa"):
        candidate = ssh_dir / name
        if candidate.is_file():
            return str(candidate)
    return None


def default_ssh_user() -> str:
    """Best-effort current OS user, used as SSH user default."""
    try:
        import getpass

        return getpass.getuser()
    except Exception as exc:  # pragma: no cover - extremely unusual
        raise VaultError(f"unable to determine current user: {exc}") from exc


def default_ssh_vault_path() -> str:
    """OS-aware default vault path used when connecting over SSH.

    The path is interpreted on the *remote* machine, so we keep ``~`` literal
    and let the remote shell expand it. Windows remotes typically use a
    relative ``Documents\\Obsidian Vault`` path because ``~`` expansion is not
    reliable across Windows OpenSSH shells.
    """
    import sys

    if sys.platform == "win32":
        return r"Documents\Obsidian Vault"
    return "~/Documents/Obsidian Vault"
