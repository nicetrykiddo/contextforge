"""Decision continuity across task switches and compaction; offline-only regression."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

CLI = Path(__file__).resolve().parents[1] / 'ctx.py'
SKILL = Path(__file__).resolve().parents[1] / '.agents/skills/contextforge/SKILL.md'


class DecisionContinuityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'project'
        self.env = dict(os.environ, XDG_CONFIG_HOME=str(Path(self.tmp.name) / 'config'))

    def cli(self, *args):
        p = subprocess.run([sys.executable, str(CLI), '--root', str(self.root), *args],
                           capture_output=True, text=True, env=self.env, timeout=25)
        self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
        return p.stdout

    def test_reason_and_pivot_survive_compaction_and_task_switch(self):
        self.cli('init', '--mode', 'general')
        first = self.cli('task', 'add', 'Target A', '--goal', 'Deliver verified result A').split()[0]
        (self.root / '.ctx/MISSION.md').write_text(
            '# Goal\nMeet acceptance test A, not mere activity.\n')
        self.cli('checkpoint', '--summary', 'Initial observation exists',
                 '--next', 'Run a discriminating check',
                 '--why-next', 'Can separate two hypotheses under test',
                 '--pivot-if', 'Matched negative control has identical output',
                 '--verified-by', 'fixture.txt:1')
        second = self.cli('task', 'add', 'Target B', '--goal', 'Deliver verified result B').split()[0]
        self.cli('task', 'focus', second)
        b_text = self.cli('context', '--budget', '900')
        self.assertNotIn('Matched negative control has identical output', b_text)
        self.cli('task', 'focus', first)
        a_text = self.cli('context', '--budget', '900')
        self.assertIn('Why this next: Can separate two hypotheses under test', a_text)
        self.assertIn('Reconsider if: Matched negative control has identical output', a_text)
        self.cli('snapshot')
        with zipfile.ZipFile(sorted((self.root / '.ctx/compactions').glob('*.zip'))[-1]) as z:
            state = json.loads(z.read('state.json'))
            self.assertEqual(state['checkpoints'][first]['pivot_if'],
                             'Matched negative control has identical output')
            self.assertEqual(state['checkpoints'][first]['why_next'],
                             'Can separate two hypotheses under test')
        tiny = self.cli('context', '--budget', '140')
        self.assertIn('Reconsider if:', tiny)
        self.assertIn('Run a discriminating check', tiny)

    def test_old_checkpoint_and_short_work_still_work(self):
        self.cli('init', '--mode', 'software')
        self.cli('task', 'add', 'Short bug', '--goal', 'Fix accepted test')
        self.cli('checkpoint', '--summary', 'Failure reproduced',
                 '--next', 'Fix the implementation')
        text = self.cli('context', '--budget', '500')
        self.assertIn('Failure reproduced', text)
        self.assertIn('Fix the implementation', text)
        self.assertNotIn('Why this next:', text)
        self.assertNotIn('Reconsider if:', text)

    def test_lifecycle_hooks_recover_active_task_not_shared_stale_handoff(self):
        self.cli('init', '--mode', 'general')
        self.cli('task', 'add', 'First', '--goal', 'First outcome')
        second = self.cli('task', 'add', 'Second', '--goal', 'Second outcome').split()[0]
        self.cli('task', 'focus', second)
        for event in ('SessionStart', 'PostCompact'):
            payload = json.dumps({'hook_event_name': event,
                                  'cwd': str(self.root), 'session_id': 'fixture'})
            p = subprocess.run([sys.executable, str(CLI), 'hook'], input=payload,
                               capture_output=True, text=True, env=self.env, timeout=20)
            self.assertEqual(p.returncode, 0, p.stderr)
            response = json.loads(p.stdout)
            raw = json.dumps(response)
            self.assertIn('contextforge context --budget 1200', raw)
            self.assertNotIn('read .ctx/MISSION.md and .ctx/HANDOFF.md', raw)
            self.assertIn('active task', raw.lower())

    def test_rethink_is_optional_and_outcome_focused(self):
        self.cli('init', '--mode', 'general')
        self.cli('task', 'add', 'Open question', '--goal', 'Deliver evidence-backed answer')
        output = self.cli('rethink', '--budget', '900')
        self.assertIn('OPTIONAL DECISION REVIEW', output)
        self.assertIn('acceptance criteria', output)
        self.assertIn('repeat a premise', output)
        self.assertNotIn('must answer before trying', output)

    def test_optional_review_distinguishes_proxy_evidence_before_scaling(self):
        self.cli('init', '--mode', 'software')
        self.cli('task', 'add', 'Repair database transaction rollback',
                 '--goal', 'Preserve data after failed commit')
        self.cli('add', '--kind', 'evidence', '--status', 'verified',
                 '--title', 'Unit test measured the retry path',
                 '--proof', 'local test result: retry reached expected branch')
        self.cli('checkpoint', '--summary', 'A partial behavior was observed',
                 '--next', 'Check transaction rollback under concurrent writes')
        hot = self.cli('context', '--budget', '1000')
        self.assertIn('Check transaction rollback', hot)
        self.assertNotIn('small pilot, measured effect', hot)
        review = self.cli('rethink', '--budget', '900')
        self.assertIn('small pilot, measured effect', review)
        self.assertIn('tested proxies from the full success criterion', review)
        self.assertIn('A partial behavior was observed', review)
        # The review is advisory; continued productive iteration is permitted.
        self.cli('checkpoint', '--summary', 'Second fixture reproduces the race',
                 '--next', 'Implement atomic rollback')
        self.assertIn('Implement atomic rollback',
                      self.cli('context', '--budget', '1000'))

    def test_skill_does_not_assume_contextforge_was_executed(self):
        instructions = SKILL.read_text()
        self.assertIn('verify `contextforge` is available', instructions)
        self.assertIn('do not claim that ContextForge commands', instructions)
        self.assertIn('a proxy, partial result', instructions)

    def test_global_installer_copies_decision_quality_reference(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as home:
            env = dict(os.environ, HOME=home)
            p = subprocess.run(['bash', str(repo / 'install.sh')],
                               capture_output=True, text=True, env=env, timeout=25)
            self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
            self.assertTrue((Path(home) / '.agents/skills/contextforge/references/decision-quality.md').is_file())
            self.assertTrue((Path(home) / '.agents/skills/contextforge/SKILL.md').is_file())
            self.assertTrue((Path(home) / '.local/bin/contextforge').is_file())

    def test_global_skill_stays_optional_and_general(self):
        text = SKILL.read_text()
        self.assertIn('research, debugging, authorized security testing, coding', text)
        self.assertIn('why the next step', text)
        self.assertIn('not a mandatory checklist', text)
        self.assertIn('Do not change the model', text)


if __name__ == '__main__':
    unittest.main()
