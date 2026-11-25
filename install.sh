#!/usr/bin/env bash
# trilium-knowledge-sync 安装脚本（Git Bash / Linux / macOS）
# 用法:
#   ./install.sh                 # 挂载技能到各 agent 技能库（symlink/junction，免复制）
#   ./install.sh -f              # 允许替换旧副本或错误挂载
#   ./install.sh -u              # 移除挂载点（默认不删除真实目录副本）
#   ./install.sh -t <dir>        # 额外/自定义技能库根目录，可重复传入
set -euo pipefail

project="$(cd "$(dirname "$0")" && pwd)"
name='trilium-knowledge-sync'
skill_src="$project/skill/$name"
force=0
uninstall=0
custom_roots=()

usage() {
  sed -n '2,7p' "$0"
}

while [ $# -gt 0 ]; do
  case "$1" in
    -f|--force) force=1 ;;
    -u|--uninstall) uninstall=1 ;;
    -t|--target-root)
      [ $# -ge 2 ] || { echo "missing value for $1" >&2; exit 2; }
      custom_roots+=("$2"); shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

[ -f "$skill_src/SKILL.md" ] || { echo "未找到技能定义: $skill_src/SKILL.md" >&2; exit 1; }

home_dir="${USERPROFILE:-$HOME}"
appdata="${APPDATA:-$home_dir/.config}"
if [ "${#custom_roots[@]}" -gt 0 ]; then
  roots=("${custom_roots[@]}")
else
  roots=(
    "$home_dir/.agents/skills"
    "$appdata/devin/skills"
    "$home_dir/.codex/skills"
    "$home_dir/.claude/skills"
  )
fi

same_link_target() {
  local target="$1" expected="$2" actual
  actual="$(readlink "$target" 2>/dev/null || true)"
  [ -n "$actual" ] || return 1
  if command -v cygpath >/dev/null 2>&1 && [[ "$actual" =~ ^[A-Za-z]:[\\/] ]]; then
    actual="$(cygpath -u "$actual")"
  fi
  if [[ "$actual" != /* ]]; then
    actual="$(dirname "$target")/$actual"
  fi
  [ "$(cd "$actual" 2>/dev/null && pwd -P)" = "$(cd "$expected" 2>/dev/null && pwd -P)" ]
}

make_link() {
  local target="$1" src="$2"
  if command -v cmd >/dev/null 2>&1 && command -v cygpath >/dev/null 2>&1; then
    if cmd //c mklink //J "$(cygpath -w "$target")" "$(cygpath -w "$src")" >/dev/null; then
      echo "junction: $target -> $src"
      return 0
    fi
    echo "无法创建 junction: $target" >&2
    return 1
  fi
  if ln -s "$src" "$target" 2>/dev/null; then
    echo "symlink: $target -> $src"
    return 0
  fi
  echo "无法创建链接: $target" >&2
  return 1
}

remove_link() {
  local target="$1"
  if command -v cmd >/dev/null 2>&1 && command -v cygpath >/dev/null 2>&1 && [ ! -L "$target" ]; then
    cmd //c rmdir "$(cygpath -w "$target")" >/dev/null
  else
    rm -f "$target"
  fi
}

for root in "${roots[@]}"; do
  target="$root/$name"

  if [ "$uninstall" = 1 ]; then
    if [ ! -e "$target" ] && [ ! -L "$target" ]; then
      echo "absent: $target"
      continue
    fi
    if [ -L "$target" ]; then
      remove_link "$target"
      echo "removed link: $target"
    elif [ -d "$target" ] && [ -f "$target/SKILL.md" ] && [ "$force" = 1 ]; then
      echo "warning: 将删除旧副本而不是链接（因指定 -f）: $target" >&2
      rm -rf "$target"
      echo "removed copy: $target"
    else
      echo "warning: 跳过非链接目录（如需删除旧副本请使用 -u -f）: $target" >&2
    fi
    continue
  fi

  mkdir -p "$root"

  if [ -e "$target" ] || [ -L "$target" ]; then
    if [ -L "$target" ]; then
      if same_link_target "$target" "$skill_src"; then
        echo "already linked: $target -> $skill_src"
        continue
      fi
      if [ "$force" != 1 ]; then
        echo "warning: 已存在指向其他位置的链接，跳过（可用 -f 重建）: $target" >&2
        continue
      fi
      remove_link "$target"
    elif [ -d "$target" ] && [ -f "$target/SKILL.md" ]; then
      if [ "$force" != 1 ]; then
        echo "warning: 已存在旧副本而非链接，跳过（可用 -f 替换为链接）: $target" >&2
        continue
      fi
      echo "warning: 将删除旧副本并替换为链接（因指定 -f）: $target" >&2
      rm -rf "$target"
    else
      echo "warning: 已存在非本技能目录，跳过: $target" >&2
      continue
    fi
  fi

  make_link "$target" "$skill_src"
done

if [ "$uninstall" = 1 ]; then echo 'uninstall done.'; else echo 'install done.'; fi
