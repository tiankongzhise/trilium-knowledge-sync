# trilium-knowledge-sync

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
$errors = $null
[void][System.Management.Automation.PSParser]::Tokenize((Get-Content -Raw .\install.ps1), [ref]$errors)
if ($errors.Count) { $errors; exit 1 }
```

## 文档同步要求

修改以下任一内容时，必须检查并同步相关文档：

- token source 格式 → `docs/configuration.md`、`docs/getting-started.md`、`SKILL.md`
- ETAPI 命令参数 → `docs/usage-for-agents.md`、`SKILL.md`、tests
- 安装目录或链接策略 → `README.md`、`docs/installation.md`、`install.ps1`、`install.sh`
- CI/发布流程 → `docs/development.md`、`.github/workflows/`

## Git 注意

- 不要提交 token、真实凭据、临时导出的笔记内容或本机隐私路径。
- 不要向远端 push，除非用户明确要求。
