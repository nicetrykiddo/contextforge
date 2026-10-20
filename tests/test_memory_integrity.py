"""State isolation, recovery, privacy, and concurrency regressions."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
from concurrent.futures import ThreadPoolExecutor

CLI = Path(__file__).resolve().parents[1] / 'ctx.py'


class MemoryIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.project = self.base / 'workspace'
        self.env = dict(os.environ, XDG_CONFIG_HOME=str(self.base / 'config'))

    def cmd(self, *args, ok=True):
        result = subprocess.run([sys.executable, str(CLI), '--root', str(self.project), *args],
                                capture_output=True, text=True, env=self.env, timeout=20)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def task(self, name, goal):
        out = self.cmd('task', 'add', name, '--goal', goal).stdout
        return out.split()[0]

    def test_task_mission_checkpoint_snapshot_isolation(self):
        self.cmd('init', '--mode', 'bugbounty')
        a = self.task('Target A', 'Investigate A')
        shared = self.project / '.ctx/MISSION.md'
        shared.write_text('MISSION A ONLY: investigate app.alpha.example\n')
        self.cmd('checkpoint', '--summary', 'A STATE MUST SURVIVE',
                 '--next', 'Recheck the A proof')
        b = self.task('Target B', 'Investigate B')
        mission_a = self.project / '.ctx/tasks' / a / 'MISSION.md'
        mission_b = self.project / '.ctx/tasks' / b / 'MISSION.md'
        self.assertIn('MISSION A ONLY', mission_a.read_text())
        self.assertIn('REPLACE_ME', mission_b.read_text())
        mission_b.write_text('MISSION B ONLY: investigate app.beta.example\n')
        self.cmd('task', 'focus', b)
        self.cmd('checkpoint', '--summary', 'B STATE MUST SURVIVE',
                 '--next', 'Recheck the B proof')
        b_text = self.cmd('context', '--budget', '1500').stdout
        self.assertIn('MISSION B ONLY', b_text)
        self.assertIn('B STATE MUST SURVIVE', b_text)
        self.assertNotIn('MISSION A ONLY', b_text)
        self.assertNotIn('A STATE MUST SURVIVE', b_text)
        self.cmd('task', 'focus', a)
        a_text = self.cmd('context', '--budget', '1500').stdout
        self.assertIn('MISSION A ONLY', a_text)
        self.assertIn('A STATE MUST SURVIVE', a_text)
        self.assertNotIn('B STATE MUST SURVIVE', a_text)
        self.cmd('snapshot')
        archive = sorted((self.project / '.ctx/compactions').glob('*.zip'))[-1]
        with zipfile.ZipFile(archive) as z:
            self.assertIn(f'tasks/{a}/MISSION.md', z.namelist())
            self.assertIn(f'tasks/{b}/MISSION.md', z.namelist())

    def test_corrupt_global_reasoning_does_not_break_local_context(self):
        self.cmd('init')
        self.task('Investigate', 'Verify tool acceptance with no visible effect')
        self.cmd('checkpoint', '--summary', 'IMPORTANT LOCAL EVIDENCE',
                 '--next', 'Continue experiment')
        global_file = self.base / 'config/contextforge/reasoning.json'
        global_file.parent.mkdir(parents=True)
        global_file.write_text('{ this is broken JSON')
        text = self.cmd('context', '--budget', '1200').stdout
        self.assertIn('IMPORTANT LOCAL EVIDENCE', text)
        self.assertIn('Optional global reasoning unavailable', text)

    def test_query_relevant_evidence_survives_many_pins(self):
        self.cmd('init')
        self.task('Investigation', 'Review a distinct observation')
        self.cmd('checkpoint', '--summary', 'Baseline reproduced', '--next', 'Inspect relevant record')
        for i in range(15):
            self.cmd('pin', '--title', f'Unrelated clue {i}', '--body',
                     'Unrelated observation from the earlier source ' * 5,
                     '--status', 'verified', '--proof', f'fixture.log:{i+1}')
        self.cmd('add', '--kind', 'finding', '--title', 'VERY SPECIAL PARSER SIGNAL',
                 '--body', 'Distinguishing keyword raven artifact',
                 '--status', 'verified', '--proof', 'fixture.log:99')
        output = self.cmd('context', '--query', 'raven', '--budget', '350').stdout
        self.assertIn('VERY SPECIAL PARSER SIGNAL', output)

    def test_changed_proof_file_is_detected(self):
        self.cmd('init')
        self.task('Evidence', 'Validate file digests')
        artifact = self.project / 'fixture.txt'
        artifact.write_text('original observation')
        self.cmd('add', '--kind', 'evidence', '--title', 'Fixture response',
                 '--status', 'verified', '--proof-file', 'fixture.txt')
        self.assertEqual(self.cmd('check').returncode, 0)
        artifact.write_text('tampered observation')
        failure = self.cmd('check', ok=False)
        self.assertEqual(failure.returncode, 1)
        self.assertIn('proof artifact changed', failure.stdout)

    def test_handoff_does_not_rescan_full_workspace_by_default(self):
        self.cmd('init')
        self.task('Fast handoff', 'Maintain minimal context')
        (self.project / 'new.txt').write_text('unindexed')
        self.cmd('handoff', '--budget', '900')
        state = json.loads((self.project / '.ctx/state.json').read_text())
        self.assertNotIn('new.txt', state['inventory'])
        self.cmd('handoff', '--refresh', '--budget', '900')
        state = json.loads((self.project / '.ctx/state.json').read_text())
        self.assertIn('new.txt', state['inventory'])

    def test_audit_checks_active_task_mission(self):
        self.cmd('init')
        self.task('First target', 'First goal')
        (self.project / '.ctx/MISSION.md').write_text('First task source')
        b = self.task('Second target', 'Second goal')
        self.cmd('task', 'focus', b)
        self.assertIn('Original mission is not anchored', self.cmd('audit').stdout)

    def test_private_state_permissions(self):
        self.cmd('init')
        self.task('A', 'One')
        self.task('B', 'Two')
        for part in ['.ctx', '.ctx/tasks']:
            fp = self.project / part
            self.assertEqual(fp.stat().st_mode & 0o777, 0o700)
        for part in ['.ctx/state.json', '.ctx/records.jsonl']:
            fp = self.project / part
            self.assertEqual(fp.stat().st_mode & 0o777, 0o600)

    def test_concurrent_writers_do_not_lose_updates(self):
        self.cmd('init')
        self.task('Concurrent', 'Ensure no state lost')
        def writer(i):
            return self.cmd('add', '--kind', 'note', '--title', f'Parallel note {i}')
        with ThreadPoolExecutor(max_workers=6) as executor:
            list(executor.map(writer, range(16)))
        lines = (self.project / '.ctx/records.jsonl').read_text().strip().splitlines()
        self.assertEqual(len(lines), 16)
        self.assertEqual(len({json.loads(line)['id'] for line in lines}), 16)
        self.assertEqual(self.cmd('check').returncode, 0)


if __name__ == '__main__':
    unittest.main()
