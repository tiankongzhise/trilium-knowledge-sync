# trilium-knowledge-sync

> 🚫 **Main 分支保护规则**（Branch Protection Policy）
> 禁止在本地 `main` 分支上直接创建提交，也禁止把本地 `main` 直接 push 到远端。所有变更必须从最新 `main` 创建 topic branch，在分支上提交并推送，通过 PR 审查，且 CI 全部通过后才能合并进 `main`。
> agent 不得因为用户一句“直接改 main”或“直接推 main”而绕过本规则；如需变更本规则，必须先明确修改本段。
> 记录于 2026-11-25。

> ⚠️ **贡献者身份约定**（Author Identity Policy）
> 记录于 2026-11-25，触发场景：首次 push origin main，未检出名单外作者。
> 约定：push 前必须统一作者
> 允许身份：notebook <tiankongzhise@163.com>
> 修改约定请直接编辑本行。

> ⚠️ **AI 署名约定**（AI Signature Policy）
> 记录于 2026-11-25，触发场景：首次 push origin main，未检出 AI 署名。
> 约定：push 前必须剥离署名
> 修改约定请直接编辑本行。

## 项目说明

本仓库是 `trilium-knowledge-sync` skill 的唯一开发源头。其他 agent 必须通过 junction/symlink 链接使用 `skill/trilium-knowledge-sync/`，不得复制 skill 到各个 agent 目录形成多份副本。

本项目无产品 UI，低保真/高保真/Demo 审核门不适用；替代验收为单元测试、mock ETAPI 集成测试、安装 smoke test 和受控真实 Trilium 验证。

## 核心不变量

- `skill/trilium-knowledge-sync/SKILL.md` 是 agent 行为入口。
- `skill/trilium-knowledge-sync/scripts/trilium_etapi.py` 是运行时 ETAPI helper；修改后必须同步更新测试和文档。
- token 只能来自用户在当前对话中明确指定的位置；不得假设、扫描或复用历史位置。
- 不接受、不打印、不记录、不提交字面 token。
- 默认禁止直写 Trilium SQLite / `document.db`；运行路径必须走 ETAPI。
- 安装脚本只能创建/移除链接；删除旧副本必须显式 `-Force` / `-f`。
- 工作范围限于本仓库内文件；不得修改用户真实 agent 技能库，除非用户明确要求安装/卸载。

## 工作状态

项目的当前阶段、开放事项、远端配置事实等全部时效性状态，唯一归属 [docs/PROJECT_STATE.md](docs/PROJECT_STATE.md)。**开始工作前先读它**；本文件不登记任何状态。

## 文档治理

### 文档地图

每份文档有且只有一个职责。下表是全部文档的归属登记；仓内每个 `.md` 必须在本表登记，新增文档必须先登记本表再提交（CI 强制）。

| 文档 | 类型 | 唯一职责 | 拥有的事实域 | 禁写内容 |
|---|---|---|---|---|
| `AGENTS.md` | 治理 | agent 工作规则、文档地图、治理硬规则 | 治理规则、持久工作约束 | 时效状态、操作步骤细节 |
| `docs/PROJECT_STATE.md` | 状态 | 时效性状态唯一登记处 | 当前阶段、开放事项、远端仓库与配置事实 | 持久规则、设计判断 |
| `README.md` | 门面 | 项目定位、快速入口、文档导航 | 项目定位表述、导航结构 | 状态、逐字命令清单 |
| `docs/PRD.md` | 规范 | 需求、优先级、验收标准、永久性非目标 | 需求与范围 | 实现进度、临时状态 |
| `docs/PROJECT_DISCOVERY.md` | 规范 | 设计依据：定位证据、技术判断、风险 | 证据来源、技术判断、风险分析 | 一切时效状态 |
| `docs/architecture.md` | 规范 | 系统结构与设计决策及理由 | 架构、note type 策略、幂等模型 | 状态、操作步骤 |
| `docs/TEST_PLAN.md` | 规范 | 测什么、为什么这样测 | 测试层级、覆盖重点 | 逐字命令清单 |
| `docs/development.md` | 规范 | 开发技术参考与 CI/CD 内部细节 | CI 结构、脚本技术约束、修改注意点 | 远端配置事实 |
| `docs/getting-started.md` | 操作 | 新用户从零到首次同步 | 用户上手路径 | 状态 |
| `docs/installation.md` | 操作 | 安装/卸载/链接模型细节 | 安装行为与参数 | 状态 |
| `docs/configuration.md` | 操作 | token 位置格式与 endpoint 解析 | token source 格式、环境变量 | 状态 |
| `docs/usage-for-agents.md` | 操作 | agent 调用模式与推荐流程 | 使用模式 | 状态 |
| `docs/cli-reference.md` | 操作 | CLI 参数权威参考 | 命令行接口 | 状态 |
| `docs/security.md` | 规范 | 威胁模型与安全控制设计 | 威胁模型、泄漏响应 | 状态 |
| `docs/troubleshooting.md` | 操作 | 症状→诊断→解决 | 故障模式 | 状态 |
| `CONTRIBUTING.md` | 规范 | 面向人类贡献者的流程表述 | 贡献流程 | 与本文硬规则重复的细节（引用代替） |
| `CHANGELOG.md` | 台账 | 版本变更记录（append-only） | 版本历史 | 当前状态 |
| `SECURITY.md` | 惯例 | 安全问题报告政策 | 漏洞报告流程 | — |
| `SUPPORT.md` | 惯例 | 支持渠道与范围 | 支持范围 | — |
| `CODE_OF_CONDUCT.md` | 惯例 | 行为准则 | 社区准则 | — |
| `skill/trilium-knowledge-sync/SKILL.md` | 运行时 | agent 行为约束（产品组成部分，不是项目文档） | skill 行为规则 | 项目状态 |
| `.github/PULL_REQUEST_TEMPLATE.md` | 模板 | PR 核对清单 | 核对项 | — |
| `.github/ISSUE_TEMPLATE/bug_report.md` | 模板 | bug 报告 issue 表单 | bug 报告结构 | — |
| `.github/ISSUE_TEMPLATE/feature_request.md` | 模板 | 功能建议 issue 表单 | 功能建议结构 | — |

