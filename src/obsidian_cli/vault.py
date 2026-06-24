from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable


class VaultError(Exception):
    """Raised when the vault cannot fulfill a requested operation."""


@dataclass(slots=True)
class SearchMatch:
    note_path: str
    line_number: int
    line_text: str


@dataclass(frozen=True, slots=True)
class SshConfig:
    host: str
    user: str | None = None
    port: int | None = None
    identity_file: str | None = None

    @property
    def destination(self) -> str:
        return f"{self.user}@{self.host}" if self.user else self.host


class VaultBackend:
    root: Path | str

    def exists(self) -> bool:
        raise NotImplementedError

    def is_obsidian_vault(self) -> bool:
        raise NotImplementedError

    def list_notes(self) -> list[str]:
        raise NotImplementedError

    def read_note(self, note_path: str) -> str:
        raise NotImplementedError

    def write_note(
        self, note_path: str, content: str, create_only: bool = False
    ) -> Path | str:
        raise NotImplementedError

    def append_note(self, note_path: str, content: str) -> Path | str:
        raise NotImplementedError

    def read_note_lines(self, note_path: str, start_line: int, end_line: int) -> str:
        raise NotImplementedError

    def write_note_lines(
        self, note_path: str, start_line: int, end_line: int, content: str
    ) -> Path | str:
        raise NotImplementedError

    def search(self, query: str, case_sensitive: bool = False) -> list[SearchMatch]:
        raise NotImplementedError


