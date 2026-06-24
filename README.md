# odcli

`odcli` is a local Python CLI for reading and writing notes in an Obsidian vault.
It works directly on Markdown files inside the vault, so it does not depend on private Obsidian APIs and remains portable and easy to extend.

## Features

- Validate whether a vault path is available
- List Markdown notes in the vault
- Read a specific note
- Read a specific line range from a note
- Overwrite a note or create it automatically
- Replace a specific line range in a note
- Append content to a note
- Full-text search across the vault
- Auto-discover the default vault from Obsidian config or common macOS and Windows locations
- Install odcli helper skills into Codex or Claude Code skill directories

## Using uv

```bash
cd /Users/huchang/agents/obsidian_cli
uv sync
uv run odcli --help
```

Run tests:

```bash
cd /Users/huchang/agents/obsidian_cli
uv run python -m unittest discover -s tests
```

Build distributions:

```bash
cd /Users/huchang/agents/obsidian_cli
uv build
```

The published package name on PyPI is `odcli`.
After installation, both `odcli` and `obsidian-cli` are available as command names.

## Run Locally

```bash
cd /Users/huchang/agents/obsidian_cli
./odcli --help
```

The compatibility entry point is still available:

```bash
cd /Users/huchang/agents/obsidian_cli
./obsidian-cli --help
```

If you prefer module execution:

```bash
PYTHONPATH=src python3 -m obsidian_cli --help
```

## Vault Resolution

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

Example:

```bash
export OBSIDIAN_VAULT="/Users/your-name/Documents/MyVault"
./odcli check
./odcli list
./odcli read Inbox/today.md
./odcli read-lines Inbox/today.md 3 8
./odcli write Inbox/today.md --content "# Today"
./odcli write-lines Inbox/today.md 3 4 --content "- replaced\n- lines\n"
./odcli append Inbox/today.md --content "\n- new item"
./odcli search "project alpha"
```

## Commands

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

### `plugin install`

Install odcli helper skills for local coding tools.

Targets:

- `codex-skill`: installs to `~/.codex/skills/odcli/SKILL.md`
- `claude-skill`: installs to `~/.claude/skills/odcli/SKILL.md`
- `all-skills`: installs both

Examples:

```bash
odcli plugin install codex-skill
odcli plugin install claude-skill
odcli plugin install all-skills
```

## Testing

```bash
cd /Users/huchang/agents/obsidian_cli
uv run python -m unittest discover -s tests
```
