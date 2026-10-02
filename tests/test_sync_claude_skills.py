""" .claude/skills/ is a copy of .agents/skills/. """

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "sync_claude_skills", ROOT / "scripts" / "sync-claude-skills.py"
)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
diff_skills = _mod.diff_skills
sync_skills = _mod.sync_skills


class SyncClaudeSkillsTests(unittest.TestCase):
    def test_repo_copy_matches_source(self) -> None:
        self.assertEqual(diff_skills(), [])

    def test_check_and_write_roundtrip(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        src = tmp / "agents"
        dst = tmp / "claude"
        (src / "publish").mkdir(parents=True)
        (src / "publish" / "SKILL.md").write_text("source\n", encoding="utf-8")
        self.assertTrue(diff_skills(src, dst))
        sync_skills(src, dst)
        self.assertEqual(diff_skills(src, dst), [])
        (dst / "publish" / "SKILL.md").write_text("stale\n", encoding="utf-8")
        issues = diff_skills(src, dst)
        self.assertEqual(len(issues), 1)
        self.assertIn("differs", issues[0])
        sync_skills(src, dst)
        self.assertEqual(diff_skills(src, dst), [])


if __name__ == "__main__":
    unittest.main()
