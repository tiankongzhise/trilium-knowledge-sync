# trilium-knowledge-sync

一个面向 Devin / Codex / Claude Code 等 agent 的 Trilium Notes 技能：把调研结果、文档、代码知识、决策记录等需要长期保留的信息，通过 **Trilium ETAPI 原生 API** 安全、幂等、可验证地同步进 Trilium 知识库。

本仓库是技能的**唯一开发源头**。其他 agent 通过 junction/symlink 链接到本仓库内的技能目录，不复制技能文件，避免多份副本失控。

## 核心原则

- **原生 API 优先**：使用 Trilium ETAPI；默认禁止直接写 SQLite / `document.db`。
- **token 位置必须当次明确**：agent 只能在用户在当前对话中明确说明 token 位置后读取；未说明则必须先询问。
- **不接触 token 值**：不接受聊天中的字面 token，不打印、不记录、不提交 token。
- **单份技能源**：安装脚本创建链接，不把 skill 复制到各个 agent 目录。
- **幂等写入**：按父笔记 + 精确标题查找，能更新就不重复创建。
- **写后核验**：验证父子关系、type/MIME、内容 hash 和内部链接。

## 快速开始

### 1. 准备 Trilium ETAPI token

在 Trilium Notes 中创建 ETAPI token：

```text
Options / 选项 → ETAPI → Create new ETAPI token
```

创建后 token 只显示一次。请把 token 放入一种**位置型凭据来源**：

- Windows 凭据管理器 Generic Credential
- 本地 token 文件
- 环境变量

不要把 token 值粘贴到聊天、仓库、笔记或 CI 中。

详细步骤见 [docs/getting-started.md](docs/getting-started.md)。

### 2. 安装/挂载技能

Windows PowerShell：

```powershell
cd C:\path\to\trilium-knowledge-sync
.\install.ps1
```

Git Bash / Linux / macOS：

```bash
cd /path/to/trilium-knowledge-sync
./install.sh
```

默认挂载到：

- `~/.agents/skills/trilium-knowledge-sync`
- `%APPDATA%/devin/skills/trilium-knowledge-sync`（Linux/macOS 对应 `~/.config/devin/skills/...`）
- `~/.codex/skills/trilium-knowledge-sync`
- `~/.claude/skills/trilium-knowledge-sync`

这些都是指向 `skill/trilium-knowledge-sync/` 的链接，不是副本。

### 3. 让 agent 使用

对 agent 提出任务时，明确写出 token 的**位置**而不是 token 值，例如：

```text
把 C:\path\research.md 更新到我的 Trilium 知识库。
token 在 Windows 凭据管理器，精确目标名是 My-Trilium-ETAPI。
```

或：

```text
把这些调研结果同步到 Trilium 的“知识库/AI”下面。
token 位置是文件 C:\secure\trilium-token.txt。
```

如果用户没有明确 token 位置，skill 会要求 agent 先询问，不允许自行猜测或扫描凭据。

## 仓库结构

```text
trilium-knowledge-sync/
├── skill/trilium-knowledge-sync/
│   ├── SKILL.md                     # agent 使用的主提示词/流程约束
│   └── scripts/trilium_etapi.py     # ETAPI CLI/helper，标准库实现
├── install.ps1                      # Windows 链接安装/卸载
├── install.sh                       # Git Bash/Linux/macOS 链接安装/卸载
├── docs/                            # 上手、配置、安全、架构、开发、排障文档
├── tests/                           # Python 单元测试
├── tools/                           # 仓库校验与维护工具
└── .github/workflows/               # CI/CD
```

## 文档

- [上手指南](docs/getting-started.md)
- [安装与链接模型](docs/installation.md)
- [token 与 endpoint 配置](docs/configuration.md)
- [agent 使用方式](docs/usage-for-agents.md)
- [CLI 参考](docs/cli-reference.md)
- [安全模型](docs/security.md)
- [架构说明](docs/architecture.md)
- [项目发现](docs/PROJECT_DISCOVERY.md)
- [产品需求](docs/PRD.md)
- [测试计划](docs/TEST_PLAN.md)
- [开发指南](docs/development.md)
- [故障排查](docs/troubleshooting.md)
- [贡献指南](CONTRIBUTING.md)
- [安全政策](SECURITY.md)
- [支持方式](SUPPORT.md)
- [行为准则](CODE_OF_CONDUCT.md)

## 本地验证

```bash
python tools/validate_repo.py
python -m unittest discover -s tests -v
bash -n install.sh
```

Windows 还会验证 `install.ps1` 的 PowerShell 语法；CI 中同时跑 Ubuntu 与 Windows。

## 许可证

MIT，见 [LICENSE](LICENSE)。如果本项目不打算公开分发，请在发布前重新确认许可证选择。
