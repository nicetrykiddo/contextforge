"""Impact-driven workflow regressions, motivated by plausible real usage.

These tests deliberately fail against v3.4.1 to distinguish a harmful behavior
from a mere novelty of synthetic attack fixtures. No network access.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CLI = Path(__file__).resolve().parents[1] / "ctx.py"

class PracticalImpactTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory(prefix="cf-impact-")
        self.addCleanup(t.cleanup)
        self.project=Path(t.name)/"project"
        self.env={**os.environ,"XDG_CONFIG_HOME":str(Path(t.name)/"config")}
        self.run_cli("init","--mode","general")
    def run_cli(self,*args,success=True):
        result=subprocess.run([sys.executable,str(CLI),"--root",str(self.project),*args],
                   text=True,capture_output=True,env=self.env,timeout=20)
        if success: self.assertEqual(result.returncode,0,result.stderr+result.stdout)
        return result

    def test_creating_backlog_task_does_not_discard_existing_active_context(self):
        # Real-world: agent adds a follow-up item while actively debugging A.
        a=self.run_cli("task","add","Fix production bug","--goal","Finish A").stdout.split()[0]
        self.run_cli("checkpoint","--summary","A checkpoint","--next","Complete A verification")
        b=self.run_cli("task","add","Follow up on docs","--goal","Later B").stdout.split()[0]
        state=json.loads((self.project/".ctx/state.json").read_text())
        self.assertNotEqual(a,b)
        self.assertEqual(state["active_task"],a,
                         "Adding backlog work silently changes active context")
        self.assertIn("A checkpoint",self.run_cli("context","--budget","800").stdout)

    def test_task_add_focus_option_explicitly_switches_context(self):
        a=self.run_cli("task","add","A").stdout.split()[0]
        b=self.run_cli("task","add","B","--focus").stdout.split()[0]
        state=json.loads((self.project/".ctx/state.json").read_text())
        self.assertEqual(state["active_task"],b)
        self.assertNotEqual(a,b)

    def test_scanned_deleted_file_does_not_remain_live_in_overlap(self):
        # Most projects use the default scope '.', so overlapping tasks are normal.
        f=self.project/"src"/"old.txt"
        f.parent.mkdir()
        f.write_text("hello")
        self.run_cli("task","add","A","--scope",".")
        self.run_cli("scan")
        self.run_cli("task","add","B","--scope","src")
        self.run_cli("task","focus",self.run_cli("task","add","C","--scope",".").stdout.split()[0])
        f.unlink()
        self.run_cli("scan")
        state=json.loads((self.project/".ctx/state.json").read_text())
        self.assertNotIn("src/old.txt",state["inventory"],
            "A completed scan still advertises a file known to be deleted")

    def test_closed_task_cannot_be_implicitly_reactivated(self):
        a=self.run_cli("task","add","Finished A").stdout.split()[0]
        self.run_cli("task","close",a)
        r=self.run_cli("task","focus",a,success=False)
        self.assertNotEqual(r.returncode,0,
            "Task focus silently makes a closed task active without reopening status")
        state=json.loads((self.project/".ctx/state.json").read_text())
        self.assertEqual(state["tasks"][a]["status"],"closed")
        self.assertIsNone(state["active_task"])

if __name__=="__main__":
    unittest.main()
