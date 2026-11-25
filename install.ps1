# trilium-knowledge-sync 安装脚本
# 用法:
#   .\install.ps1                    # 挂载技能到各 agent 技能库（junction/symlink，免复制）
#   .\install.ps1 -Force             # 允许替换旧副本或错误挂载
#   .\install.ps1 -Uninstall         # 移除各技能库中的挂载点（默认不删除真实目录副本）
#   .\install.ps1 -TargetRoot <dir>  # 额外/自定义技能库根目录，可重复传入
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [switch]$Uninstall,
    [switch]$Force,
    [string[]]$TargetRoot = @()
)

$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $MyInvocation.MyCommand.Path
$skillName = 'trilium-knowledge-sync'
$skillSrc = Join-Path $project "skill\$skillName"

if (-not (Test-Path (Join-Path $skillSrc 'SKILL.md'))) {
    throw "未找到技能定义: $skillSrc\SKILL.md"
}

$defaultRoots = @(
    "$env:USERPROFILE\.agents\skills",
    "$env:APPDATA\devin\skills",
    "$env:USERPROFILE\.codex\skills",
    "$env:USERPROFILE\.claude\skills"
)
$roots = if ($TargetRoot.Count -gt 0) { $TargetRoot } else { $defaultRoots }
$targets = @($roots | ForEach-Object { Join-Path $_ $skillName })

function Remove-DirectoryLink {
    param([Parameter(Mandatory = $true)][string]$Path)
    if ($env:OS -eq 'Windows_NT') {
        cmd /c rmdir "$Path" | Out-Null
    } else {
        Remove-Item -LiteralPath $Path -Force
    }
}

function Test-SameLinkTarget {
    param(
        [Parameter(Mandatory = $true)]$Item,
        [Parameter(Mandatory = $true)][string]$Expected
    )
    $actual = $Item.Target
    if ($actual -is [array]) { $actual = $actual[0] }
    if (-not $actual) { return $false }
    try {
        return [string]::Equals((Resolve-Path $actual).Path.TrimEnd('\', '/'), (Resolve-Path $Expected).Path.TrimEnd('\', '/'), [System.StringComparison]::OrdinalIgnoreCase)
    } catch {
        return $false
    }
}

foreach ($target in $targets) {
    $parent = Split-Path -Parent $target

    if ($Uninstall) {
        if (-not (Test-Path $target)) { Write-Output "absent: $target"; continue }
        $item = Get-Item $target -Force
        if ($item.LinkType) {
            if ($PSCmdlet.ShouldProcess($target, 'remove skill link')) {
                Remove-DirectoryLink -Path $target
                Write-Output "removed link: $target"
            }
        } elseif ($Force -and (Test-Path (Join-Path $target 'SKILL.md'))) {
            Write-Warning "将删除旧副本而不是链接（因指定 -Force）: $target"
            if ($PSCmdlet.ShouldProcess($target, 'remove copied skill directory')) {
                Remove-Item -LiteralPath $target -Recurse -Force
                Write-Output "removed copy: $target"
            }
        } else {
            Write-Warning "跳过非链接目录（如需删除旧副本请使用 -Uninstall -Force）: $target"
        }
        continue
    }

    if (-not (Test-Path $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }

    if (Test-Path $target) {
        $item = Get-Item $target -Force
        if ($item.LinkType) {
            if (Test-SameLinkTarget -Item $item -Expected $skillSrc) {
                Write-Output "already linked: $target -> $skillSrc"
                continue
            }
            if (-not $Force) {
                Write-Warning "已存在指向其他位置的链接，跳过（可用 -Force 重建）: $target"
                continue
            }
            if ($PSCmdlet.ShouldProcess($target, 'replace incorrect skill link')) {
                Remove-DirectoryLink -Path $target
            }
        } elseif (Test-Path (Join-Path $target 'SKILL.md')) {
            if (-not $Force) {
                Write-Warning "已存在旧副本而非链接，跳过（可用 -Force 替换为链接）: $target"
                continue
            }
            Write-Warning "将删除旧副本并替换为链接（因指定 -Force）: $target"
            if ($PSCmdlet.ShouldProcess($target, 'replace copied skill with link')) {
                Remove-Item -LiteralPath $target -Recurse -Force
            }
        } else {
            Write-Warning "已存在非本技能目录，跳过: $target"
            continue
        }
    }

    if ($PSCmdlet.ShouldProcess($target, "link to $skillSrc")) {
        if ($env:OS -eq 'Windows_NT') {
            New-Item -ItemType Junction -Path $target -Target $skillSrc | Out-Null
            Write-Output "junction: $target -> $skillSrc"
        } else {
            New-Item -ItemType SymbolicLink -Path $target -Target $skillSrc | Out-Null
            Write-Output "symlink: $target -> $skillSrc"
        }
    }
}

if ($Uninstall) { Write-Output 'uninstall done.' } else { Write-Output 'install done.' }
