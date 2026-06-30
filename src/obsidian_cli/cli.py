from __future__ import annotations

import argparse
import os
import sys

from obsidian_cli.commands import CommandRunner
from obsidian_cli.discovery import VaultLocator
from obsidian_cli.plugins import SkillInstaller
from obsidian_cli.ssh_config import (
    SshAliasConfig,
    SshConfigLocator,
    default_identity_file,
    default_ssh_user,
)
from obsidian_cli.vault import (
    ObsidianVault,
    SshConfig,
    SshObsidianVault,
    VaultBackend,
    VaultError,
)


_KNOWN_COMMANDS = {
    "check",
    "list",
    "read",
    "read-lines",
    "write",
    "append",
    "write-lines",
    "search",
    "plugin",
}

_GLOBAL_VALUE_FLAGS = {
    "--vault",
    "--ssh-host",
    "--ssh-user",
    "--ssh-port",
    "--ssh-identity",
    "--ssh-alias",
}


class ObsidianCLI:
    def __init__(
        self,
        vault_locator: VaultLocator | None = None,
        ssh_config_locator: SshConfigLocator | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        self._env = dict(os.environ if env is None else env)
        self._vault_locator = vault_locator or VaultLocator(env=self._env)
        self._ssh_config_locator = ssh_config_locator or SshConfigLocator()
        self._skill_installer = SkillInstaller()
        self._parser = self._build_parser()

    def run(self, argv: list[str] | None = None) -> int:
        if argv is None:
            argv = sys.argv[1:]
        argv = self._inject_alias(argv)
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
            description="Read and write notes inside a local or remote Obsidian vault.",
        )
        parser.add_argument(
            "--vault",
            help="Path to the Obsidian vault. Falls back to OBSIDIAN_VAULT/ODCLI_VAULT.",
        )
        parser.add_argument(
            "--ssh-alias",
            help=(
                "SSH host alias as defined in ~/.ssh/config. "
                "Equivalent to: odcli <alias> <command>."
            ),
        )
        parser.add_argument(
            "--ssh-host",
            help="SSH host for a remote vault. Falls back to ODCLI_SSH_HOST.",
        )
        parser.add_argument(
            "--ssh-user",
            help="SSH username. Falls back to ODCLI_SSH_USER or the current OS user.",
        )
        parser.add_argument(
            "--ssh-port",
            type=int,
            help="SSH port. Falls back to ODCLI_SSH_PORT or the alias config.",
        )
        parser.add_argument(
            "--ssh-identity",
            help=(
                "SSH identity file. Falls back to ODCLI_SSH_IDENTITY, the alias "
                "config, or auto-discovery in ~/.ssh."
            ),
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
        host = args.ssh_host or self._env.get("ODCLI_SSH_HOST")
        user = args.ssh_user or self._env.get("ODCLI_SSH_USER")
        port = args.ssh_port
        if port is None:
            env_port = self._env.get("ODCLI_SSH_PORT")
            if env_port:
                try:
                    port = int(env_port)
                except ValueError as exc:
                    raise VaultError(
                        f"ODCLI_SSH_PORT must be an integer, got: {env_port}"
                    ) from exc
        identity = args.ssh_identity or self._env.get("ODCLI_SSH_IDENTITY")

        alias_config: SshAliasConfig | None = None
        alias = args.ssh_alias
        if alias:
            alias_config = self._ssh_config_locator.resolve_alias(alias)
            if alias_config is None:
                # Mirror ssh: an unknown alias is treated as a literal hostname.
                host = host or alias
            else:
                host = host or alias_config.host_name or alias
                user = user or alias_config.user
                port = port or alias_config.port
                identity = identity or alias_config.identity_file

        if not host:
            return ObsidianVault(self._vault_locator.resolve(args.vault))

        user = user or default_ssh_user()
        if identity is None:
            identity = default_identity_file()

        ssh_root = self._vault_locator.resolve_configured(args.vault)
        return SshObsidianVault(
            str(ssh_root),
            SshConfig(
                host=host,
                user=user,
                port=port,
                identity_file=identity,
            ),
        )

    @staticmethod
    def _read_content_arg(content: str | None, use_stdin: bool) -> str:
        if content is not None and use_stdin:
            raise VaultError("use either --content or --stdin, not both")
        if content is not None:
            return content
        if use_stdin:
            return sys.stdin.read()
        raise VaultError("content is required; provide --content or --stdin")

    @staticmethod
    def _inject_alias(argv: list[str] | None) -> list[str]:
        """Rewrite ``odcli vm list`` into ``odcli --ssh-alias vm list``.

        Scans the global-flags zone (before the subcommand) for the first bare
        positional argument that is not a known subcommand and treats it as an
        SSH alias. Flags that consume a value are skipped so their values are
        not mistaken for aliases.
        """
        if not argv:
            return argv
        tokens = list(argv)
        i = 0
        while i < len(tokens):
            arg = tokens[i]
            if arg == "--":
                return tokens
            if arg in _GLOBAL_VALUE_FLAGS:
                i += 2
                continue
            if arg.startswith("--") and "=" in arg:
                i += 1
                continue
            if arg.startswith("-"):
                i += 1
                continue
            if arg in _KNOWN_COMMANDS:
                return tokens
            return tokens[:i] + ["--ssh-alias", arg] + tokens[i + 1 :]
        return tokens


def main(argv: list[str] | None = None) -> int:
    return ObsidianCLI().run(argv)
