# odcli

`odcli` is a command-line tool for reading and writing notes in a local Obsidian vault.

It works directly on Markdown files inside the vault, so you can use it without any private Obsidian API.

## Install

From PyPI:

```bash
pip install odcli
```

Or with `uv`:

```bash
uv tool install odcli
```

After installation, both command names are available:

```bash
odcli --help
obsidian-cli --help
```

## Quickstart

If your vault is already in a common location, `odcli` can usually find it automatically:

```bash
odcli check
odcli list
```

If you want to set the vault explicitly:

```bash
export OBSIDIAN_VAULT="/path/to/MyVault"
odcli check
```

You can also override the vault per command:

```bash
odcli --vault "/path/to/MyVault" list
```

## Remote Vault over SSH

You can operate on an Obsidian vault stored on another machine over SSH.

Example:

```bash
odcli \
  --ssh-host your-server \
  --ssh-user your-user \
  --vault /path/to/ObsidianVault \
  list
```

Read a remote note:

```bash
odcli \
  --ssh-host your-server \
  --ssh-user your-user \
  --vault /path/to/ObsidianVault \
  read Inbox/today.md
```

Write a remote note:

```bash
odcli \
  --ssh-host your-server \
  --ssh-user your-user \
  --vault /path/to/ObsidianVault \
  write Inbox/today.md --content "# Remote note"
```

Optional SSH flags:

- `--ssh-port`
- `--ssh-identity`

In SSH mode, `--vault` or `OBSIDIAN_VAULT` should point to the remote vault path.

## Common Commands

Read a note:

```bash
odcli read Inbox/today.md
```

Read specific lines:

```bash
odcli read-lines Inbox/today.md 3 8
```

Create or overwrite a note:

```bash
odcli write Inbox/today.md --content "# Today"
```

Replace a line range:

```bash
odcli write-lines Inbox/today.md 3 4 --content "- replaced\n- lines\n"
```

Append content:

```bash
odcli append Inbox/today.md --content "\n- new item"
```

Search across the vault:

```bash
odcli search "project alpha"
```

## Skill Install

`odcli` can install helper skills for local coding tools.

Install into Codex:

```bash
odcli plugin install codex-skill
```

Install into Claude Code:

```bash
odcli plugin install claude-skill
```

Install both:

```bash
odcli plugin install all-skills
```

Installed paths:

- Codex: `~/.codex/skills/odcli/SKILL.md`
- Claude Code: `~/.claude/skills/odcli/SKILL.md`

## Release

Local release to PyPI:

```bash
make pub
```

This runs tests, builds the wheel and source distribution, validates them with `twine check`, and uploads them to PyPI. The upload step temporarily ignores `HTTP_PROXY`, `HTTPS_PROXY`, and related proxy variables.

To publish to another repository such as TestPyPI:

```bash
make pub PYPI_REPOSITORY=testpypi
```

Git tag based release from GitHub:

1. Bump `version` in `pyproject.toml` and `src/obsidian_cli/__init__.py`.
2. Commit and push the version change.
3. Create and push the matching tag:

```bash
make push-tag
```

The GitHub Actions workflow listens for tags like `v0.1.8`, runs tests, builds the package, checks the distributions, and publishes to PyPI automatically.

GitHub repository setup:

1. Add the repository secret `PYPI_API_TOKEN`.
2. Make sure the token has permission to upload the `odcli` project on PyPI.

## Vault Discovery

Resolution priority:

1. `--vault /path/to/vault`
2. `OBSIDIAN_VAULT`
3. The most recently opened vault recorded by local Obsidian config
4. Common default directories

Built-in default locations:

- macOS: `~/Documents/Obsidian Vault`
- macOS: `~/Documents/Obsidian`
- macOS iCloud: `~/Library/Mobile Documents/iCloud~md~obsidian/Documents`
- Windows: `%USERPROFILE%\\Documents\\Obsidian Vault`
- Windows: `%USERPROFILE%\\Documents\\Obsidian`

## Command Summary

### `check`

Validate that the vault exists and report whether `.obsidian` is present.

### `list`

List Markdown notes in the vault.

Optional arguments:

- `--limit N`

### `read`

Read a note.

Arguments:

- `note_path`: path relative to the vault root

### `write`

Overwrite a note. Parent directories are created automatically if needed.

Arguments:

- `note_path`
- `--content TEXT`
- `--stdin`

Optional arguments:

- `--create-only`

### `read-lines`

Read a line range. Line numbers are 1-based and inclusive.

Arguments:

- `note_path`
- `start_line`
- `end_line`

### `write-lines`

Replace a line range. Line numbers are 1-based and inclusive.

Arguments:

- `note_path`
- `start_line`
- `end_line`
- `--content TEXT`
- `--stdin`

### `append`

Append content to the end of a note.

Arguments:

- `note_path`
- `--content TEXT`
- `--stdin`

### `search`

Search across all Markdown notes in the vault.

Arguments:

- `query`
- `--case-sensitive`

## Global Options

- `--vault`
- `--ssh-host`
- `--ssh-user`
- `--ssh-port`
- `--ssh-identity`

## For Developers

Run from source:

```bash
cd path/to/obsidian_cli
uv sync
uv run odcli --help
```

Run tests:

```bash
cd path/to/obsidian_cli
uv run python -m unittest discover -s tests
```

Build distributions:

```bash
cd path/to/obsidian_cli
uv build
```
