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

Example with explicit flags:

```bash
odcli \
  --ssh-host your-server \
  --ssh-user your-user \
  --vault /path/to/ObsidianVault \
  list
```

### SSH config alias (recommended)

If you already have a host defined in `~/.ssh/config`, you can use it the same
way you would with `ssh`:

```bash
odcli vm list
odcli vm read Inbox/today.md
odcli vm write Inbox/today.md --content "# Remote note"
```

The alias form is equivalent to `odcli --ssh-alias vm ...`. `HostName`, `User`,
`Port`, and `IdentityFile` are read from your SSH config, and any explicit flag
or environment variable overrides the config value.

### Environment variables

To avoid repeating the same flags every time, set defaults in your shell:

```bash
export ODCLI_SSH_HOST=your-server
export ODCLI_SSH_USER=your-user
export ODCLI_SSH_PORT=22
export ODCLI_SSH_IDENTITY=~/.ssh/id_ed25519
export ODCLI_VAULT=/path/to/ObsidianVault   # OBSIDIAN_VAULT also works
```

Resolution order for each SSH field:

1. CLI flag (`--ssh-host`, `--ssh-user`, `--ssh-port`, `--ssh-identity`)
2. Environment variable (`ODCLI_SSH_HOST`, `ODCLI_SSH_USER`,
   `ODCLI_SSH_PORT`, `ODCLI_SSH_IDENTITY`)
3. `~/.ssh/config` entry for the alias (when using `odcli <alias> ...`)
4. Built-in defaults:
   - **user**: the current OS user (`getpass.getuser()`)
   - **identity file**: first existing key in `~/.ssh` (`id_ed25519`,
     `id_ecdsa`, `id_rsa`)
   - **vault**: OS-aware default path
     - macOS/Linux: `~/Documents/Obsidian Vault`
     - Windows: `Documents\Obsidian Vault`

For the identity file, either set `ODCLI_SSH_IDENTITY` explicitly or rely on
auto-discovery — you do not need both.

Optional SSH flags:

- `--ssh-port`
- `--ssh-identity`
- `--ssh-alias`

In SSH mode, `--vault`, `ODCLI_VAULT`, or `OBSIDIAN_VAULT` should point to the
remote vault path. If none is provided, an OS-aware default is used.

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
- `--ssh-alias` (or the bare `odcli <alias> <command>` form)
- `--ssh-host`
- `--ssh-user`
- `--ssh-port`
- `--ssh-identity`

### Environment Variables

- `OBSIDIAN_VAULT` / `ODCLI_VAULT`: vault path
- `ODCLI_SSH_HOST`: SSH host
- `ODCLI_SSH_USER`: SSH username
- `ODCLI_SSH_PORT`: SSH port
- `ODCLI_SSH_IDENTITY`: SSH private key path

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
