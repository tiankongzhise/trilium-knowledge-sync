# Project Discovery

本文档是**永恒设计文档**：记录项目定位、证据来源与持久技术判断，回答"为什么这样设计"。它不记录随时间变化的状态；项目当前阶段、开放事项与远端配置事实一律以 [PROJECT_STATE.md](PROJECT_STATE.md) 为准。

## 项目定位

`trilium-knowledge-sync` 是一个面向本地 AI coding agents 的 Trilium Notes 同步技能仓库。它不是 Trilium 插件、不是独立后端服务，也不是通用笔记迁移平台。

核心目标：

1. 让 agent 能把用户指定资料通过 Trilium ETAPI 安全写入知识库。
2. 让 token 使用边界可审计：必须当次明确位置，不扫描、不复用、不接触字面 token。
3. 让所有 agent 链接同一份 skill，避免多副本维护失控。
4. 让仓库具备可测试、可验证、可发布的工程化结构。

## 证据来源

- 用户明确要求：技能仓库、链接使用、CI/CD、README、ignore、上手指南、安装脚本及缺失文档。
- 本机事实：Trilium Notes/TriliumNext 桌面版可通过本机 ETAPI 操作；Network access 关闭时本机 ETAPI token 调用仍可能可用。
- Trilium ETAPI OpenAPI 定义：`create-note`、note PATCH/content/search/import/export 等接口。
- 现有 `ai-signature-guard` 项目的单仓库 + junction/symlink 安装模式。

## 事实 / 推断 / 建议

| 类型 | 结论 | 置信度 | 证据/影响 |
|---|---|---|---|
| 事实 | 技能源应放在 `skill/trilium-knowledge-sync/` | 高 | 用户明确要求其他 agent 链接同一技能 |
| 事实 | 安装方式必须避免复制 | 高 | 用户明确说“不要复制得到处都是” |
| 事实 | helper 不应接受字面 token | 高 | 安全需求与对话约束 |
| 事实 | Trilium 写入默认应走 ETAPI | 高 | SQLite/WAL/cache/sync 风险 |
| 事实 | 本项目自身不需要数据库 | 高 | 只是 CLI/helper + 文档 + skill |
| 推断 | Markdown 原文最适合 `code + text/x-markdown` | 中 | 可保留源格式，Trilium 对 Markdown code note 有预览能力 |
| 建议 | 索引页使用 `text + text/html` 和内部 reference link | 中 | 已验证的 Trilium 笔记结构 |

## 技术判断

### 语言与运行时

- Python 3.9+，只使用标准库。
- 理由：agent 环境通常已有 Python；避免依赖安装和供应链复杂度。
- 不选择 Node/TypeScript：会引入额外 runtime 和依赖，收益不足。

### 持久化

本项目自身不持久化任何业务数据。目标数据由 Trilium 管理。helper 只读写用户明确指定的 token 位置和 Trilium ETAPI，不维护本地缓存数据库。

### 前端复杂度

无产品前端。交互界面是 agent 对话和 CLI。低保真/高保真/Demo 三阶段产品 UI 审核流程不适用。替代验证方式是：

- mock ETAPI end-to-end 测试
- 安装脚本 smoke test
- 真实 Trilium 手动验证（需要用户提供有效 token 位置）

### 安全判断

主要边界：

- token 位置强确认
- 不接受字面 token
- 端口探测先识别 Trilium 形状，再发送 token
- 不默认删除笔记
- 不直接写 SQLite
- 安装脚本默认不删除真实目录副本

## 主要风险

1. 用户 token 被误读或误用：通过位置确认和最小暴露降低。
2. 写错父笔记/同名笔记：通过精确父 ID + 精确标题、写后核验降低。
3. Windows junction/symlink 行为差异：通过双平台 CI smoke test 降低。
4. Trilium 版本 API 差异：通过标准 ETAPI 和故障排查文档降低。
