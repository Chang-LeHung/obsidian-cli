from __future__ import annotations

import argparse
import sys

from obsidian_cli.commands import CommandRunner
from obsidian_cli.discovery import VaultLocator
from obsidian_cli.plugins import SkillInstaller
from obsidian_cli.vault import (
    ObsidianVault,
    SshConfig,
    SshObsidianVault,
    VaultBackend,
    VaultError,
)


class ObsidianCLI:
    def __init__(self, vault_locator: VaultLocator | None = None) -> None:
        self._vault_locator = vault_locator or VaultLocator()
        self._skill_installer = SkillInstaller()
        self._parser = self._build_parser()

    def run(self, argv: list[str] | None = None) -> int:
        args = self._parser.parse_args(argv)

        try:
            if args.command == "plugin":
                return self._run_plugin_command(args)

            runner = CommandRunner(self._build_vault(args))

            if args.command == "check":
                return runner.check()
            if args.command == "list":
                return runner.list_notes(args.limit)
            if args.command == "read":
                return runner.read_note(args.note_path)
            if args.command == "read-lines":
                return runner.read_note_lines(
                    args.note_path, args.start_line, args.end_line
                )
            if args.command == "write":
                return runner.write_note(
                    args.note_path,
                    self._read_content_arg(args.content, args.stdin),
                    args.create_only,
                )
            if args.command == "append":
                return runner.append_note(
                    args.note_path,
                    self._read_content_arg(args.content, args.stdin),
                )
            if args.command == "write-lines":
                return runner.write_note_lines(
                    args.note_path,
                    args.start_line,
                    args.end_line,
                    self._read_content_arg(args.content, args.stdin),
                )
            if args.command == "search":
                return runner.search(args.query, args.case_sensitive)
        except VaultError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

        self._parser.error(f"unsupported command: {args.command}")
        return 2

    def _build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="obsidian-cli",
            description="Read and write notes inside a local Obsidian vault.",
        )
        parser.add_argument(
            "--vault",
            help="Path to the Obsidian vault. Falls back to OBSIDIAN_VAULT.",
        )
        parser.add_argument("--ssh-host", help="SSH host for a remote vault.")
        parser.add_argument("--ssh-user", help="SSH username for a remote vault.")
        parser.add_argument("--ssh-port", type=int, help="SSH port for a remote vault.")
        parser.add_argument(
            "--ssh-identity",
            help="SSH identity file used when connecting to a remote vault.",
        )

        subparsers = parser.add_subparsers(dest="command", required=True)
        subparsers.add_parser("check", help="Validate the vault path.")

        list_parser = subparsers.add_parser("list", help="List markdown notes.")
        list_parser.add_argument(
            "--limit", type=int, default=0, help="Maximum number of notes to show."
        )

        read_parser = subparsers.add_parser("read", help="Read a note.")
        read_parser.add_argument(
            "note_path", help="Path to the note relative to the vault root."
        )

        read_lines_parser = subparsers.add_parser(
            "read-lines", help="Read a line range from a note."
        )
        read_lines_parser.add_argument(
            "note_path", help="Path to the note relative to the vault root."
        )
        read_lines_parser.add_argument(
            "start_line", type=int, help="1-based start line, inclusive."
        )
        read_lines_parser.add_argument(
            "end_line", type=int, help="1-based end line, inclusive."
        )

        write_parser = subparsers.add_parser("write", help="Write a note.")
        write_parser.add_argument(
            "note_path", help="Path to the note relative to the vault root."
        )
        write_parser.add_argument("--content", help="Text content to write.")
        write_parser.add_argument(
            "--stdin", action="store_true", help="Read note content from stdin."
        )
        write_parser.add_argument(
            "--create-only",
            action="store_true",
            help="Fail if the note already exists.",
        )

        append_parser = subparsers.add_parser("append", help="Append to a note.")
        append_parser.add_argument(
            "note_path", help="Path to the note relative to the vault root."
        )
        append_parser.add_argument("--content", help="Text content to append.")
        append_parser.add_argument(
            "--stdin", action="store_true", help="Read appended content from stdin."
        )

        write_lines_parser = subparsers.add_parser(
            "write-lines",
            help="Replace a line range inside a note.",
        )
        write_lines_parser.add_argument(
            "note_path", help="Path to the note relative to the vault root."
        )
        write_lines_parser.add_argument(
            "start_line", type=int, help="1-based start line, inclusive."
        )
        write_lines_parser.add_argument(
            "end_line", type=int, help="1-based end line, inclusive."
        )
        write_lines_parser.add_argument(
            "--content", help="Replacement text for the selected lines."
        )
        write_lines_parser.add_argument(
            "--stdin", action="store_true", help="Read replacement text from stdin."
        )

        search_parser = subparsers.add_parser("search", help="Search text in notes.")
        search_parser.add_argument("query", help="Text to search for.")
        search_parser.add_argument(
            "--case-sensitive",
            action="store_true",
            help="Use case-sensitive matching.",
        )

        plugin_parser = subparsers.add_parser(
            "plugin", help="Install odcli helper skills for supported coding tools."
        )
        plugin_subparsers = plugin_parser.add_subparsers(
            dest="plugin_command", required=True
        )
        plugin_install_parser = plugin_subparsers.add_parser(
            "install", help="Install an odcli skill into a supported tool directory."
        )
        plugin_install_parser.add_argument(
            "target",
            choices=["codex-skill", "claude-skill", "all-skills"],
            help="Installation target.",
        )

        return parser

    def _run_plugin_command(self, args: argparse.Namespace) -> int:
        if args.plugin_command == "install":
            for result in self._skill_installer.install(args.target):
                print(f"{result.target}: {result.path}")
            return 0
        self._parser.error(f"unsupported plugin command: {args.plugin_command}")
        return 2

    def _build_vault(self, args: argparse.Namespace) -> VaultBackend:
        if args.ssh_host:
            ssh_root = self._vault_locator.resolve_configured(args.vault)
            return SshObsidianVault(
                str(ssh_root),
                SshConfig(
                    host=args.ssh_host,
                    user=args.ssh_user,
                    port=args.ssh_port,
                    identity_file=args.ssh_identity,
                ),
            )
        return ObsidianVault(self._vault_locator.resolve(args.vault))

    @staticmethod
    def _read_content_arg(content: str | None, use_stdin: bool) -> str:
        if content is not None and use_stdin:
            raise VaultError("use either --content or --stdin, not both")
        if content is not None:
            return content
        if use_stdin:
            return sys.stdin.read()
        raise VaultError("content is required; provide --content or --stdin")


def main(argv: list[str] | None = None) -> int:
    return ObsidianCLI().run(argv)
