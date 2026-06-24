from __future__ import annotations

from obsidian_cli.vault import VaultBackend, VaultError


class CommandRunner:
    def __init__(self, vault: VaultBackend) -> None:
        self._vault = vault

    def check(self) -> int:
        if not self._vault.exists():
            raise VaultError(f"vault does not exist: {self._vault.root}")
        print(f"vault: {self._vault.root}")
        if self._vault.is_obsidian_vault():
            print("status: ok (.obsidian found)")
        else:
            print("status: warning (.obsidian not found)")
        return 0

    def list_notes(self, limit: int) -> int:
        notes = self._vault.list_notes()
        if limit > 0:
            notes = notes[:limit]
        for note in notes:
            print(note)
        return 0

    def read_note(self, note_path: str) -> int:
        print(self._vault.read_note(note_path), end="")
        return 0

    def read_note_lines(self, note_path: str, start_line: int, end_line: int) -> int:
        print(self._vault.read_note_lines(note_path, start_line, end_line), end="")
        return 0

    def write_note(self, note_path: str, content: str, create_only: bool) -> int:
        print(self._vault.write_note(note_path, content, create_only=create_only))
        return 0

    def append_note(self, note_path: str, content: str) -> int:
        print(self._vault.append_note(note_path, content))
        return 0

    def write_note_lines(
        self,
        note_path: str,
        start_line: int,
        end_line: int,
        content: str,
    ) -> int:
        print(self._vault.write_note_lines(note_path, start_line, end_line, content))
        return 0

    def search(self, query: str, case_sensitive: bool) -> int:
        matches = self._vault.search(query, case_sensitive=case_sensitive)
        for match in matches:
            print(f"{match.note_path}:{match.line_number}: {match.line_text}")
        return 0 if matches else 1
