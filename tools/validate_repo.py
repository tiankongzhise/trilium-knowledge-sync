#!/usr/bin/env python3
"""Repository validation for trilium-knowledge-sync.

Uses only the Python standard library so it can run in minimal CI images.
"""

from __future__ import annotations

import re
import subprocess
import sys
import urllib.parse
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_NAME = "trilium-knowledge-sync"
SKILL_DIR = REPO_ROOT / "skill" / SKILL_NAME
SKILL_MD = SKILL_DIR / "SKILL.md"
HELPER = SKILL_DIR / "scripts" / "trilium_etapi.py"

REQUIRED_PATHS = [
    "README.md",
    "LICENSE",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SUPPORT.md",
    "CHANGELOG.md",
    "AGENTS.md",
    ".gitignore",
    ".gitattributes",
    "install.ps1",
    "install.sh",
    "docs/getting-started.md",
    "docs/installation.md",
    "docs/configuration.md",
    "docs/usage-for-agents.md",
    "docs/cli-reference.md",
    "docs/security.md",
    "docs/architecture.md",
    "docs/PROJECT_DISCOVERY.md",
    "docs/PROJECT_STATE.md",
    "docs/PRD.md",
    "docs/TEST_PLAN.md",
    "docs/development.md",
    "docs/troubleshooting.md",
    "tests/test_trilium_etapi.py",
    "tests/test_validate_repo.py",
    "tools/verify.py",
    ".github/workflows/ci.yml",
    ".github/workflows/release.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
    "skill/trilium-knowledge-sync/SKILL.md",
    "skill/trilium-knowledge-sync/scripts/trilium_etapi.py",
]

ALLOWED_FRONTMATTER_KEYS = {
    "name",
    "description",
    "license",
    "allowed-tools",
    "metadata",
    "argument-hint",
    "model",
    "subagent",
    "agent",
    "permissions",
    "triggers",
}

REQUIRED_SKILL_CONCEPTS = [
    "当前对话",
    "token",
    "ETAPI",
    "SQLite",
    "upsert-note",
    "写后核验",
    "禁止",
]

# Documentation governance: transitional state phrases ("not done yet" style)
# may only live in the state register and the append-only changelog. Everywhere
# else they are guaranteed to rot — this is the authoritative list referenced
# by AGENTS.md; changing it is a governance change.
STATE_PHRASES = [
    "待确认",
    "待办",
    "TODO",
    "FIXME",
    "未决",
    "尚无",
    "仍应",
    "待实现",
    "待补充",
    "尚未配置",
    "尚未支持",
    "尚未实现",
    "尚未完成",
    "计划支持",
    "未来会",
    "将来会",
]

STATE_PHRASE_WHITELIST = {
    "docs/PROJECT_STATE.md",
    "CHANGELOG.md",
}

DOC_MAP_HEADING = "### 文档地图"

errors: list[str] = []


