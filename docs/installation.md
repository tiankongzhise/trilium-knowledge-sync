# 安装与链接模型

## 为什么使用链接而不是复制

agent 技能库通常分布在多个目录，例如 Devin、Codex、Claude Code、`.agents`。如果把 skill 复制过去，会出现：

- 多处版本不一致
- 修复 bug 后某些 agent 仍使用旧版本
- 难以判断哪个副本是权威来源
- 安全规则更新无法可靠生效

因此本仓库采用**单仓库 + junction/symlink**：

```text
C:\path\to\trilium-knowledge-sync\
└── skill\trilium-knowledge-sync\   ← 唯一权威技能目录
    ├── SKILL.md
    └── scripts\trilium_etapi.py

%APPDATA%\devin\skills\trilium-knowledge-sync   → 链接到上面
~\.agents\skills\trilium-knowledge-sync         → 链接到上面
~\.codex\skills\trilium-knowledge-sync          → 链接到上面
~\.claude\skills\trilium-knowledge-sync         → 链接到上面
```

## 安装

### Windows PowerShell

```powershell
cd C:\path\to\trilium-knowledge-sync
.\install.ps1
```

强制替换旧副本或错误链接：

```powershell
.\install.ps1 -Force
```

查看将做什么但不执行：

```powershell
.\install.ps1 -WhatIf
```

### Git Bash / Linux / macOS

```bash
cd /path/to/trilium-knowledge-sync
./install.sh
```

强制替换：

```bash
./install.sh -f
```

### 自定义额外技能库

PowerShell：

```powershell
.\install.ps1 -TargetRoot "$env:USERPROFILE\.agents\skills" -TargetRoot "$env:APPDATA\devin\skills"
```

Bash：

```bash
./install.sh -t "$HOME/.agents/skills" -t "$HOME/.config/devin/skills"
```

传入 `-TargetRoot` / `-t` 后会使用自定义列表替代默认列表。

## 卸载

```powershell
.\install.ps1 -Uninstall
```

```bash
./install.sh -u
```

默认只移除链接。若发现旧的真实目录副本，为避免误删，脚本会跳过；确认要删除旧副本时再加：

```powershell
.\install.ps1 -Uninstall -Force
./install.sh -u -f
```

## 手动等价操作

Windows：

```powershell
mklink /J "%APPDATA%\devin\skills\trilium-knowledge-sync" "C:\path\to\trilium-knowledge-sync\skill\trilium-knowledge-sync"
```

Linux/macOS：

```bash
mkdir -p ~/.config/devin/skills
ln -s /path/to/trilium-knowledge-sync/skill/trilium-knowledge-sync \
  ~/.config/devin/skills/trilium-knowledge-sync
```

## 安装后验证

确认目标确实是链接：

```powershell
Get-Item "$env:APPDATA\devin\skills\trilium-knowledge-sync" | Format-List FullName,LinkType,Target
```

确认 skill 文件可读：

```powershell
Get-Content "$env:APPDATA\devin\skills\trilium-knowledge-sync\SKILL.md" -TotalCount 8
```

确认 helper 可运行（PowerShell）：

```powershell
python "$env:APPDATA\devin\skills\trilium-knowledge-sync\scripts\trilium_etapi.py" --version
```

Git Bash / Linux / macOS：

```bash
python "$APPDATA/devin/skills/trilium-knowledge-sync/scripts/trilium_etapi.py" --version 2>/dev/null || \
python "$HOME/.config/devin/skills/trilium-knowledge-sync/scripts/trilium_etapi.py" --version
```
