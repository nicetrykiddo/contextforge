"""Adversarial reproductions against v3.4.0. Audit branch only.

Tests intentionally assert *undesirable existing behavior* to document verified
flaws, not acceptable semantics. Do not merge these assertions into production.
All paths and canaries are synthetic, under temporary directories.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

CLI = Path(__file__).resolve().parents[1] / "ctx.py"


class AdversarialReproductions(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="contextforge-repro-")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.project = self.base / "project"
        self.env = {**os.environ, "XDG_CONFIG_HOME": str(self.base / "config")}

    def cmd(self, *args, ok=True):
        p = subprocess.run([sys.executable, str(CLI), "--root", str(self.project), *args],
                           text=True, capture_output=True, env=self.env, timeout=30)
        if ok:
            self.assertEqual(p.returncode, 0, f"{args}: {p.stdout} {p.stderr}")
        return p

    def init(self):
        self.cmd("init", "--mode", "general")
        (self.project / ".ctx" / "MISSION.md").write_text(
            "# Task\nRestore a known local outcome; no external access.\n")

    def test_reproduces_symlink_handoff_overwrite_outside_project(self):
        self.init()
        outside = self.base / "external_file.txt"
        outside.write_text("DO_NOT_OVERWRITE_EXTERNAL_FILE", encoding="utf8")
        link = self.project / ".ctx" / "HANDOFF.md"
        link.symlink_to(outside)
        self.cmd("handoff", "--budget", "800")
        self.assertNotIn("DO_NOT_OVERWRITE_EXTERNAL_FILE", outside.read_text())
        self.assertIn("ContextForge", outside.read_text())
        print("REPRODUCED H1: handoff overwrote file OUTSIDE .ctx via symlink")

    def test_reproduces_snapshot_handoff_overwrite_outside_project(self):
        self.init()
        outside = self.base / "external_snapshot_target.txt"
        outside.write_text("DO_NOT_OVERWRITE_EXTERNAL_FILE", encoding="utf8")
        (self.project / ".ctx" / "HANDOFF.md").symlink_to(outside)
        self.cmd("snapshot")
        self.assertNotIn("DO_NOT_OVERWRITE_EXTERNAL_FILE", outside.read_text())
        self.assertIn("ContextForge", outside.read_text())
        print("REPRODUCED H2: snapshot overwrote file OUTSIDE .ctx via symlink")

    def test_reproduces_reading_mission_symlink_outside_project(self):
        self.init()
        outside = self.base / "external_sensitive_canary.txt"
        outside.write_text("UNAUTHORIZED-OUTSIDE-MISSION-CANARY-919", encoding="utf8")
        mission = self.project / ".ctx" / "MISSION.md"
        mission.unlink()
        mission.symlink_to(outside)
        result = self.cmd("context", "--budget", "1100")
        self.assertIn("UNAUTHORIZED-OUTSIDE-MISSION-CANARY-919", result.stdout)
        print("REPRODUCED H3: context read outside-project symlinked mission")

    def test_reproduces_cross_task_stale_checkpoint_false_alarm(self):
        self.init()
        a = self.cmd("task", "add", "First task", "--goal", "Recover A").stdout.split()[0]
        self.cmd("add", "--kind", "evidence", "--title", "A proof", "--body", "synthetic")
        self.cmd("checkpoint", "--summary", "A finished one step", "--next", "Check A next")
        b = self.cmd("task", "add", "Second task", "--goal", "Recover B").stdout.split()[0]
        self.cmd("task", "focus", b)
        self.cmd("add", "--kind", "note", "--title", "B unrelated note")
        self.cmd("task", "focus", a)
        snap = self.cmd("snapshot")
        self.assertIn("checkpoint missing/stale", snap.stdout)
        print("REPRODUCED H4: unrelated B record falsely marks A checkpoint stale")

    def test_reproduces_irrelevant_results_in_query_retrieval(self):
        self.init()
        self.cmd("task", "add", "Search", "--goal", "Only related findings")
        self.cmd("add", "--kind", "note", "--title", "IRRELEVANT-BLUEBERRY-EVIDENCE",
                 "--body", "completely unrelated to query")
        out = self.cmd("context", "--query", "xxxxxxxxunknownkeywordxyz", "--budget", "1500")
        self.assertIn("IRRELEVANT-BLUEBERRY-EVIDENCE", out.stdout)
        print("REPRODUCED H5: query with zero matches still emits unrelated record")

    def test_reproduces_snapshot_archive_write_via_symlinked_archive_dir(self):
        self.init()
        outside = self.base / "unrelated_directory"
        outside.mkdir()
        snap = self.project / ".ctx" / "compactions"
        snap.symlink_to(outside, target_is_directory=True)
        self.cmd("snapshot")
        self.assertTrue(list(outside.glob("*.zip")))
        print("REPRODUCED H6: compaction wrote archive outside root via symlinked directory")

    def test_reproduces_search_including_unrelated_task_private_records(self):
        self.init()
        first = self.cmd("task", "add", "Task A", "--goal", "Investigate A").stdout.split()[0]
        self.cmd("add", "--kind", "note", "--title", "CROSS-TARGET-CANARY-223")
        second = self.cmd("task", "add", "Task B", "--goal", "Investigate B").stdout.split()[0]
        self.cmd("task", "focus", second)
        results = self.cmd("search", "CROSS-TARGET-CANARY").stdout
        self.assertIn("CROSS-TARGET-CANARY-223", results)
        self.assertNotEqual(first, second)
        print("REPRODUCED H8: search defaults to cross-task evidence while context is task-scoped")

    def test_reproduces_installed_agents_md_recommends_stale_shared_recovery(self):
        self.init()
        instructions = (self.project / "AGENTS.md").read_text()
        self.assertIn("read `.ctx/MISSION.md` directly", instructions)
        self.assertIn("Recover from `.ctx/HANDOFF.md` after compaction", instructions)
        print("REPRODUCED H9: newly initialized AGENTS.md contradicts active-task hook/skill")

    def test_reproduces_new_task_does_not_focus_and_records_go_to_old_task(self):
        self.init()
        first = self.cmd("task", "add", "Task A", "--goal", "Investigate A").stdout.split()[0]
        second = self.cmd("task", "add", "Task B", "--goal", "Investigate B").stdout.split()[0]
        self.cmd("add", "--kind", "note", "--title", "MEANT-FOR-NEW-SECOND-TASK")
        record = json.loads((self.project / ".ctx/records.jsonl").read_text().splitlines()[-1])
        self.assertEqual(record["task"], first)
        self.assertNotEqual(record["task"], second)
        print("REPRODUCED H10: create B leaves A active; implicit record gets attributed to A")

    def test_reproduces_active_task_scan_drops_other_task_inventory(self):
        self.init()
        (self.project / "a").mkdir()
        (self.project / "b").mkdir()
        (self.project / "a" / "a-evidence.txt").write_text("A")
        (self.project / "b" / "b-evidence.txt").write_text("B")
        first = self.cmd("task", "add", "Task A", "--goal", "Preserve A", "--scope", "a").stdout.split()[0]
        self.cmd("scan")
        state = json.loads((self.project / ".ctx/state.json").read_text())
        self.assertIn("a/a-evidence.txt", state["inventory"])
        second = self.cmd("task", "add", "Task B", "--goal", "Preserve B", "--scope", "b").stdout.split()[0]
        self.cmd("task", "focus", second)
        self.cmd("scan")
        state = json.loads((self.project / ".ctx/state.json").read_text())
        self.assertNotIn("a/a-evidence.txt", state["inventory"])
        self.assertIn("b/b-evidence.txt", state["inventory"])
        print("REPRODUCED H11: default scan of B silently erases A entries in shared file inventory")

    def test_reproduces_automated_global_lesson_approval_without_human_auth(self):
        self.init()
        msg = self.cmd("reasoning", "propose", "--principle",
            "A tool success message need not prove the observable user goal",
            "--when", "A tool returns accepted but downstream effect unconfirmed",
            "--response", "Check evidence of the actual final state first").stdout
        found = re.search(r"\bL-[a-f0-9]+\b", msg)
        self.assertIsNotNone(found)
        self.cmd("reasoning", "approve", found.group(0))
        store = json.loads((self.base / "config/contextforge/reasoning.json").read_text())
        self.assertEqual(store["lessons"][0]["status"], "approved")
        print("REPRODUCED H7: approval requires no interactive or out-of-band human confirmation")


if __name__ == "__main__":
    unittest.main()
