---
name: trilium-knowledge-sync
description: 当用户要求把调研结果、文档、代码知识、决策记录、配置步骤或其他需要长期保留的信息写入、更新或同步到 Trilium Notes 知识库时使用。通过 Trilium ETAPI 原生 API 操作，禁止默认直写 SQLite。必须依赖用户在当前对话中明确提供的 token 位置；若用户未明确位置，必须先询问，不得自行假设、搜索或复用历史位置。
allowed-tools:
  - read
  - grep
  - glob
  - exec
  - edit
---

# Trilium Knowledge Sync

把用户需要长期保留的内容安全、可验证地写入 Trilium Notes。优先保证：**原生 ETAPI、凭据最小暴露、幂等更新、写后核验、不破坏既有知识库**。

## 适用场景

当用户要求执行以下任一操作时启用本技能：

- 把调研结果、文档、笔记、代码知识、配置步骤、决策记录写入 Trilium Notes
- 更新、补充、重组已有 Trilium 知识库内容
- 将本地 Markdown/HTML/文本资料同步成 Trilium 笔记树
- 在 Trilium 中建立索引页、专题页、知识库条目或跨笔记链接

不适用：单纯读取本地文件、与 Trilium 无关的写作、用户明确要求直接操作 SQLite 的场景。默认**禁止直写 SQLite**；即使用户提出，也必须先说明风险并再次确认。

## 不可违反的 token 规则

### 1. 必须先确认“当前对话中明确给出的 token 位置”

在读取任何凭据前，先检查**当前对话**。用户必须明确说过 token 在哪里，例如：

- Windows 凭据管理器的精确目标名（Generic Credential target name）
- 本地文件路径
- 环境变量名
- 其他明确的凭据位置或注入方式

如果用户**没有明确说明位置**，立即停止写入流程并向用户询问。不得：

- 根据历史对话、经验或本项目文档假设位置
- 扫描 Windows 凭据管理器、浏览器、SSH、云凭据或其他 secret store
- 尝试常见目标名或默认文件名
- 复用其他任务、其他项目或上一会话中的 token 位置
- 要求用户把 token 值粘贴到聊天中

询问时只问“位置”，不要问 token 值。可使用以下话术：

```text
我需要通过 Trilium ETAPI 写入知识库，但你还没有明确 token 的位置。请只告诉我 token 存放在哪里，不要发送 token 本身，例如：
1. Windows 凭据管理器 Generic Credential 的精确目标名；
2. 保存 token 的本地文件路径；
3. 环境变量名。
```

### 2. token 使用红线

- 永不打印、记录、提交、复制到笔记、写入日志或进入 CI artifact。
- 不新增 `--token` 这类接收字面 token 的参数；只接受位置引用。
- 只读取用户明确指定的那一个凭据位置；Windows 凭据目标名的空格也属于精确名称的一部分。
- 如果 token 意外出现在聊天、日志或文件中，提醒用户轮换/吊销，并避免继续扩散。
- 任务结束后不要擅自删除用户凭据；可提醒用户是否吊销一次性 token。

## 运行时资源

本技能目录内带有 ETAPI 辅助 CLI：

```text
scripts/trilium_etapi.py
```

技能被调用时，宿主 agent 通常会显示本技能的 base directory。使用该 base directory 下的脚本路径；不要把这个脚本复制到项目或用户目录的其他位置。

该脚本只依赖 Python 标准库，支持 Windows / Linux / macOS，所有请求都通过 Trilium ETAPI。

## 标准执行流程

### 1. 理解写入目标

先明确：

- 要写什么：文件、目录、摘要、研究结论、代码知识、用户口述内容等
- 写到哪里：用户是否指定父笔记、路径或已有笔记
- 是新建、更新、合并还是重组
- 是否需要保留原始 Markdown/代码格式
- 是否需要索引页、内部链接、标签或跨笔记引用

如果目标父笔记不明显，先查看树或询问用户，不要随意放在 root。

### 2. 确认 token 位置

只有在当前对话中已经明确位置后才能继续。把用户描述转换为脚本参数：

| 用户说明 | 脚本 token source |
|---|---|
| Windows 凭据管理器目标名 `NAME` | `win-cred:NAME` |
| 文件 `C:\path\token.txt` | `file:C:\path\token.txt` |
| 环境变量 `TRILIUM_TOKEN` | `env:TRILIUM_TOKEN` |

`stdin` 不是合法 token source；用户提出经管道/重定向注入 token 时，拒绝并引导改用 `env:` 或 `file:`。

注意：Windows 目标名必须精确，包含大小写和末尾空格。不要自动尝试变体。

### 3. 验证 ETAPI 连通性

先执行应用信息检查，确认 token 和 endpoint 可用：

```bash
python "<SKILL_BASE_DIR>/scripts/trilium_etapi.py" \
  --token-source 'win-cred:EXACT_TARGET_NAME' \
  app-info
```

脚本会按顺序解析 endpoint：显式 `--base-url`、`TRILIUM_ETAPI_URL`、Trilium `healthcheck-url` 文件、常见本地端口。必要时让用户指定 `--base-url`，例如：

```text
http://127.0.0.1:37840/etapi
```

常见错误：

