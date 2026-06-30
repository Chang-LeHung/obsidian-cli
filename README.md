# odcli

CLI for reading and writing Obsidian vault notes — locally or over SSH.

`odcli` operates directly on Markdown files, so it needs no Obsidian API or
running Obsidian instance. Point it at a local vault or connect to a remote
machine the same way you would with `ssh`.

## Install

```bash
pip install odcli
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv tool install odcli
```

After installation both `odcli` and `obsidian-cli` are available.

## Quick start

### Local vault

`odcli` auto-discovers the vault from your Obsidian config or common default
locations. No setup needed in most cases:

```bash
odcli list
odcli read Inbox/today.md
```

To point at a specific vault:

```bash
export OBSIDIAN_VAULT="/path/to/MyVault"   # or ODCLI_VAULT
odcli list
```

Or per-command:

```bash
odcli --vault "/path/to/MyVault" list
```

### Remote vault over SSH

If the host is in your `~/.ssh/config`, use it like `ssh`:

```bash
odcli myserver list
odcli myserver read Inbox/today.md
odcli myserver write Inbox/today.md --content "# Hello"
```

Or use explicit flags:

```bash
odcli --ssh-host myserver --ssh-user me list
```

## SSH details

### How the alias is resolved

`odcli myserver list` is rewritten to `odcli --ssh-alias myserver list`.
`HostName`, `User`, `Port`, and `IdentityFile` are pulled from `~/.ssh/config`
(including `Include`-d files). Any explicit flag or environment variable
overrides the config value.

### Environment variables

Set defaults in your shell profile so you never have to repeat flags:

| Variable | Description |
|---|---|
| `ODCLI_SSH_HOST` | SSH host |
| `ODCLI_SSH_USER` | SSH username |
| `ODCLI_SSH_PORT` | SSH port |
| `ODCLI_SSH_IDENTITY` | SSH private key path |
| `ODCLI_VAULT` / `OBSIDIAN_VAULT` | Vault path (local or remote) |

### Resolution order

Each SSH field is resolved in this order:

1. CLI flag (`--ssh-host`, `--ssh-user`, `--ssh-port`, `--ssh-identity`)
2. Environment variable (`ODCLI_SSH_*`)
3. `~/.ssh/config` entry for the alias
4. Built-in default:
   - **user** — current OS user
   - **identity** — first key found in `~/.ssh` (`id_ed25519` > `id_ecdsa` > `id_rsa`)
   - **vault** — `~/Documents/Obsidian Vault` (macOS/Linux) or `Documents\Obsidian Vault` (Windows)

## Commands

| Command | Description |
|---|---|
| `check` | Validate the vault path |
| `list [--limit N]` | List Markdown notes |
| `read <note>` | Print a note |
| `read-lines <note> <start> <end>` | Print a line range (1-based, inclusive) |
| `write <note> --content TEXT` | Create or overwrite a note |
| `write-lines <note> <start> <end> --content TEXT` | Replace a line range |
| `append <note> --content TEXT` | Append to a note |
| `search <query> [--case-sensitive]` | Full-text search across all notes |

All write commands accept `--stdin` instead of `--content` to read from stdin.
`write` also accepts `--create-only` to fail if the note already exists.

## AI coding assistant integration

`odcli` can install helper skills so AI coding tools know how to use it:

```bash
odcli plugin install all-skills   # Codex + Claude Code
odcli plugin install codex-skill  # Codex only
odcli plugin install claude-skill # Claude Code only
```

## Vault discovery

When no vault is specified, `odcli` searches in this order:

1. `--vault` flag
2. `OBSIDIAN_VAULT` / `ODCLI_VAULT` environment variable
3. Most recently opened vault from Obsidian's own config
4. Common default directories:
   - macOS: `~/Documents/Obsidian Vault`, `~/Documents/Obsidian`, iCloud
   - Windows: `%USERPROFILE%\Documents\Obsidian Vault`, `%USERPROFILE%\Documents\Obsidian`

## Development

```bash
uv sync                                       # install deps
uv run python -m unittest discover -s tests   # run tests
uv build                                      # build wheel + sdist
```
