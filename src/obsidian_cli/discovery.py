from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from obsidian_cli.vault import VaultError


@dataclass(frozen=True, slots=True)
class VaultCandidate:
    source: str
    path: Path


class VaultLocator:
    def __init__(
        self, env: dict[str, str] | None = None, home: Path | None = None
    ) -> None:
        self._env = dict(env or os.environ)
        self._home = (home or Path.home()).expanduser()

    def resolve(self, cli_value: str | None) -> Path:
        cli_path = self._path_from_string(cli_value)
        if cli_path is not None:
            return cli_path

        env_path = self._path_from_string(self._env.get("OBSIDIAN_VAULT"))
        if env_path is not None:
            return env_path

        discovered = self.discover_default_vault()
        if discovered is not None:
            return discovered.path

        raise VaultError(
            "vault path is required; use --vault, OBSIDIAN_VAULT, or place your vault in a default Obsidian location"
        )

    def discover_default_vault(self) -> VaultCandidate | None:
        config_candidate = self._discover_from_obsidian_config()
        if config_candidate is not None:
            return config_candidate

        for candidate in self._iter_default_candidates():
            if self._is_obsidian_vault(candidate.path):
                return candidate
        return None

    def _discover_from_obsidian_config(self) -> VaultCandidate | None:
        for config_path in self._iter_obsidian_config_paths():
            if not config_path.is_file():
                continue
            try:
                payload = json.loads(config_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue

            vaults = payload.get("vaults")
            if not isinstance(vaults, dict):
                continue

            recent_vaults: list[tuple[int, str]] = []
            for item in vaults.values():
                if not isinstance(item, dict):
                    continue
                path_value = item.get("path")
                if not isinstance(path_value, str):
                    continue
                timestamp = item.get("ts")
                recent_vaults.append(
                    (timestamp if isinstance(timestamp, int) else -1, path_value)
                )

            for _, path_value in sorted(recent_vaults, reverse=True):
                path = Path(path_value).expanduser()
                if self._is_obsidian_vault(path):
                    return VaultCandidate(
                        source=f"obsidian-config:{config_path}", path=path
                    )

        return None

    def _iter_obsidian_config_paths(self) -> list[Path]:
        appdata = self._env.get("APPDATA")
        paths = [
            self._home
            / "Library"
            / "Application Support"
            / "obsidian"
            / "obsidian.json",
            self._home / ".config" / "obsidian" / "obsidian.json",
        ]
        if appdata:
            paths.append(Path(appdata) / "obsidian" / "obsidian.json")
        else:
            paths.append(
                self._home / "AppData" / "Roaming" / "obsidian" / "obsidian.json"
            )
        return paths

    def _iter_default_candidates(self) -> list[VaultCandidate]:
        return [
            VaultCandidate(
                "macos-documents-default", self._home / "Documents" / "Obsidian Vault"
            ),
            VaultCandidate(
                "macos-documents-generic", self._home / "Documents" / "Obsidian"
            ),
            VaultCandidate(
                "macos-icloud-default",
                self._home
                / "Library"
                / "Mobile Documents"
                / "iCloud~md~obsidian"
                / "Documents",
            ),
            VaultCandidate(
                "windows-documents-default", self._home / "Documents" / "Obsidian Vault"
            ),
            VaultCandidate(
                "windows-documents-generic", self._home / "Documents" / "Obsidian"
            ),
        ]

    @staticmethod
    def _path_from_string(raw_value: str | None) -> Path | None:
        if not raw_value:
            return None
        return Path(raw_value)

    @staticmethod
    def _is_obsidian_vault(path: Path) -> bool:
        return (path / ".obsidian").is_dir()