def fail(message: str) -> None:
    errors.append(message)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def parse_frontmatter(text: str) -> tuple[dict[str, object], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing opening frontmatter delimiter")
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        raise ValueError("missing closing frontmatter delimiter")

    result: dict[str, object] = {}
    current_key: Optional[str] = None
    for raw in lines[1:end]:
        if not raw.strip():
            continue
        if raw.startswith((" ", "\t")):
            item = raw.strip()
            if item.startswith("-") and current_key:
                result.setdefault(current_key, [])
                if not isinstance(result[current_key], list):
                    raise ValueError(f"frontmatter key {current_key!r} mixes scalar and list values")
                result[current_key].append(item[1:].strip())
            continue
        if ":" not in raw:
            raise ValueError(f"invalid frontmatter line: {raw}")
        key, value = raw.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"\'')
        current_key = key
        result[key] = value if value else []
    return result, "\n".join(lines[end + 1 :])


def validate_required_paths() -> None:
    for relative in REQUIRED_PATHS:
        if not (REPO_ROOT / relative).exists():
            fail(f"missing required path: {relative}")


def validate_skill() -> None:
    if not SKILL_MD.exists():
        return
    try:
        frontmatter, body = parse_frontmatter(read_text(SKILL_MD))
    except ValueError as exc:
        fail(f"SKILL.md frontmatter invalid: {exc}")
        return

    unknown = sorted(set(frontmatter) - ALLOWED_FRONTMATTER_KEYS)
    if unknown:
        fail(f"SKILL.md frontmatter has unsupported keys: {', '.join(unknown)}")

    name = frontmatter.get("name")
    if name != SKILL_NAME:
        fail(f"SKILL.md name must equal directory name {SKILL_NAME!r}, got {name!r}")
    if isinstance(name, str) and not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        fail("SKILL.md name must use lowercase hyphenated format")

    description = frontmatter.get("description")
    if not isinstance(description, str) or not description.strip():
        fail("SKILL.md description is missing")
    elif len(description) > 1024:
        fail("SKILL.md description exceeds 1024 characters")

    allowed_tools = frontmatter.get("allowed-tools")
    if allowed_tools is not None and not isinstance(allowed_tools, list):
        fail("SKILL.md allowed-tools must be a list")

    for concept in REQUIRED_SKILL_CONCEPTS:
        if concept not in body and concept not in str(description):
            fail(f"SKILL.md is missing required safety/behavior concept: {concept}")

    hard_rules = [
        "根据历史对话、经验或本项目文档假设位置",
        "永不打印、记录、提交、复制到笔记",
        "禁止默认直接写 `document.db` / SQLite / WAL",
        "禁止扫描或枚举无关凭据",
    ]
    for rule in hard_rules:
        if rule not in body:
            fail(f"SKILL.md missing hard rule text: {rule}")


def validate_helper() -> None:
    if not HELPER.exists():
        return
    source = read_text(HELPER)
    try:
        compile(source, str(HELPER), "exec")
    except SyntaxError as exc:
        fail(f"trilium_etapi.py has a syntax error: {exc}")
        return

    if 'add_argument("--token"' in source or "add_argument('--token'" in source:
        fail("trilium_etapi.py must not accept a literal --token argument")
    if 'source == "stdin"' in source or "source == 'stdin'" in source:
        fail("trilium_etapi.py must not accept stdin as a token source (owner decision 2026-11-25)")
    if "allow_abbrev=False" not in source:
        fail("argparse must disable abbreviations so --token cannot alias --token-source")
    for source_type in ("win-cred:", "file:", "env:"):
        if source_type not in source:
            fail(f"trilium_etapi.py does not document/support token source type {source_type}")
    if "Authorization" not in source or "Bearer " not in source:
        fail("trilium_etapi.py does not appear to implement ETAPI authorization")
    if "def upsert_note" not in source:
        fail("trilium_etapi.py is missing upsert_note")


def validate_markdown_links() -> None:
    link_re = re.compile(r"(?<!!)\[[^\]\n]+\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
    for md in iter_markdown_files(REPO_ROOT):
        text = read_text(md)
        for match in link_re.finditer(text):
            target = match.group(1).strip("<>")
            if target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            target = urllib.parse.unquote(target.split("#", 1)[0].split("?", 1)[0])
            if not target:
                continue
            resolved = (md.parent / target).resolve()
            try:
                resolved.relative_to(REPO_ROOT)
            except ValueError:
                fail(f"{md.relative_to(REPO_ROOT)} links outside repository: {target}")
                continue
            if not resolved.exists():
                fail(f"{md.relative_to(REPO_ROOT)} has broken relative link: {target}")


def validate_install_scripts() -> None:
    ps1_path = REPO_ROOT / "install.ps1"
    ps1 = read_text(ps1_path) if ps1_path.exists() else ""
    sh = read_text(REPO_ROOT / "install.sh") if (REPO_ROOT / "install.sh").exists() else ""
    if ps1_path.exists() and not ps1_path.read_bytes().startswith(b"\xef\xbb\xbf"):
        fail("install.ps1 must be UTF-8 with BOM so Windows PowerShell 5.1 parses CJK text correctly")
    for content, label in ((ps1, "install.ps1"), (sh, "install.sh")):
        if "trilium-knowledge-sync" not in content:
            fail(f"{label} does not reference the skill name")
        if "SKILL.md" not in content:
            fail(f"{label} does not validate SKILL.md before linking")
        if "Force" not in content and "-f" not in content:
            fail(f"{label} does not expose an explicit force path for replacing old copies")
    if "New-Item -ItemType Junction" not in ps1:
        fail("install.ps1 does not create Windows junctions")
    if "mklink //J" not in sh or "ln -s" not in sh:
        fail("install.sh must support Windows junctions and POSIX symlinks")


def iter_repo_files(root: Path) -> list[Path]:
    """Return files that belong to the repository.

    Inside a git worktree only git-tracked (index/committed) files count as
    repository content: untracked local files (e.g. machine-local skills or
    scratch notes) are deliberately invisible to governance. Falls back to a
    working-tree scan outside git worktrees so tests on plain directories
    keep working.
    """
    try:
        proc = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=root, capture_output=True, timeout=30,
        )
        if proc.returncode == 0:
            return sorted(
                root / name
                for name in proc.stdout.decode("utf-8", "replace").split("\0")
                if name
            )
    except (OSError, subprocess.TimeoutExpired):
        pass
    return sorted(
        p for p in root.rglob("*") if ".git" not in p.parts and p.is_file()
    )


def iter_markdown_files(root: Path) -> list[Path]:
    return [p for p in iter_repo_files(root) if p.suffix == ".md"]


def find_state_phrase_violations(root: Path) -> list[str]:
    violations: list[str] = []
    for md in iter_markdown_files(root):
        relative = md.relative_to(root).as_posix()
        if relative in STATE_PHRASE_WHITELIST:
            continue
        text = read_text(md)
        for phrase in STATE_PHRASES:
            if phrase in text:
                violations.append(f"{relative} contains state phrase {phrase!r}")
    return violations


def parse_doc_map_entries(agents_text: str) -> Optional[list[str]]:
    lines = agents_text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip() == DOC_MAP_HEADING:
            start = i
            break
    if start is None:
        return None
    entries: list[str] = []
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if stripped.startswith("#"):
            break
        match = re.match(r"^\|\s*`([^`]+)`\s*\|", stripped)
        if match:
            entries.append(match.group(1).strip())
    return entries


def find_doc_map_violations(root: Path) -> list[str]:
    violations: list[str] = []
    agents_md = root / "AGENTS.md"
    if not agents_md.exists():
        return ["AGENTS.md is missing; cannot check document map"]
    entries = parse_doc_map_entries(read_text(agents_md))
    if entries is None:
        return [f"AGENTS.md is missing the document map section ({DOC_MAP_HEADING!r})"]
    if not entries:
        return ["AGENTS.md document map has no entries"]

    seen: set[str] = set()
    for entry in entries:
        if entry in seen:
            violations.append(f"document map has duplicate entry: {entry}")
        seen.add(entry)
        if not (root / entry).exists():
            violations.append(f"document map entry does not exist in repository: {entry}")

    listed = set(entries)
    for md in iter_markdown_files(root):
        relative = md.relative_to(root).as_posix()
        if relative not in listed:
            violations.append(f"{relative} is not registered in the AGENTS.md document map")
    return violations


def validate_doc_governance() -> None:
    for violation in find_state_phrase_violations(REPO_ROOT):
        fail(f"state phrase outside whitelist: {violation}")
    for violation in find_doc_map_violations(REPO_ROOT):
        fail(f"document map violation: {violation}")


def validate_no_common_secret_markers() -> None:
    markers = [
        "-----BEGIN PRIVATE KEY-----",
        "-----BEGIN RSA PRIVATE KEY-----",
        "-----BEGIN OPENSSH PRIVATE KEY-----",
    ]
    for path in sorted(REPO_ROOT.rglob("*")):
        if not path.is_file() or ".git" in path.parts or path.stat().st_size > 2_000_000:
            continue
        if path.resolve() == Path(__file__).resolve():
            continue
        try:
            text = read_text(path)
        except UnicodeDecodeError:
            continue
        for marker in markers:
            if marker in text:
                fail(f"possible private key material in {path.relative_to(REPO_ROOT)}")


def main() -> int:
    validate_required_paths()
    validate_skill()
    validate_helper()
    validate_markdown_links()
    validate_install_scripts()
    validate_doc_governance()
    validate_no_common_secret_markers()

    if errors:
        print("Repository validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    print("Repository validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