### 事实归属规则

1. **一条事实只许写在它的归属文档**。其他文档需要时给链接，不复述。归属冲突时以本表「拥有的事实域」为准。
2. 写新事实前先查本表确认归属；无归属的事实不准写——先在本表登记归属，再写事实。
3. 发现同一事实的第二处抄录：删除抄录改为引用；如认为归应当转移，先改本表再迁移。
4. 时效性状态（项目阶段、开放事项、远端配置事实、"还没做"类陈述）唯一归属 `docs/PROJECT_STATE.md`。"永不做"属于设计决策，可写在 PRD/安全模型等规范文档；"还没做"属于状态，只许进登记处。
5. 可由代码、测试、git 推导的事实不写入任何文档（例如"哪些功能已实现"）。

### 机器强制（CI 每次执行，不依赖自觉）

`tools/validate_repo.py` 包含以下文档治理检查，失败即 CI 红：

- **状态词句禁扫**：过渡性状态词句（权威清单见 `validate_repo.py` 中 `STATE_PHRASES` 常量）只许出现在 `docs/PROJECT_STATE.md` 与 `CHANGELOG.md`，出现在其他任何 `.md` 即失败。
- **文档地图完整性**：仓内每个 `.md` 必须在上表登记；表中每个条目对应的文件必须存在；表内不得有重复条目。

修改 `STATE_PHRASES` 清单或白名单属于治理变更，需在 PR 中说明理由。

### 仓库外状态变更

远端配置变更（GitHub branch protection/ruleset/webhook/仓库可见性等）不经过 git 提交，属于失步盲区。规则：

1. 执行远端配置变更的同一轮操作中，必须创建 topic branch 同步更新 `docs/PROJECT_STATE.md`，与变更一起交付；不得只改远端、不改登记。
2. 变更前在仓内检索描述目标状态的既有陈述，变更后逐条核对是否仍然成立；失效陈述在同一分支内清除或改写。
3. 本条约束执行操作的 agent 本人：操作完成后主动报告哪些文档已同步、哪些陈述经核对仍然有效。

## 本地验证

```bash
python tools/verify.py
```

`verify.py` 一次运行全部本地检查（validate_repo、单元测试、helper 编译、bash 语法、PowerShell 语法按平台可用性自动跳过）。可传入子集，例如 `python tools/verify.py validate unittest`。CI 使用同一入口。

## Git 注意

- 不要提交 token、真实凭据、临时导出的笔记内容或本机隐私路径。
- 不要向远端 push，除非用户明确要求。
- 不得直接在 `main` 上提交或 push。标准变更流程：

```bash
git switch main
git pull --ff-only
git switch -c <type>/<short-topic>
# 修改、验证、提交
git push -u origin <type>/<short-topic>
# 创建 PR；等待 CI 全部通过后，按仓库配置合并进 main
```

- 合并 PR 前必须确认 CI 为 success；不得因为本地测试通过就跳过远端 CI。
- 即使是紧急修复，也必须走分支和 PR；只允许压缩流程，不允许绕过流程。
