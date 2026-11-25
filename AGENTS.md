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

## 当前阶段状态

| 字段 | 当前值 |
|---|---|
| 当前阶段 | 初始工程基线，进行中；用户已授权创建仓库与配套工程化文件，尚未做最终人工终审 |
| 允许修改 | 本仓库内文件；不得修改用户真实 agent 技能库，除非用户明确要求安装/卸载 |
| 审核产物 | `skill/trilium-knowledge-sync/`、`docs/`、`tests/`、`.github/workflows/`、安装脚本 |
| 未决事项 | 远端仓库归属、发布策略、真实 Trilium token 的手动验收 |
| 下一阶段 | 用户复核初始基线；之后进入增量维护 |

本项目无产品 UI，低保真/高保真/Demo 审核门不适用；替代验收为单元测试、mock ETAPI 集成测试、安装 smoke test 和受控真实 Trilium 验证。详细事实见 `docs/PROJECT_DISCOVERY.md`，需求见 `docs/PRD.md`，测试策略见 `docs/TEST_PLAN.md`。

## 核心不变量

- `skill/trilium-knowledge-sync/SKILL.md` 是 agent 行为入口。
- `skill/trilium-knowledge-sync/scripts/trilium_etapi.py` 是运行时 ETAPI helper；修改后必须同步更新测试和文档。
- token 只能来自用户在当前对话中明确指定的位置；不得假设、扫描或复用历史位置。
- 不接受、不打印、不记录、不提交字面 token。
- 默认禁止直写 Trilium SQLite / `document.db`；运行路径必须走 ETAPI。
- 安装脚本只能创建/移除链接；删除旧副本必须显式 `-Force` / `-f`。

## 本地验证命令

```bash
python tools/validate_repo.py
python -m unittest discover -s tests -v
bash -n install.sh
python -m py_compile skill/trilium-knowledge-sync/scripts/trilium_etapi.py
```

Windows 额外验证：

```powershell
$path = (Resolve-Path .\install.ps1).Path
$source = [System.IO.File]::ReadAllText($path, [System.Text.Encoding]::UTF8)
$errors = $null
[void][System.Management.Automation.PSParser]::Tokenize($source, [ref]$errors)
if ($errors.Count) { $errors; exit 1 }
```

## 文档同步要求

修改以下任一内容时，必须检查并同步相关文档：

- token source 格式 → `docs/configuration.md`、`docs/getting-started.md`、`SKILL.md`
- ETAPI 命令参数 → `docs/usage-for-agents.md`、`SKILL.md`、tests
- 安装目录或链接策略 → `README.md`、`docs/installation.md`、`install.ps1`、`install.sh`
- CI/发布流程 → `docs/development.md`、`.github/workflows/`
- 远端仓库配置（branch protection、ruleset、webhook、仓库级 secret/权限等）→ `docs/development.md`、本文件状态表

## 仓库外状态变更防失步

远端配置变更（GitHub branch protection/ruleset/webhook 等）不经过 git 提交，上文的文档同步检查点不会自然触发，属于文档失步盲区。2026-11-25 已发生一次实例：branch protection 通过 API 配置后，`docs/development.md` 的"仍应配置"陈述过期却无人察觉。规则：

1. 执行远端配置变更的同一轮操作中，必须创建 topic branch 同步更新所有描述该状态的文档，与变更一起交付；不得只改远端、不改文档。
2. 变更前先在仓库内搜索描述目标状态的过渡性词句（"尚未"、"仍应"、"未配置"、"待办"、"TODO" 等），变更完成后逐条核对是否仍然成立。
3. 文档只写当前事实与持久规则。过渡性陈述必须登记到本文件状态表的「未决事项」，完成时移除；禁止只在正文里留"将来要做"的孤句。
4. 本条同样约束执行操作的 agent 本人：操作完成后主动报告哪些文档已同步、哪些陈述经核对仍然有效。

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
