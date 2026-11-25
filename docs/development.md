# 开发指南

## 本地环境

- Python 3.9+
- Git
- Windows PowerShell / PowerShell 7（Windows 安装脚本）
- Bash（Linux/macOS 或 Git Bash）

无第三方 Python 依赖。

## 常用验证

```bash
python tools/validate_repo.py
python -m unittest discover -s tests -v
bash -n install.sh
python -m py_compile skill/trilium-knowledge-sync/scripts/trilium_etapi.py
```

PowerShell 语法验证：

```powershell
$path = (Resolve-Path .\install.ps1).Path
$source = [System.IO.File]::ReadAllText($path, [System.Text.Encoding]::UTF8)
$errors = $null
[void][System.Management.Automation.PSParser]::Tokenize($source, [ref]$errors)
if ($errors.Count) { $errors; exit 1 }
```

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
2. 新增命令要同步更新：
   - `SKILL.md`
   - `docs/usage-for-agents.md`
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

- `ci.yml`：Ubuntu + Windows 验证；Python 3.9 兼容性任务固定在 `ubuntu-22.04`（新版 Ubuntu runner 不再提供该版本），另用 `3.x` 跟踪当前稳定 Python。
- GitHub Actions 使用 `actions/checkout@v7` 与 `actions/setup-python@v7`（Node 24 runtime）。
- `release.yml`：tag 触发，运行验证并创建 release artifact。

首次推送远端后，应根据仓库保护策略再决定是否要求 PR、status check 或 tag 审批。

## 发布建议

1. 更新 `CHANGELOG.md`
2. 运行全部验证
3. 创建 tag，例如 `v0.1.0`
4. push tag 后检查 release workflow

不要在没有明确远端仓库和 owner 授权前发布。
