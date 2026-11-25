# agent 使用方式

本文面向调用 `trilium-knowledge-sync` 的 agent，概括安全流程和 CLI 用法。权威行为约束以 `skill/trilium-knowledge-sync/SKILL.md` 为准。

## 调用前必须确认 token 位置

如果用户没有在当前对话中明确 token 位置，必须先问：

```text
我需要通过 Trilium ETAPI 写入知识库。请只告诉我 token 存放在哪里，不要发送 token 本身，例如：
1. Windows 凭据管理器 Generic Credential 的精确目标名；
2. 保存 token 的本地文件路径；
3. 环境变量名。
```

不能接受“用你上次那个 token”“你自己找一下”“应该在凭据管理器里”这类模糊说法。必须让用户明确具体位置。

## CLI 基本形式

```bash
python "<SKILL_BASE_DIR>/scripts/trilium_etapi.py" \
  --token-source '<位置>' \
  [--base-url 'http://127.0.0.1:37840/etapi'] \
  <command>
```

`<SKILL_BASE_DIR>` 是 skill 被调用时宿主 agent 显示的技能目录，不是复制出来的路径。

## 常用命令

### 验证连通性

```bash
python scripts/trilium_etapi.py --token-source 'win-cred:My-Trilium-ETAPI' app-info
```

### 查看树结构

```bash
python scripts/trilium_etapi.py --token-source 'win-cred:My-Trilium-ETAPI' list-children root
python scripts/trilium_etapi.py --token-source 'win-cred:My-Trilium-ETAPI' list-children '<parentNoteId>'
```

### 搜索与精确查找

```bash
python scripts/trilium_etapi.py --token-source 'win-cred:My-Trilium-ETAPI' search '免费开发资源' --fast --limit 10
python scripts/trilium_etapi.py --token-source 'win-cred:My-Trilium-ETAPI' find-child '<parentNoteId>' '<精确标题>'
```

### 创建/更新 Markdown 笔记

`upsert-note` 会在创建/替换后重新读取父关系和正文做校验；输出中的 `verified: true` 表示 helper 已验证，不代替 agent 对最终知识库结构的复核。

```bash
python scripts/trilium_etapi.py \
  --token-source 'win-cred:My-Trilium-ETAPI' \
  upsert-note \
  --parent-id '<parentNoteId>' \
  --title '调研报告标题' \
  --type code \
  --mime text/x-markdown \
  --content-file 'C:\path\report.md' \
  --position 10
```

### 创建/更新 HTML 索引页

先把 HTML 写入临时文件，再执行：

```bash
python scripts/trilium_etapi.py \
  --token-source 'win-cred:My-Trilium-ETAPI' \
  upsert-note \
  --parent-id '<parentNoteId>' \
  --title '专题索引' \
  --type text \
  --mime text/html \
  --content-file 'C:\path\index.html' \
  --position 5 \
  --expanded
```

Trilium 内部链接格式：

```html
<a class="reference-link" href="#root/<noteId>">笔记标题</a>
```

## 推荐同步模式

### 单篇 Markdown

1. 用户给出源文件和目标位置
2. 查找父笔记
3. `upsert-note` 为 `code + text/x-markdown`
4. 校验 hash

### 多篇资料 + 索引

1. 创建/确认专题父笔记
2. 每篇资料一个 Markdown 子笔记
3. 父笔记写 HTML 导读和内部链接
4. 验证所有链接 noteId

### 更新已有笔记

1. 用 `find-child` 或搜索定位笔记
2. 优先只替换目标任务范围内的内容
3. `put-content` 前先确认确实是用户要更新的笔记
4. 写后读取核验，并向用户说明是创建还是更新

## 不应该做的事

- 不用 `delete` 命令清理重复笔记；helper 也故意不提供删除命令
- 不把 token 或 note 内容写进 shell history、日志或 artifact
- 不直接写 SQLite
- 不批量扫描凭据
- 不把 Markdown 原文塞进 HTML text note