class ObsidianVault(VaultBackend):
    def __init__(self, root: Path) -> None:
        self.root = root.expanduser().resolve()

    def exists(self) -> bool:
        return self.root.exists() and self.root.is_dir()

    def is_obsidian_vault(self) -> bool:
        return (self.root / ".obsidian").exists()

    def resolve_note(self, note_path: str) -> Path:
        candidate = (self.root / note_path).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise VaultError(f"path escapes vault root: {note_path}")
        return candidate

    def list_notes(self) -> list[str]:
        if not self.exists():
            raise VaultError(f"vault does not exist: {self.root}")
        return sorted(
            str(path.relative_to(self.root))
            for path in self.root.rglob("*.md")
            if ".obsidian" not in path.parts
        )

    def read_note(self, note_path: str) -> str:
        path = self.resolve_note(note_path)
        if not path.exists():
            raise VaultError(f"note not found: {note_path}")
        if not path.is_file():
            raise VaultError(f"not a file: {note_path}")
        return path.read_text(encoding="utf-8")

    def _read_existing_markdown_path(self, note_path: str) -> Path:
        path = self.resolve_note(note_path)
        self._validate_markdown_extension(path, note_path)
        if not path.exists():
            raise VaultError(f"note not found: {note_path}")
        if not path.is_file():
            raise VaultError(f"not a file: {note_path}")
        return path

    @staticmethod
    def _validate_markdown_extension(path: Path, note_path: str) -> None:
        if path.suffix.lower() != ".md":
            raise VaultError(f"only markdown files are supported (.md): {note_path}")

    @staticmethod
    def _validate_line_range(start_line: int, end_line: int, line_count: int) -> None:
        if start_line < 1 or end_line < 1:
            raise VaultError("line numbers must be >= 1")
        if start_line > end_line:
            raise VaultError("start line must be <= end line")
        if end_line > line_count:
            raise VaultError(
                f"line range {start_line}-{end_line} exceeds file length {line_count}"
            )

    def write_note(
        self, note_path: str, content: str, create_only: bool = False
    ) -> Path:
        path = self.resolve_note(note_path)
        self._validate_markdown_extension(path, note_path)
        if create_only and path.exists():
            raise VaultError(f"note already exists: {note_path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def append_note(self, note_path: str, content: str) -> Path:
        path = self.resolve_note(note_path)
        self._validate_markdown_extension(path, note_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(content)
        return path

    def read_note_lines(self, note_path: str, start_line: int, end_line: int) -> str:
        path = self._read_existing_markdown_path(note_path)
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        self._validate_line_range(start_line, end_line, len(lines))
        return "".join(lines[start_line - 1 : end_line])

    def write_note_lines(
        self, note_path: str, start_line: int, end_line: int, content: str
    ) -> Path:
        path = self._read_existing_markdown_path(note_path)
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        self._validate_line_range(start_line, end_line, len(lines))

        replacement_lines = content.splitlines(keepends=True)
        lines[start_line - 1 : end_line] = replacement_lines
        path.write_text("".join(lines), encoding="utf-8")
        return path

    def search(self, query: str, case_sensitive: bool = False) -> list[SearchMatch]:
        if not query:
            raise VaultError("query must not be empty")

        needle = query if case_sensitive else query.lower()
        matches: list[SearchMatch] = []

        for note_path in self.list_notes():
            content = self.read_note(note_path)
            for idx, line in enumerate(content.splitlines(), start=1):
                haystack = line if case_sensitive else line.lower()
                if needle in haystack:
                    matches.append(
                        SearchMatch(
                            note_path=note_path,
                            line_number=idx,
                            line_text=line,
                        )
                    )
        return matches


class SshObsidianVault(VaultBackend):
    def __init__(
        self,
        root: str,
        ssh_config: SshConfig,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        self._root = PurePosixPath(root)
        self.root = f"{ssh_config.destination}:{self._root}"
        self._ssh_config = ssh_config
        self._runner = runner

    def exists(self) -> bool:
        return self._remote_test(f"test -d {self._quote(self._root)}")

    def is_obsidian_vault(self) -> bool:
        return self._remote_test(f"test -d {self._quote(self._root / '.obsidian')}")

    def list_notes(self) -> list[str]:
        if not self.exists():
            raise VaultError(f"vault does not exist: {self.root}")
        command = (
            f"cd {self._quote(self._root)} && "
            "find . -path './.obsidian' -prune -o -type f -name '*.md' -print | "
            "sed 's#^\\./##' | sort"
        )
        output = self._run_ssh(command)
        return [line for line in output.splitlines() if line]

    def read_note(self, note_path: str) -> str:
        path = self._resolve_note(note_path)
        self._ensure_remote_markdown(path, note_path)
        self._ensure_remote_exists(path, note_path)
        return self._run_ssh(f"cat {self._quote(path)}", strip_output=False)

    def write_note(
        self, note_path: str, content: str, create_only: bool = False
    ) -> str:
        path = self._resolve_note(note_path)
        self._ensure_remote_markdown(path, note_path)
        if create_only and self._remote_test(f"test -e {self._quote(path)}"):
            raise VaultError(f"note already exists: {note_path}")
        self._run_ssh(
            f"mkdir -p {self._quote(path.parent)} && cat > {self._quote(path)}",
            input_text=content,
            strip_output=False,
        )
        return str(path)

    def append_note(self, note_path: str, content: str) -> str:
        path = self._resolve_note(note_path)
        self._ensure_remote_markdown(path, note_path)
        self._run_ssh(
            f"mkdir -p {self._quote(path.parent)} && cat >> {self._quote(path)}",
            input_text=content,
            strip_output=False,
        )
        return str(path)

    def read_note_lines(self, note_path: str, start_line: int, end_line: int) -> str:
        content = self.read_note(note_path)
        lines = content.splitlines(keepends=True)
        ObsidianVault._validate_line_range(start_line, end_line, len(lines))
        return "".join(lines[start_line - 1 : end_line])

    def write_note_lines(
        self, note_path: str, start_line: int, end_line: int, content: str
    ) -> str:
        existing = self.read_note(note_path)
        lines = existing.splitlines(keepends=True)
        ObsidianVault._validate_line_range(start_line, end_line, len(lines))
        lines[start_line - 1 : end_line] = content.splitlines(keepends=True)
        return self.write_note(note_path, "".join(lines))

    def search(self, query: str, case_sensitive: bool = False) -> list[SearchMatch]:
        if not query:
            raise VaultError("query must not be empty")

        needle = query if case_sensitive else query.lower()
        matches: list[SearchMatch] = []
        for note_path in self.list_notes():
            content = self.read_note(note_path)
            for idx, line in enumerate(content.splitlines(), start=1):
                haystack = line if case_sensitive else line.lower()
                if needle in haystack:
                    matches.append(
                        SearchMatch(
                            note_path=note_path,
                            line_number=idx,
                            line_text=line,
                        )
                    )
        return matches

    def _ensure_remote_exists(self, path: PurePosixPath, note_path: str) -> None:
        if not self._remote_test(f"test -f {self._quote(path)}"):
            raise VaultError(f"note not found: {note_path}")

    @staticmethod
    def _ensure_remote_markdown(path: PurePosixPath, note_path: str) -> None:
        if path.suffix.lower() != ".md":
            raise VaultError(f"only markdown files are supported (.md): {note_path}")

    def _resolve_note(self, note_path: str) -> PurePosixPath:
        relative = PurePosixPath(note_path)
        if relative.is_absolute() or ".." in relative.parts:
            raise VaultError(f"path escapes vault root: {note_path}")
        return self._root / relative

    def _remote_test(self, command: str) -> bool:
        ssh_command = self._build_ssh_command(command)
        result = self._runner(ssh_command, text=True, capture_output=True)
        return result.returncode == 0

    def _run_ssh(
        self, command: str, input_text: str | None = None, strip_output: bool = True
    ) -> str:
        ssh_command = self._build_ssh_command(command)
        result = self._runner(
            ssh_command,
            text=True,
            capture_output=True,
            input=input_text,
        )
        if result.returncode != 0:
            message = (
                result.stderr.strip() or result.stdout.strip() or "ssh command failed"
            )
            raise VaultError(message)
        return result.stdout.strip() if strip_output else result.stdout

    def _build_ssh_command(self, remote_command: str) -> list[str]:
        command = ["ssh"]
        if self._ssh_config.port is not None:
            command.extend(["-p", str(self._ssh_config.port)])
        if self._ssh_config.identity_file:
            command.extend(["-i", self._ssh_config.identity_file])
        command.append(self._ssh_config.destination)
        command.append(remote_command)
        return command

    @staticmethod
    def _quote(path: PurePosixPath) -> str:
        return shlex.quote(str(path))
