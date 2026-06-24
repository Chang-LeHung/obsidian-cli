from __future__ import annotations

import sys
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
from obsidian_cli.vault import ObsidianVault, VaultError


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


if __name__ == "__main__":
    unittest.main()
