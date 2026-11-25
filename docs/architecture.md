# 架构说明

## 总体结构

```text
用户请求
  ↓
agent 识别 Trilium 写入意图
  ↓
trilium-knowledge-sync/SKILL.md
  ├─ 强制确认当前对话中的 token 位置
  ├─ 约束 note type / MIME / 幂等 / 核验 / 禁止事项
  ↓
scripts/trilium_etapi.py
  ├─ 解析 token source（win-cred/file/env/stdin）
  ├─ 发现 ETAPI endpoint
  ├─ 调用 Trilium ETAPI
  ↓
Trilium Notes
```

## 仓库组件

| 组件 | 作用 |
|---|---|
| `skill/trilium-knowledge-sync/SKILL.md` | agent 行为约束、触发条件、操作流程 |
| `skill/trilium-knowledge-sync/scripts/trilium_etapi.py` | 可测试的 ETAPI helper/CLI |
| `install.ps1` / `install.sh` | 把技能目录链接到各 agent 技能库 |
| `docs/` | 用户与开发者文档 |
| `tests/` | 不依赖真实 Trilium 的单元测试 |
| `tools/validate_repo.py` | 仓库结构、SKILL 关键规则、文档链接校验 |
| `.github/workflows/` | CI 与 release 模板 |

## 链接安装模型

```text
repo/skill/trilium-knowledge-sync  ← 唯一权威版本
        ↑
        ├── junction/symlink: ~/.agents/skills/trilium-knowledge-sync
        ├── junction/symlink: %APPDATA%/devin/skills/trilium-knowledge-sync
        ├── junction/symlink: ~/.codex/skills/trilium-knowledge-sync
        └── junction/symlink: ~/.claude/skills/trilium-knowledge-sync
```

运行时 helper 也放在 skill 目录内，因此链接后 agent 可以同时访问 `SKILL.md` 和 `scripts/trilium_etapi.py`，不需要第二份拷贝。

## ETAPI helper 设计

`trilium_etapi.py` 分为四层：

1. **token resolution**：只解析位置，不接受 token 值
2. **endpoint discovery**：显式 URL → 环境变量 → healthcheck 文件 → 本地端口探测
3. **HTTP client**：认证、JSON/text 编解码、错误边界
4. **note operations**：查询、搜索、创建、更新、upsert

helper 只使用 Python 标准库，降低安装和供应链复杂度。

## note type 策略

| 内容 | type | MIME | 原因 |
|---|---|---|---|
| Markdown 原文 | `code` | `text/x-markdown` | 保留源格式，并利用 Trilium Markdown 预览 |
| 索引/导读 | `text` | `text/html` | 支持富文本和内部链接 |
| 代码片段 | `code` | 对应语言 MIME | 保留语法高亮 |
| 二进制 | attachment/file | 原始 MIME | 避免 base64 污染正文 |

## 幂等模型

`upsert-note` 使用以下键定位：

```text
parentNoteId + exact title
```

存在则比较内容 hash，必要时替换；不存在则创建。helper 不做模糊匹配、不自动删除重复项，避免误伤用户已有笔记。

## 失败边界

- token/endpoint 失败：写入前失败，无副作用
- 单个 note upsert 失败：报告已成功和失败的 noteId
- 写后核验失败：明确报告不一致项，不声称成功
