from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from obsidian_cli.vault import ObsidianVault, VaultError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="obsidian-cli",
        description="Read and write notes inside a local Obsidian vault.",
    )
    parser.add_argument(
        "--vault",
        help="Path to the Obsidian vault. Falls back to OBSIDIAN_VAULT.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("check", help="Validate the vault path.")

    list_parser = subparsers.add_parser("list", help="List markdown notes.")
    list_parser.add_argument("--limit", type=int, default=0, help="Maximum number of notes to show.")

    read_parser = subparsers.add_parser("read", help="Read a note.")
    read_parser.add_argument("note_path", help="Path to the note relative to the vault root.")

    read_lines_parser = subparsers.add_parser("read-lines", help="Read a line range from a note.")
    read_lines_parser.add_argument("note_path", help="Path to the note relative to the vault root.")
    read_lines_parser.add_argument("start_line", type=int, help="1-based start line, inclusive.")
    read_lines_parser.add_argument("end_line", type=int, help="1-based end line, inclusive.")

    write_parser = subparsers.add_parser("write", help="Write a note.")
    write_parser.add_argument("note_path", help="Path to the note relative to the vault root.")
    write_parser.add_argument("--content", help="Text content to write.")
    write_parser.add_argument("--stdin", action="store_true", help="Read note content from stdin.")
    write_parser.add_argument(
        "--create-only",
        action="store_true",
        help="Fail if the note already exists.",
    )

    append_parser = subparsers.add_parser("append", help="Append to a note.")
    append_parser.add_argument("note_path", help="Path to the note relative to the vault root.")
    append_parser.add_argument("--content", help="Text content to append.")
    append_parser.add_argument("--stdin", action="store_true", help="Read appended content from stdin.")

    write_lines_parser = subparsers.add_parser(
        "write-lines",
        help="Replace a line range inside a note.",
    )
    write_lines_parser.add_argument("note_path", help="Path to the note relative to the vault root.")
    write_lines_parser.add_argument("start_line", type=int, help="1-based start line, inclusive.")
    write_lines_parser.add_argument("end_line", type=int, help="1-based end line, inclusive.")
    write_lines_parser.add_argument("--content", help="Replacement text for the selected lines.")
    write_lines_parser.add_argument("--stdin", action="store_true", help="Read replacement text from stdin.")

    search_parser = subparsers.add_parser("search", help="Search text in notes.")
    search_parser.add_argument("query", help="Text to search for.")
    search_parser.add_argument(
        "--case-sensitive",
        action="store_true",
        help="Use case-sensitive matching.",
    )

    return parser


def resolve_vault_path(cli_value: str | None) -> Path:
    raw_value = cli_value or os.environ.get("OBSIDIAN_VAULT")
    if not raw_value:
        raise VaultError("vault path is required; use --vault or OBSIDIAN_VAULT")
    return Path(raw_value)


def read_content_arg(content: str | None, use_stdin: bool) -> str:
    if content is not None and use_stdin:
        raise VaultError("use either --content or --stdin, not both")
    if content is not None:
        return content
    if use_stdin:
        return sys.stdin.read()
    raise VaultError("content is required; provide --content or --stdin")


def cmd_check(vault: ObsidianVault) -> int:
    if not vault.exists():
        raise VaultError(f"vault does not exist: {vault.root}")
    print(f"vault: {vault.root}")
    if vault.is_obsidian_vault():
        print("status: ok (.obsidian found)")
    else:
        print("status: warning (.obsidian not found)")
    return 0


def cmd_list(vault: ObsidianVault, limit: int) -> int:
    notes = vault.list_notes()
    if limit > 0:
        notes = notes[:limit]
    for note in notes:
        print(note)
    return 0


def cmd_read(vault: ObsidianVault, note_path: str) -> int:
    print(vault.read_note(note_path), end="")
    return 0


def cmd_read_lines(vault: ObsidianVault, note_path: str, start_line: int, end_line: int) -> int:
    print(vault.read_note_lines(note_path, start_line, end_line), end="")
    return 0


def cmd_write(vault: ObsidianVault, note_path: str, content: str, create_only: bool) -> int:
    path = vault.write_note(note_path, content, create_only=create_only)
    print(path)
    return 0


def cmd_append(vault: ObsidianVault, note_path: str, content: str) -> int:
    path = vault.append_note(note_path, content)
    print(path)
    return 0


def cmd_write_lines(
    vault: ObsidianVault,
    note_path: str,
    start_line: int,
    end_line: int,
    content: str,
) -> int:
    path = vault.write_note_lines(note_path, start_line, end_line, content)
    print(path)
    return 0


def cmd_search(vault: ObsidianVault, query: str, case_sensitive: bool) -> int:
    matches = vault.search(query, case_sensitive=case_sensitive)
    for match in matches:
        print(f"{match.note_path}:{match.line_number}: {match.line_text}")
    return 0 if matches else 1


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        vault = ObsidianVault(resolve_vault_path(args.vault))

        if args.command == "check":
            return cmd_check(vault)
        if args.command == "list":
            return cmd_list(vault, args.limit)
        if args.command == "read":
            return cmd_read(vault, args.note_path)
        if args.command == "read-lines":
            return cmd_read_lines(vault, args.note_path, args.start_line, args.end_line)
        if args.command == "write":
            content = read_content_arg(args.content, args.stdin)
            return cmd_write(vault, args.note_path, content, args.create_only)
        if args.command == "append":
            content = read_content_arg(args.content, args.stdin)
            return cmd_append(vault, args.note_path, content)
        if args.command == "write-lines":
            content = read_content_arg(args.content, args.stdin)
            return cmd_write_lines(
                vault,
                args.note_path,
                args.start_line,
                args.end_line,
                content,
            )
        if args.command == "search":
            return cmd_search(vault, args.query, args.case_sensitive)
    except VaultError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    parser.error(f"unsupported command: {args.command}")
    return 2
