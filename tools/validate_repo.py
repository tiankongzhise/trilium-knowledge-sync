#!/usr/bin/env python3
"""Repository validation for trilium-knowledge-sync.

Uses only the Python standard library so it can run in minimal CI images.
"""

from __future__ import annotations

import re
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
    "docs/PRD.md",
    "docs/TEST_PLAN.md",
    "docs/development.md",
    "docs/troubleshooting.md",
    "tests/test_trilium_etapi.py",
    ".github/workflows/ci.yml",
    ".github/workflows/release.yml",
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
    if "allow_abbrev=False" not in source:
        fail("argparse must disable abbreviations so --token cannot alias --token-source")
    for source_type in ("win-cred:", "file:", "env:", "stdin"):
        if source_type not in source:
            fail(f"trilium_etapi.py does not document/support token source type {source_type}")
    if "Authorization" not in source or "Bearer " not in source:
        fail("trilium_etapi.py does not appear to implement ETAPI authorization")
    if "def upsert_note" not in source:
        fail("trilium_etapi.py is missing upsert_note")


def validate_markdown_links() -> None:
    link_re = re.compile(r"(?<!!)\[[^\]\n]+\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
    for md in sorted(REPO_ROOT.rglob("*.md")):
        if ".git" in md.parts:
            continue
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
    ps1 = read_text(REPO_ROOT / "install.ps1") if (REPO_ROOT / "install.ps1").exists() else ""
    sh = read_text(REPO_ROOT / "install.sh") if (REPO_ROOT / "install.sh").exists() else ""
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
