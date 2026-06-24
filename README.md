# obsidian-cli

一个基于 Python 的本地 CLI，用来对 Obsidian vault 做读写操作。它直接操作 vault 里的 Markdown 文件，不依赖 Obsidian 的私有接口，因此稳定、可移植，也方便后续扩展。

## 功能

- 校验 vault 路径是否有效
- 列出 vault 中的 Markdown 笔记
- 读取指定笔记
- 按指定行区间读取笔记
- 覆盖写入或自动创建笔记
- 按指定行区间覆盖写入
- 追加内容到笔记末尾
- 在 vault 中全文搜索

## 使用 uv

```bash
cd /Users/huchang/agents/obsidian_cli
uv sync
uv run obsidian-cli --help
```

运行测试：

```bash
cd /Users/huchang/agents/obsidian_cli
uv run python -m unittest discover -s tests
```

构建分发包：

```bash
cd /Users/huchang/agents/obsidian_cli
uv build
```

## 直接运行

```bash
cd /Users/huchang/agents/obsidian_cli
./obsidian-cli --help
```

如果你更喜欢显式调用 Python：

```bash
PYTHONPATH=src python3 -m obsidian_cli --help
```

## 可选安装

如果你想安装到虚拟环境中：

```bash
cd /Users/huchang/agents/obsidian_cli
uv sync
```

## 指定 vault

优先级如下：

1. `--vault /path/to/vault`
2. 环境变量 `OBSIDIAN_VAULT`

示例：

```bash
export OBSIDIAN_VAULT="/Users/your-name/Documents/MyVault"
./obsidian-cli check
./obsidian-cli list
./obsidian-cli read Inbox/today.md
./obsidian-cli read-lines Inbox/today.md 3 8
./obsidian-cli write Inbox/today.md --content "# Today"
./obsidian-cli write-lines Inbox/today.md 3 4 --content "- replaced\n- lines\n"
./obsidian-cli append Inbox/today.md --content "\n- new item"
./obsidian-cli search "project alpha"
```

## 命令

### `check`

检查 vault 是否存在，以及是否包含 `.obsidian` 目录。

### `list`

列出 vault 中的 Markdown 文件。

可选参数：

- `--limit N`

### `read`

读取笔记内容。

参数：

- `note_path`：相对于 vault 根目录的路径

### `write`

覆盖写入笔记；若父目录不存在会自动创建。

参数：

- `note_path`
- `--content TEXT`
- `--stdin`：从标准输入读取内容

可选参数：

- `--create-only`：若文件已存在则报错

### `read-lines`

读取指定行区间，行号从 `1` 开始，区间是闭区间。

参数：

- `note_path`
- `start_line`
- `end_line`

### `write-lines`

用新内容替换指定行区间，行号从 `1` 开始，区间是闭区间。

参数：

- `note_path`
- `start_line`
- `end_line`
- `--content TEXT`
- `--stdin`

### `append`

追加内容到笔记末尾。

参数：

- `note_path`
- `--content TEXT`
- `--stdin`

### `search`

在所有 Markdown 笔记中搜索文本。

参数：

- `query`
- `--case-sensitive`

## 测试

```bash
cd /Users/huchang/agents/obsidian_cli
uv run python -m unittest discover -s tests
```
