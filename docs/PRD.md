# Product Requirements Document

## 用户与使用场景

主要用户：

- 本机使用 Trilium Notes 作为知识库的用户
- 被用户授权操作知识库的 AI coding agent
- 维护该 skill 的开发者

核心场景：

1. 用户要求 agent 把调研报告、文档、决策、配置步骤等写入 Trilium。
2. agent 检查当前对话是否明确 token 位置；未明确则询问。
3. agent 通过 skill 中的 ETAPI helper 验证连接、查看树结构、创建/更新笔记。
4. agent 写后核验并向用户报告路径、noteId 和验证结果。

## 目标

- 安全写入 Trilium，不破坏既有知识库。
- token 不进入聊天、日志、git、CI artifact 或笔记正文。
- 多 agent 使用同一份 skill 源，安装后自动共享更新。
- 重复执行不产生重复笔记。
- 使用 correct note type/MIME 保留 Markdown/HTML/代码语义。

## 非目标

- 不绕过 protected notes。
- 不扫描或枚举本机凭据。
- 不默认删除、移动或批量重组用户笔记。
- 不直接写 SQLite / `document.db`。
- 不实现完整 Trilium 客户端或同步服务器。
- 不替用户决定 token 存放位置。

## 核心流程

### 流程 A：token 位置未明确

1. 用户提出写入 Trilium。
2. agent 发现当前对话没有明确位置。
3. agent 停止写入，询问位置。
4. 用户只提供位置，不提供 token 值。

验收：agent 不读取凭据、不扫描、不假设。

### 流程 B：单篇 Markdown 同步

1. 用户提供源文件、目标位置和 token 位置。
2. helper 验证 ETAPI。
3. agent 找到父笔记。
4. `upsert-note` 创建或更新 `code + text/x-markdown` 笔记。
5. helper 重新读取父关系和正文。
6. agent 报告 noteId、hash 和验证结果。

验收：重复执行第二次返回 `unchanged`，不产生重复 sibling。

### 流程 C：专题父笔记 + 多份子笔记

1. 每份资料创建/更新一个子笔记。
2. 父笔记生成 HTML 导读、内部链接和来源说明。
3. 验证内部链接 noteId 均存在。

验收：知识库树结构清晰，链接可点击，正文 hash 与源文件一致。

### 流程 D：连接或 token 失败

1. `app-info` 返回 401/连接失败。
2. agent 报告失败类型和可检查项。
3. 不打印 token，不尝试无关凭据。

验收：无部分写入却被汇报为成功。

## 功能需求

| ID | 需求 | 优先级 |
|---|---|---|
| FR-1 | 支持 win-cred/file/env/stdin 四类 token 位置 | Must |
| FR-2 | 自动或显式解析 ETAPI endpoint | Must |
| FR-3 | 支持 app-info、get/list/search/find | Must |
| FR-4 | 支持 create/patch/put-content/upsert | Must |
| FR-5 | upsert 写后重新读取核验 | Must |
| FR-6 | Windows junction 与 POSIX symlink 安装 | Must |
| FR-7 | 不接受字面 token 参数 | Must |
| FR-8 | 单元测试与 mock ETAPI 集成测试 | Must |
| FR-9 | CI 验证和 release 模板 | Must |
| FR-10 | attachment/ZIP import 高级封装 | Could |

## 验收标准

- `python tools/validate_repo.py` 通过。
- `python -m unittest discover -s tests -v` 通过。
- Bash/PowerShell 安装 smoke test 在隔离 HOME/APPDATA 中通过。
- skill frontmatter 可被通用 skill validator 接受。
- 用户未明确 token 位置时，skill 文案要求 agent 停止并询问。
- `--token` 不能作为合法 CLI 参数使用。
- 任何测试输出和错误信息不包含 fake token 值。