- `401 NOT_AUTHENTICATED`：token 错误、已删除、位置读错或凭据目标名不精确
- 连接失败：Trilium 未运行、端口不对、desktop 实例不是本机当前实例
- `403` 与 web access 相关：不要盲目要求开启 Network access；本机 ETAPI 通常即使关闭 Network access 也可用

### 4. 观察知识库结构，避免重复

使用以下命令读取结构，而不是猜：

```bash
python "<SKILL_BASE_DIR>/scripts/trilium_etapi.py" --token-source '<source>' list-children root
python "<SKILL_BASE_DIR>/scripts/trilium_etapi.py" --token-source '<source>' list-children <parentNoteId>
python "<SKILL_BASE_DIR>/scripts/trilium_etapi.py" --token-source '<source>' search '<关键词>' --fast --limit 10
python "<SKILL_BASE_DIR>/scripts/trilium_etapi.py" --token-source '<source>' find-child <parentNoteId> '<精确标题>'
```

原则：

- 优先更新已有精确匹配笔记，不制造重复笔记
- 父笔记不明确时询问用户，或选择用户知识库中语义最接近的现有分类并说明理由
- 不移动、删除、覆盖用户已有笔记，除非用户明确要求

### 5. 选择正确的 note type / MIME

- Markdown 原文、调研报告、Markdown 表格：优先 `type=code`、`mime=text/x-markdown`，以保留原文并支持 Trilium Markdown 预览
- 索引页、导读页、富文本总结：使用 `type=text`、`mime=text/html`，内容必须是 HTML
- 代码文件：使用 `type=code` 和相应 MIME，不要把代码塞进 HTML
- 二进制/附件：优先使用 Trilium attachment 机制；不要为了省事做 base64 硬塞
- 不要把 Markdown 原文直接当 HTML 放进 text note，否则表格、代码块和标题会失去语义

### 6. 幂等写入

优先使用 `upsert-note`：按“指定父笔记下的精确标题”查找，存在则更新，缺否则创建。

如果同一父笔记下存在多个同名未删除笔记，`upsert-note` 会拒绝执行并在 stderr 列出全部候选的辨识信息（noteId、type、mime、修改时间等）。此时**禁止自行挑选其中一个**，必须把候选列表完整呈给用户，说明每个 noteId 对应哪篇笔记，由用户决定如何处理：在 Trilium 中人工重命名/移动/删除重复项后重试，或明确指定某个 noteId 用 `patch-note`/`put-content` 定点操作。`find-child` 输出数组，同样不做静默选择。

```bash
python "<SKILL_BASE_DIR>/scripts/trilium_etapi.py" \
  --token-source '<source>' \
  upsert-note \
  --parent-id '<parentNoteId>' \
  --title '<笔记标题>' \
  --type code \
  --mime text/x-markdown \
  --content-file '<markdown文件路径>' \
  --position 10
```

创建导读/索引页时：

1. 先创建或更新子笔记，取得 noteId
2. 生成包含 `<a class="reference-link" href="#root/<noteId>">标题</a>` 的 HTML 索引
3. 将索引写入父笔记
4. 多份资料场景建议使用一个专题父笔记，而不是散落 root

如需使用除 upsert 外的底层命令：

- `create-note`：创建笔记
- `patch-note`：修改标题/type/mime
- `put-content`：替换内容
- `get-note` / `get-content`：读取核验

不要实现或执行批量删除。删除、移动、覆盖非本任务创建的笔记，必须先得到用户明确确认。

### 7. 写后核验

每次写入后至少核验：

- 父笔记的 `childNoteIds` 包含新笔记
- 标题、type、mime 符合预期
- `GET content` 与源内容 hash 一致（文本统一按 UTF-8/LF 比较）
- 索引页内部链接中的 noteId 都存在
- 若是更新而非新建，确认没有产生重复 sibling

示例：

```bash
python "<SKILL_BASE_DIR>/scripts/trilium_etapi.py" --token-source '<source>' get-note '<noteId>'
python "<SKILL_BASE_DIR>/scripts/trilium_etapi.py" --token-source '<source>' get-content '<noteId>' --output '<临时输出文件>'
```

### 8. 汇报

汇报应包含：

- Trilium 中的层级路径
- 每个新建/更新笔记的标题和 noteId
- 验证结果（hash、父子关系、链接）
- 是否存在未处理事项

不要在汇报中暴露 token、完整凭据路径以外的敏感信息或无关用户隐私。

## 禁止事项

- 禁止默认直接写 `document.db` / SQLite / WAL
- 禁止绕过 protected notes 的保护机制
- 禁止扫描或枚举无关凭据
- 禁止把 token 写入笔记、日志、git、CI artifact 或聊天
- 禁止无过滤批量删除笔记或批量清理
- 禁止在目标位置不明确时擅自覆盖用户已有知识

## 失败处理

- token 位置未明确：询问用户，停止
- token 读取失败：报告位置不可读，请用户确认精确位置；不要自行暴力尝试
- ETAPI 401：请用户检查 token 是否吊销/错误；不要打印 token
- ETAPI 404：父笔记或目标笔记不存在，重新检查树
- 写入部分成功：明确报告已创建/更新的 noteId 和失败点，不要假装全部成功
