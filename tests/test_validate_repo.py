#!/usr/bin/env python3
"""Unit tests for the documentation governance checks in tools/validate_repo.py."""

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import validate_repo as vr  # noqa: E402


def write_file(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_agents_md(entries: list[str]) -> str:
    rows = "\n".join(f"| `{entry}` | 规范 | 职责 | 事实域 | — |" for entry in entries)
    return (
        "# project\n\n"
        "### 文档地图\n\n"
        "| 文档 | 类型 | 唯一职责 | 拥有的事实域 | 禁写内容 |\n"
        "|---|---|---|---|---|\n"
        f"{rows}\n\n"
        "### 下一节\n"
    )


class StatePhraseTests(unittest.TestCase):
    def test_phrase_in_normal_doc_is_violation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "docs/some.md", "这里尚无定论。\n")
            violations = vr.find_state_phrase_violations(root)
            self.assertEqual(len(violations), 1)
            self.assertIn("docs/some.md", violations[0])
            self.assertIn("尚无", violations[0])

    def test_phrase_allowed_in_whitelisted_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "docs/PROJECT_STATE.md", "开放事项：尚无结论，待确认。\n")
            write_file(root, "CHANGELOG.md", "TODO 历史遗留记录。\n")
            write_file(root, "docs/clean.md", "这是普通描述，没有状态词句。\n")
            self.assertEqual(vr.find_state_phrase_violations(root), [])

    def test_clean_repo_has_no_violations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "README.md", "一切正常。\n")
            self.assertEqual(vr.find_state_phrase_violations(root), [])

    def test_every_listed_phrase_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "docs/x.md", "\n".join(vr.STATE_PHRASES))
            violations = vr.find_state_phrase_violations(root)
            self.assertEqual(len(violations), len(vr.STATE_PHRASES))

    def test_files_inside_git_directory_are_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, ".git/hooks/sample.md", "TODO\n")
            self.assertEqual(vr.find_state_phrase_violations(root), [])


class DocMapParseTests(unittest.TestCase):
    def test_parse_entries(self):
        text = make_agents_md(["AGENTS.md", "docs/PRD.md"])
        self.assertEqual(vr.parse_doc_map_entries(text), ["AGENTS.md", "docs/PRD.md"])

    def test_parse_stops_at_next_heading(self):
        text = make_agents_md(["AGENTS.md"]) + "| `docs/late.md` | 规范 | x | y | — |\n"
        self.assertEqual(vr.parse_doc_map_entries(text), ["AGENTS.md"])

    def test_missing_section_returns_none(self):
        self.assertIsNone(vr.parse_doc_map_entries("# project\n\nno map here\n"))

    def test_header_row_is_not_an_entry(self):
        entries = vr.parse_doc_map_entries(make_agents_md(["AGENTS.md"]))
        self.assertNotIn("文档", entries)


class DocMapViolationTests(unittest.TestCase):
    def build_root(self, root: Path, entries: list[str], files: list[str]) -> None:
        write_file(root, "AGENTS.md", make_agents_md(entries))
        for relative in files:
            if relative == "AGENTS.md":
                continue  # already written with the document map content above
            write_file(root, relative, "content\n")

    def test_unregistered_markdown_file_is_violation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.build_root(root, ["AGENTS.md"], ["AGENTS.md", "docs/orphan.md"])
            violations = vr.find_doc_map_violations(root)
            self.assertTrue(any("docs/orphan.md" in v for v in violations), violations)

    def test_missing_entry_file_is_violation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.build_root(root, ["AGENTS.md", "docs/ghost.md"], ["AGENTS.md"])
            violations = vr.find_doc_map_violations(root)
            self.assertTrue(any("docs/ghost.md" in v for v in violations), violations)

    def test_duplicate_entry_is_violation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.build_root(root, ["AGENTS.md", "AGENTS.md"], ["AGENTS.md"])
            violations = vr.find_doc_map_violations(root)
            self.assertTrue(any("duplicate" in v for v in violations), violations)

    def test_consistent_map_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.build_root(
                root,
                ["AGENTS.md", "docs/PRD.md", ".github/pull_request_template.md"],
                ["AGENTS.md", "docs/PRD.md", ".github/pull_request_template.md"],
            )
            self.assertEqual(vr.find_doc_map_violations(root), [])

    def test_missing_map_section_is_violation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "AGENTS.md", "# project\n")
            violations = vr.find_doc_map_violations(root)
            self.assertEqual(len(violations), 1)
            self.assertIn("document map section", violations[0])


class RealRepoTests(unittest.TestCase):
    """The repository itself must satisfy the governance checks."""

    def test_repo_has_no_state_phrase_violations(self):
        self.assertEqual(vr.find_state_phrase_violations(REPO_ROOT), [])

    def test_repo_document_map_is_complete(self):
        self.assertEqual(vr.find_doc_map_violations(REPO_ROOT), [])


if __name__ == "__main__":
    unittest.main()
