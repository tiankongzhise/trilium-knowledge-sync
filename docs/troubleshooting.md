# 故障排查

## `401 Unauthorized`

含义：ETAPI 可达，但 token 无效、格式错误或已吊销。

检查：

1. 凭据目标名是否精确，包括空格、大小写和语言字符。
2. token 是否仍在 Trilium `Options → ETAPI` 中存在且启用。
3. 是否读到的是预期对象；不要尝试枚举其他凭据。
4. token 是否属于旧版 Trilium；必要时删除并新建。

## `无法自动发现 Trilium ETAPI endpoint`

常见原因：

- Trilium 未运行
- `healthcheck-url` 文件不存在
- 端口不是常见端口
- 桌面版刚启动，接口尚未就绪

解决：显式传入：

```bash
--base-url http://127.0.0.1:37840/etapi
```

或设置：

```bash
TRILIUM_ETAPI_URL=http://127.0.0.1:37840/etapi
```

## 浏览器访问 `403 Forbidden`

不一定是错误。桌面版关闭 Network access 时可能拒绝浏览器访问，但本机 ETAPI token 调用仍可用。以带 token 的：

```bash
python scripts/trilium_etapi.py --token-source '<位置>' app-info
```

为准。

## Windows 凭据 `ERROR_NOT_FOUND 1168`

目标名不匹配。最常见问题：

- 漏掉末尾空格
- 多/少大小写字符
- 目标名带前缀或后缀
- 凭据其实是 Windows Credentials，而不是 Generic Credential

不要因此扫描凭据管理器；应询问用户确认精确目标名。

## 找不到笔记或标题不匹配

优先使用结构化定位：

```bash
list-children root
list-children '<parentNoteId>'
find-child '<parentNoteId>' '<exact-title>'
```

标题匹配是精确匹配，不会忽略大小写、空格或全半角差异。`find-child` 输出数组：空数组表示无匹配，多个元素表示存在同名重复。

## `upsert-note refused: ... has N non-deleted children titled ...`

含义：同一父笔记下存在多个同名未删除笔记。helper 拒绝静默选择，这不是故障，是刻意保护——选错目标意味着覆盖错误的用户笔记。

处理：

1.  stderr 中每个候选都有 `noteId` 及 `type`/`mime`/`utcDateModified` 等辨识信息；再用 `get-note '<noteId>'` 或 `get-content` 查看具体内容区分哪篇是哪篇。
2. 在 Trilium UI 中人工处理重复：重命名、移动或删除多余副本（helper 不提供删除命令）。
3. 处理完后重试 upsert；或者如果明确知道要更新哪一篇，直接用精确 noteId 执行 `put-content` / `patch-note` 定点操作。
4. 向用户报告时给出每个 noteId 对应哪篇笔记，由用户确认迁移方式。

## 写入成功但 Trilium UI 没看到

可能原因：

- 当前 UI 没展开父节点
- 写入到了同名但不同的父笔记
- Trilium UI 缓存尚未刷新
- 笔记是 `code + text/x-markdown`，预览面板未打开

处理：记录 noteId，通过 `get-note` / `get-content` 校验；必要时重启 Trilium 后确认。

## 内容显示为一行或格式不对

检查 type/MIME：

- Markdown 原文应为 `code + text/x-markdown`
- 导读/富文本应为 `text + text/html`
- 不要把 Markdown 原文写进 HTML text note

## 安装后 agent 仍发现不了

检查：

1. 技能库目录里是否存在 `trilium-knowledge-sync`
2. 它是否真是 junction/symlink
3. 链接目标是否指向 `skill/trilium-knowledge-sync`
4. `SKILL.md` 是否可读
5. agent 是否需要重启或刷新技能库

## junction/symlink 权限问题

Windows 推荐 junction，通常不需要开发者模式。Linux/macOS symlink 一般可用；若策略禁止 symlink，可咨询仓库维护者，但不要用复制副本作为长期方案。
