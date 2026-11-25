# 开发指南

## 本地环境

- Python 3.9+
- Git
- Windows PowerShell / PowerShell 7（Windows 安装脚本）
- Bash（Linux/macOS 或 Git Bash）

无第三方 Python 依赖。

## 常用验证

```bash
python tools/verify.py
```

`verify.py` 一次运行全部本地检查；传入选项名可只跑子集（`validate`、`unittest`、`compile`、`bash`、`ps1`），例如 `python tools/verify.py validate`。PowerShell 语法检查在无 PowerShell 的平台上自动跳过。

安装脚本 smoke test 应使用临时 HOME/APPDATA，避免污染真实 agent 技能库。

## 修改 SKILL.md 的注意点

`SKILL.md` 的 frontmatter 中 `name` 必须与目录名一致：

```text
trilium-knowledge-sync
```

`description` 是 agent 自动触发的重要依据。修改触发场景时，要同时检查：

- 是否仍然强调“当前对话明确 token 位置”
- 是否仍然强调 ETAPI、不直写 SQLite
- 是否覆盖写入/更新/同步 Trilium 的常见措辞

正文中的 token 规则属于安全硬约束，不能弱化。

## 修改 trilium_etapi.py 的注意点

1. 保持只接受 token 位置，不新增字面 token 参数。
2. 新增命令要同步更新（归属见 `AGENTS.md` 文档地图）：
   - `docs/cli-reference.md`（CLI 接口的权威归属）
   - `docs/usage-for-agents.md`
   - `SKILL.md`
   - `tests/test_trilium_etapi.py`
   - README（如用户可见行为变化）
3. 错误信息不能包含 Authorization header 或 token。
4. 文本写入默认按 UTF-8 处理；binary 支持如果未来加入，需要单独设计。

## 修改安装脚本的注意点

安装脚本的核心目标是“链接而不是复制”。任何改动都必须保持：

- 默认不删除真实目录副本
- 删除旧副本必须显式 force
- 移除链接时不递归进入目标目录
- 支持多 agent 技能库
- `install.ps1` 必须保存为 UTF-8 with BOM；否则 Windows PowerShell 5.1 在部分非 UTF-8 ANSI codepage 下可能误读中文注释/字符串

## CI/CD

- `ci.yml`：任意分支 push、PR 和手动触发都会运行 Ubuntu + Windows 验证；Python 3.9 兼容性任务固定在 `ubuntu-24.04`（Ubuntu 26.04 runner 不再提供该版本，而 22.04 已进入弃用周期），另用 `3.x` 跟踪当前稳定 Python。
- GitHub Actions 使用 `actions/checkout@v7` 与 `actions/setup-python@v7`（Node 24 runtime）。
- `release.yml`：tag 触发，运行验证并创建 release artifact。

仓库规则要求所有变更通过 topic branch + PR 进入 `main`，且 CI 全部成功后才能合并；禁止本地直接提交或 push `main`。branch protection 的当前配置事实（required checks、生效日期等）属于时效性状态，以 [PROJECT_STATE.md](PROJECT_STATE.md) 为准。修改 CI 任务命名或增删任务时，必须同步更新远端保护配置中的 required contexts，并在同一轮操作中更新登记处。

## 发布流程

发布策略（2026-11-25 由仓库 owner 确定）：

1. **触发**：仅当仓库 owner 在当前对话明确要求发版并给出版本号。agent 不自行提议发版或版本号。push tag 与普通 push 适用同一授权规则。
2. **版本号真相源**是 `skill/trilium-knowledge-sync/scripts/trilium_etapi.py` 中的 `VERSION` 常量；tag 必须等于 `v${VERSION}`，CHANGELOG 最新小节与之一致。三处不一致的发版视为失败发版，需修正后重走流程。
3. **流程**：
   1. 发版 PR：更新 CHANGELOG（把 Unreleased 内容归入新版本小节）、同步 `VERSION`、运行全量验证。
   2. CI 全绿后合并进 `main`。
   3. 从 `main` 最新 commit 创建 tag（`git tag v<VERSION>`）并 push。
   4. 检查 release workflow 产物与 GitHub Release 页面。
4. 0.x 阶段不承诺兼容性，但 breaking change 必须在 CHANGELOG 明确标注。

`release.yml` 在 `v*.*.*` tag push 时自动执行验证、打包全仓库 zip 并创建 Release。
