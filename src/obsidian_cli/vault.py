from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class VaultError(Exception):
    """Raised when the vault cannot fulfill a requested operation."""


@dataclass(slots=True)
class SearchMatch:
    note_path: str
    line_number: int
    line_text: str


class ObsidianVault:
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
        if path.suffix.lower() != ".md":
            raise VaultError("only markdown files are supported (.md)")
        if not path.exists():
            raise VaultError(f"note not found: {note_path}")
        if not path.is_file():
            raise VaultError(f"not a file: {note_path}")
        return path

    def _validate_line_range(self, start_line: int, end_line: int, line_count: int) -> None:
        if start_line < 1 or end_line < 1:
            raise VaultError("line numbers must be >= 1")
        if start_line > end_line:
            raise VaultError("start line must be <= end line")
        if end_line > line_count:
            raise VaultError(
                f"line range {start_line}-{end_line} exceeds file length {line_count}"
            )

    def write_note(self, note_path: str, content: str, create_only: bool = False) -> Path:
        path = self.resolve_note(note_path)
        if path.suffix.lower() != ".md":
            raise VaultError("only markdown files are supported (.md)")
        if create_only and path.exists():
            raise VaultError(f"note already exists: {note_path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def append_note(self, note_path: str, content: str) -> Path:
        path = self.resolve_note(note_path)
        if path.suffix.lower() != ".md":
            raise VaultError("only markdown files are supported (.md)")
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
