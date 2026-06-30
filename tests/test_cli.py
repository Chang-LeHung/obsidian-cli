from __future__ import annotations

import sys
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from obsidian_cli.cli import ObsidianCLI, main
from obsidian_cli.discovery import VaultCandidate, VaultLocator
from obsidian_cli.plugins import SkillInstaller
from obsidian_cli.vault import ObsidianVault, SshConfig, SshObsidianVault, VaultError


class VaultTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.vault_root = Path(self.temp_dir.name) / "vault"
        self.vault_root.mkdir()
        (self.vault_root / ".obsidian").mkdir()
        self.vault = ObsidianVault(self.vault_root)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_write_and_read_note(self) -> None:
        self.vault.write_note("Inbox/test.md", "# Hello")
        self.assertEqual(self.vault.read_note("Inbox/test.md"), "# Hello")

    def test_list_notes_excludes_obsidian_config(self) -> None:
        self.vault.write_note("Note.md", "body")
        (self.vault_root / ".obsidian" / "workspace.md").write_text(
            "ignored", encoding="utf-8"
        )
        self.assertEqual(self.vault.list_notes(), ["Note.md"])

    def test_search_matches_line(self) -> None:
        self.vault.write_note("Note.md", "alpha\nbeta project\nomega")
        matches = self.vault.search("project")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].line_number, 2)

    def test_read_note_lines(self) -> None:
        self.vault.write_note("Note.md", "a\nb\nc\nd\n")
        self.assertEqual(self.vault.read_note_lines("Note.md", 2, 3), "b\nc\n")

    def test_write_note_lines_replaces_only_selected_range(self) -> None:
        self.vault.write_note("Note.md", "a\nb\nc\nd\n")
        self.vault.write_note_lines("Note.md", 2, 3, "x\ny\n")
        self.assertEqual(self.vault.read_note("Note.md"), "a\nx\ny\nd\n")

    def test_write_note_lines_rejects_invalid_range(self) -> None:
        self.vault.write_note("Note.md", "a\nb\n")
        with self.assertRaises(VaultError):
            self.vault.write_note_lines("Note.md", 2, 4, "x\n")

    def test_cli_check(self) -> None:
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            exit_code = main(["--vault", str(self.vault_root), "check"])
        self.assertEqual(exit_code, 0)

    def test_cli_write_requires_content(self) -> None:
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            exit_code = main(["--vault", str(self.vault_root), "write", "x.md"])
        self.assertEqual(exit_code, 2)

    def test_cli_read_lines(self) -> None:
        self.vault.write_note("Note.md", "a\nb\nc\n")
        stdout = StringIO()
        with redirect_stdout(stdout), redirect_stderr(StringIO()):
            exit_code = main(
                ["--vault", str(self.vault_root), "read-lines", "Note.md", "2", "3"]
            )
        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue(), "b\nc\n")

    def test_cli_write_lines(self) -> None:
        self.vault.write_note("Note.md", "a\nb\nc\n")
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            exit_code = main(
                [
                    "--vault",
                    str(self.vault_root),
                    "write-lines",
                    "Note.md",
                    "2",
                    "2",
                    "--content",
                    "beta\n",
                ]
            )
        self.assertEqual(exit_code, 0)
        self.assertEqual(self.vault.read_note("Note.md"), "a\nbeta\nc\n")

    def test_vault_locator_prefers_env_var(self) -> None:
        locator = VaultLocator(
            env={"OBSIDIAN_VAULT": str(self.vault_root)}, home=self.vault_root
        )
        self.assertEqual(locator.resolve(None), self.vault_root)

    def test_vault_locator_resolve_configured_uses_ssh_default(self) -> None:
        locator = VaultLocator(env={}, home=self.vault_root)
        result = locator.resolve_configured(None)
        self.assertIsNotNone(result)

    def test_vault_locator_resolve_configured_prefers_env(self) -> None:
        locator = VaultLocator(
            env={"OBSIDIAN_VAULT": "/remote/vault"}, home=self.vault_root
        )
        self.assertEqual(locator.resolve_configured(None), Path("/remote/vault"))

    def test_vault_locator_resolve_configured_accepts_odcli_vault_env(self) -> None:
        locator = VaultLocator(
            env={"ODCLI_VAULT": "/remote/vault"}, home=self.vault_root
        )
        self.assertEqual(locator.resolve_configured(None), Path("/remote/vault"))

    def test_vault_locator_discovers_default_vault(self) -> None:
        locator = VaultLocator(env={}, home=self.vault_root.parent)
        with patch.object(locator, "_discover_from_obsidian_config", return_value=None):
            with patch.object(
                locator,
                "_iter_default_candidates",
                return_value=[VaultCandidate(source="default", path=self.vault_root)],
            ):
                self.assertEqual(locator.resolve(None), self.vault_root)

    def test_vault_locator_uses_obsidian_config_first(self) -> None:
        config_vault = self.vault_root / "Configured"
        config_vault.mkdir()
        (config_vault / ".obsidian").mkdir()
        locator = VaultLocator(env={}, home=self.vault_root)
        with patch.object(
            locator,
            "_discover_from_obsidian_config",
            return_value=VaultCandidate(source="config", path=config_vault),
        ):
            self.assertEqual(locator.resolve(None), config_vault)

    def test_cli_can_receive_custom_locator(self) -> None:
        locator = VaultLocator(
            env={"OBSIDIAN_VAULT": str(self.vault_root)}, home=self.vault_root
        )
        cli = ObsidianCLI(vault_locator=locator)
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            exit_code = cli.run(["check"])
        self.assertEqual(exit_code, 0)

    def test_skill_installer_installs_codex_skill(self) -> None:
        installer = SkillInstaller(home=self.vault_root)
        results = installer.install("codex-skill")
        self.assertEqual(len(results), 1)
        skill_path = self.vault_root / ".codex" / "skills" / "odcli" / "SKILL.md"
        self.assertTrue(skill_path.is_file())
        self.assertTrue(skill_path.read_text(encoding="utf-8").startswith("---\n"))

    def test_skill_installer_installs_claude_skill(self) -> None:
        installer = SkillInstaller(home=self.vault_root)
        results = installer.install("claude-skill")
        self.assertEqual(len(results), 1)
        skill_path = self.vault_root / ".claude" / "skills" / "odcli" / "SKILL.md"
        self.assertTrue(skill_path.is_file())
        self.assertTrue(skill_path.read_text(encoding="utf-8").startswith("---\n"))

    def test_cli_plugin_install_all_skills(self) -> None:
        cli = ObsidianCLI(vault_locator=VaultLocator(env={}, home=self.vault_root))
        cli._skill_installer = SkillInstaller(home=self.vault_root)
        stdout = StringIO()
        with redirect_stdout(stdout), redirect_stderr(StringIO()):
            exit_code = cli.run(["plugin", "install", "all-skills"])
        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("codex-skill:", output)
        self.assertIn("claude-skill:", output)

    def test_ssh_vault_list_notes(self) -> None:
        def fake_runner(
            command: list[str], **_: object
        ) -> subprocess.CompletedProcess[str]:
            if "test -d" in command[-1]:
                return subprocess.CompletedProcess(command, 0, "", "")
            if "find ." in command[-1]:
                return subprocess.CompletedProcess(
                    command,
                    0,
                    "Inbox/today.md\nProjects/alpha.md\n",
                    "",
                )
            return subprocess.CompletedProcess(command, 1, "", "unexpected command")

        vault = SshObsidianVault(
            "/vault", SshConfig(host="example.com"), runner=fake_runner
        )
        self.assertEqual(vault.list_notes(), ["Inbox/today.md", "Projects/alpha.md"])

    def test_ssh_vault_write_and_read_note(self) -> None:
        written: dict[str, str] = {}

        def fake_runner(
            command: list[str], **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            remote_command = command[-1]
            if "test -f" in remote_command:
                exists = "/vault/Inbox/test.md" in written
                return subprocess.CompletedProcess(command, 0 if exists else 1, "", "")
            if "mkdir -p" in remote_command and "cat >" in remote_command:
                written["/vault/Inbox/test.md"] = str(kwargs.get("input", ""))
                return subprocess.CompletedProcess(command, 0, "", "")
            if remote_command == "cat /vault/Inbox/test.md":
                return subprocess.CompletedProcess(
                    command,
                    0,
                    written["/vault/Inbox/test.md"],
                    "",
                )
            return subprocess.CompletedProcess(command, 1, "", "unexpected command")

        vault = SshObsidianVault(
            "/vault", SshConfig(host="example.com"), runner=fake_runner
        )
        vault.write_note("Inbox/test.md", "# Hello\n")
        self.assertEqual(vault.read_note("Inbox/test.md"), "# Hello\n")

    def test_cli_builds_ssh_vault_when_requested(self) -> None:
        cli = ObsidianCLI(
            vault_locator=VaultLocator(
                env={"OBSIDIAN_VAULT": "/remote/vault"}, home=self.vault_root
            ),
            env={},
        )
        vault = cli._build_vault(
            type(
                "Args",
                (),
                {
                    "vault": None,
                    "ssh_alias": None,
                    "ssh_host": "example.com",
                    "ssh_user": "alice",
                    "ssh_port": 2222,
                    "ssh_identity": "~/.ssh/id_ed25519",
                },
            )()
        )
        self.assertIsInstance(vault, SshObsidianVault)

    def test_cli_ssh_alias_injection_rewrites_bare_positional(self) -> None:
        rewritten = ObsidianCLI._inject_alias(["vm", "list"])
        self.assertEqual(rewritten, ["--ssh-alias", "vm", "list"])

    def test_cli_ssh_alias_injection_skips_known_command(self) -> None:
        rewritten = ObsidianCLI._inject_alias(["list"])
        self.assertEqual(rewritten, ["list"])

    def test_cli_ssh_alias_injection_skips_flag_values(self) -> None:
        rewritten = ObsidianCLI._inject_alias(["--vault", "my-vault", "vm", "list"])
        self.assertEqual(
            rewritten, ["--vault", "my-vault", "--ssh-alias", "vm", "list"]
        )

    def test_cli_ssh_alias_injection_skips_equals_flag_values(self) -> None:
        rewritten = ObsidianCLI._inject_alias(["--vault=my-vault", "list"])
        self.assertEqual(rewritten, ["--vault=my-vault", "list"])

    def test_ssh_config_locator_resolves_alias(self) -> None:
        from obsidian_cli.ssh_config import SshConfigLocator

        config = self.vault_root / ".ssh" / "config"
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(
            "Host vm\n"
            "  HostName 172.20.10.11\n"
            "  User huchang\n"
            "  Port 2222\n"
            "  IdentityFile ~/.ssh/id_ed25519\n",
            encoding="utf-8",
        )
        locator = SshConfigLocator(config_path=config)
        resolved = locator.resolve_alias("vm")
        self.assertIsNotNone(resolved)
        assert resolved is not None
        self.assertEqual(resolved.host_name, "172.20.10.11")
        self.assertEqual(resolved.user, "huchang")
        self.assertEqual(resolved.port, 2222)
        self.assertEqual(
            resolved.identity_file,
            str(Path.home() / ".ssh" / "id_ed25519"),
        )

    def test_ssh_config_locator_returns_none_for_unknown_alias(self) -> None:
        from obsidian_cli.ssh_config import SshConfigLocator

        config = self.vault_root / ".ssh" / "config"
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text("Host other\n  HostName 1.2.3.4\n", encoding="utf-8")
        locator = SshConfigLocator(config_path=config)
        self.assertIsNone(locator.resolve_alias("vm"))

    def test_cli_builds_ssh_vault_from_alias(self) -> None:
        from obsidian_cli.ssh_config import SshConfigLocator

        config = self.vault_root / ".ssh" / "config"
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(
            "Host vm\n"
            "  HostName 172.20.10.11\n"
            "  User huchang\n"
            "  Port 2222\n"
            "  IdentityFile ~/.ssh/id_ed25519\n",
            encoding="utf-8",
        )
        cli = ObsidianCLI(
            vault_locator=VaultLocator(
                env={"OBSIDIAN_VAULT": "/remote/vault"}, home=self.vault_root
            ),
            ssh_config_locator=SshConfigLocator(config_path=config),
            env={},
        )
        vault = cli._build_vault(
            type(
                "Args",
                (),
                {
                    "vault": None,
                    "ssh_alias": "vm",
                    "ssh_host": None,
                    "ssh_user": None,
                    "ssh_port": None,
                    "ssh_identity": None,
                },
            )()
        )
        self.assertIsInstance(vault, SshObsidianVault)
        ssh_config = vault._ssh_config  # type: ignore[attr-defined]
        self.assertEqual(ssh_config.host, "172.20.10.11")
        self.assertEqual(ssh_config.user, "huchang")
        self.assertEqual(ssh_config.port, 2222)
        self.assertEqual(
            ssh_config.identity_file, str(Path.home() / ".ssh" / "id_ed25519")
        )

    def test_cli_ssh_env_vars_provide_defaults(self) -> None:
        cli = ObsidianCLI(
            vault_locator=VaultLocator(
                env={"OBSIDIAN_VAULT": "/remote/vault"}, home=self.vault_root
            ),
            env={
                "ODCLI_SSH_HOST": "example.com",
                "ODCLI_SSH_USER": "bob",
                "ODCLI_SSH_PORT": "2222",
            },
        )
        vault = cli._build_vault(
            type(
                "Args",
                (),
                {
                    "vault": None,
                    "ssh_alias": None,
                    "ssh_host": None,
                    "ssh_user": None,
                    "ssh_port": None,
                    "ssh_identity": None,
                },
            )()
        )
        self.assertIsInstance(vault, SshObsidianVault)
        ssh_config = vault._ssh_config  # type: ignore[attr-defined]
        self.assertEqual(ssh_config.host, "example.com")
        self.assertEqual(ssh_config.user, "bob")
        self.assertEqual(ssh_config.port, 2222)

    def test_cli_cli_flag_overrides_ssh_env_var(self) -> None:
        cli = ObsidianCLI(
            vault_locator=VaultLocator(
                env={"OBSIDIAN_VAULT": "/remote/vault"}, home=self.vault_root
            ),
            env={"ODCLI_SSH_HOST": "example.com", "ODCLI_SSH_USER": "bob"},
        )
        vault = cli._build_vault(
            type(
                "Args",
                (),
                {
                    "vault": None,
                    "ssh_alias": None,
                    "ssh_host": "override.com",
                    "ssh_user": None,
                    "ssh_port": None,
                    "ssh_identity": None,
                },
            )()
        )
        self.assertIsInstance(vault, SshObsidianVault)
        ssh_config = vault._ssh_config  # type: ignore[attr-defined]
        self.assertEqual(ssh_config.host, "override.com")
        self.assertEqual(ssh_config.user, "bob")


if __name__ == "__main__":
    unittest.main()
