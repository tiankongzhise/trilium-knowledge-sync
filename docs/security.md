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
- `stdin`

这样可避免 token 值出现在命令行和 shell history 中。注意：`stdin` 适合自动化，但调用方仍要保证 token 不进入日志。

### 自动 endpoint 发现的最小暴露

从 Trilium `healthcheck-url` 文件自动发现的 endpoint 必须是 loopback 地址。常见本地端口探测也会先观察未认证的 `/etapi/app-info` 响应是否具有 Trilium 形状，再发送 token，避免把 token 直接发给恰好占用端口的无关本机服务。远程或反向代理 endpoint 必须由用户/调用方显式指定。

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
