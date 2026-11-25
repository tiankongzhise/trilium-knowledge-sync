# 安全模型

## 威胁模型

本技能处理两类敏感对象：

1. **Trilium ETAPI token**：持有者可读取/修改 token 权限范围内的笔记。
2. **知识库内容**：可能包含隐私、账号信息、项目资料或未公开决策。

主要风险：

- token 进入聊天、shell history、日志、git 或 CI artifact
- agent 扫描或复用错误凭据
- 写错父笔记、覆盖错误笔记、重复创建笔记
- 绕过 ETAPI 直写 SQLite，破坏 WAL、缓存、同步状态或 revision 记录

## 残余风险：agent 运行时遵守无法验证（使用前必读）

**这是本安全模型最重要、也最容易被误解的边界，请务必理解后再决定是否使用本 skill。**

本仓库的测试、CI 和 `validate_repo.py` 校验能保证的只有：helper 代码按设计工作、`SKILL.md` 中包含规定的约束文案。它们**不能保证**调用 skill 的 AI agent 在运行时真正遵守这些规则。

skill 的本质是写给 agent 的 prompt 指令。宿主 agent 是否遵循取决于模型行为、宿主平台的 prompt 处理方式和上下文状态——仓库内**不存在任何机制可以强制或验证**。具体来说，以下承诺只在 agent 自觉遵循时才成立：

- 只读取你在当前对话中明确指定的 token 位置，不扫描、不猜测、不复用历史位置
- 不打印、不记录、不把 token 复制进笔记或日志
- 写入前先向你确认，写后如实报告验证结果
- 不直写 SQLite、不执行未授权的删除或批量操作

需要明确：**helper 层面的强制（拒绝字面 token、探测形状检查、写后核验）是真实有效的**；但 **agent 行为层面的约束（何时读凭据、读哪个凭据、是否如实报告）只是请求，不是保证**。"测试全绿"不代表 agent 会守规矩。

你可以使用的缓解手段：

- 观察 agent 实际执行的命令行：token source 是否就是你指定的那个，有没有出现意外的凭据访问
- 重要写入前要求 agent 先给出操作计划（父笔记、标题、type/MIME）再执行
- 核对写后报告中的 noteId、hash，必要时在 Trilium 中抽查正文
- 一旦发现 agent 违反上述规则：视为安全事件——吊销该 token、检查笔记内容是否被污染、排查泄露范围

## 安全控制

### token 位置强确认

agent 只能在用户当前对话中明确 token 位置后读取该位置。这里有两个关键点：

- **当前对话**：不能复用历史会话或“以前用过”的位置。
- **明确位置**：不能只说“在凭据管理器”而不给目标名。

该规则牺牲一点便利性，换取可审计、最小暴露的凭据使用边界。

### 不接受字面 token

helper 不提供 `--token` 参数。支持的位置形式只有：

- `win-cred:<target>`
- `file:<path>`
- `env:<name>`

这样可避免 token 值出现在命令行和 shell history 中。`stdin` 不被接受为 token 通道：stdin 注入通常需经 shell 变量、管道或重定向，helper 无法审计 token 的来源路径，暴露面与字面 token 相当（2026-11-25 owner 决策）。自动化场景使用 `env:` 或 `file:`。

### 自动 endpoint 发现的最小暴露

从 Trilium `healthcheck-url` 文件自动发现的 endpoint 必须是 loopback 地址。常见本地端口探测也会先观察未认证的 `/etapi/app-info` 响应是否具有 Trilium 形状，再发送 token，避免把 token 直接发给恰好占用端口的无关本机服务。远程或反向代理 endpoint 必须由用户/调用方显式指定。

已接受的残余风险（owner 决策 2026-11-25，使用时须知情）：

- 端口探测的形状判断包含 `"Not authenticated"` 子串匹配，恰好返回该文案 401 的本机服务会被误判为 Trilium 并收到 token（仅限 loopback；形状检查防"巧合占用"，防不了本机"故意模仿"——能模仿的攻击者已具备本地执行能力）。
- `healthcheck-url` 文件路径发现后不做形状验证直接信任（仅受 loopback 硬约束），因为它由 Trilium 自身写入。
- 多实例 Trilium 下 healthcheck 指向不确定，可能静默连错知识库；多实例环境必须显式 `--base-url`（见 [configuration.md](configuration.md)）。
- 缓解：固定单实例用户显式配置 `TRILIUM_ETAPI_URL` 作为主路径，端口探测仅作后备。

### ETAPI 原生写入

ETAPI 会让 Trilium 正常维护：

- note/blob/branch 的一致性
- revision
- sync/entity change 状态
- 内存缓存与 UI 可见性

直接 SQLite 写入绕过这些机制，默认禁止。

### 最小破坏性

- helper 不提供 delete 命令。
- upsert 只按“指定父笔记 + 精确标题”操作。
- 默认不移动、删除、覆盖非本任务创建的笔记。
- 删除、批量重组、直接 SQL、protected notes 操作都需要用户单独明确授权。

## 泄漏响应

如果 token 意外泄露：

1. 立即停止相关写入。
2. 在 Trilium `Options → ETAPI` 删除/吊销 token。
3. 创建新 token 并更新存放位置。
4. 检查 git、CI artifact、日志、聊天记录和笔记内容，避免继续扩散。
5. 如已经进入 git 历史，按凭据泄露流程清理历史或视为永久泄露并轮换。

## 安装脚本安全

安装脚本默认：

- 只移除 junction/symlink 自身，不递归删除链接目标。
- 遇到真实目录副本时跳过。
- 只有显式 `-Force` / `-f` 才删除旧副本。

这是为了防止把用户手工放置的目录误删。
