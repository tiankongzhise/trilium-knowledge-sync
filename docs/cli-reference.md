# trilium_etapi.py CLI 参考

helper 路径：

```text
skill/trilium-knowledge-sync/scripts/trilium_etapi.py
```

所有命令都需要 token 位置，但不接受 token 值：

```bash
python trilium_etapi.py --token-source '<位置>' [--base-url '<url>'] <command>
```

## 全局参数

| 参数 | 说明 |
|---|---|
| `--token-source` | `win-cred:<target>`、`file:<path>` 或 `env:<name>`；也可用 `TRILIUM_TOKEN_SOURCE` |
| `--base-url` | ETAPI base URL；例如 `http://127.0.0.1:37840/etapi` |
| `--timeout` | HTTP 超时秒数，默认 15 |
| `--debug` | 显示完整异常栈；仅在受控环境使用 |
| `--version` | 输出版本 |

## app-info

验证 token 与 ETAPI 连通性：

```bash
python trilium_etapi.py --token-source 'env:TRILIUM_TOKEN' app-info
```

输出 Trilium 应用信息 JSON。

## get-note

```bash
python trilium_etapi.py --token-source '<位置>' get-note '<noteId>'
```

输出 note metadata JSON，包括 title/type/mime/parentNoteIds/childNoteIds。

## get-content

输出到 stdout：

```bash
python trilium_etapi.py --token-source '<位置>' get-content '<noteId>'
```

写入 UTF-8 文件：

```bash
python trilium_etapi.py --token-source '<位置>' get-content '<noteId>' --output '<path>'
```

写文件模式输出 JSON：noteId、output、contentSha256。

## list-children

```bash
python trilium_etapi.py --token-source '<位置>' list-children '<parentNoteId>'
```

输出直接子笔记数组；deleted child 会被过滤。

## find-child

```bash
python trilium_etapi.py --token-source '<位置>' find-child '<parentNoteId>' '<exact title>'
```

精确标题匹配，输出**匹配数组**（0.x breaking）：找不到输出 `[]`，找到一个输出单元素数组，存在多个同名未删除笔记时输出全部——helper 绝不静默替你选择其中一个。数组元素为完整 note metadata，可用 `noteId`/`type`/`mime`/`utcDateModified` 等字段区分候选。

## search

```bash
python trilium_etapi.py --token-source '<位置>' search '<query>' --limit 10 --fast
```

`--fast` 对应 Trilium fastSearch，不查正文内容。

## create-note

```bash
python trilium_etapi.py \
  --token-source '<位置>' \
  create-note \
  --parent-id '<parentNoteId>' \
  --title '<title>' \
  --type code \
  --mime text/x-markdown \
  --content-file '<path>' \
  --position 10 \
  --expanded
```

`--content-file` 省略时创建空内容笔记；`--content-file -` 从 stdin 读内容（stdin 仅用于笔记内容，不能用作 token 通道）。

## patch-note

```bash
python trilium_etapi.py --token-source '<位置>' patch-note '<noteId>' \
  --title '<new title>' \
  --type code \
  --mime text/x-markdown
```

至少提供一个字段。适合修正 note metadata；不涉及 branch 位置。

## put-content

```bash
python trilium_etapi.py --token-source '<位置>' put-content '<noteId>' --content-file '<path>'
```

替换正文后会重新读取核验。输出包含 `verified: true` 时才表示核验通过。

## upsert-note

```bash
python trilium_etapi.py \
  --token-source '<位置>' \
  upsert-note \
  --parent-id '<parentNoteId>' \
  --title '<exact title>' \
  --type code \
  --mime text/x-markdown \
  --content-file '<path>' \
  --position 10 \
  --expanded
```

行为：

1. 在指定父笔记下按精确标题查找未删除 child。
2. **存在多个同名未删除 child 时拒绝执行**，非零退出，stderr 列出全部候选的 `noteId`、`type`、`mime`、`utcDateModified` 等辨识信息；不静默选择。此时应在 Trilium 中人工处理重复（重命名/移动/删除），或用精确 noteId 通过 `patch-note`/`put-content` 定点操作。
3. 不存在则创建。
4. 存在唯一匹配则必要时 patch type/MIME。
5. 正文 hash 不同则替换。
6. 写入后重新读取父关系或正文核验。

输出字段：

- `action`: `created` / `updated` / `unchanged`；`updated` 可能表示正文、type 或 MIME 被修正
- `noteId`
- `parentNoteId`
- `title`
- `type`
- `mime`
- `contentSha256`
- `verified`

## 不提供的能力

helper 故意不提供 delete、批量移动、批量重命名、直接 SQLite、凭据扫描等命令。需要这些操作时，应回到用户明确授权和单独设计流程。
