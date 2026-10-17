import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

CLI = Path(__file__).resolve().parents[1] / 'ctx.py'

class ContextForgeMixin:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'project'
        self.root.mkdir()
    def tearDown(self):
        self.temp.cleanup()
    def cmd(self, *args, ok=True):
        p = subprocess.run([sys.executable, str(CLI), '--root', str(self.root), *args],
                           capture_output=True, text=True)
        if ok:
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        return p
    def init(self, mode='ctf', scope='.'):
        return self.cmd('init', '--mode', mode, '--scope', scope)
    def tid(self):
        state = json.loads((self.root / '.ctx/state.json').read_text())
        return state['active_task']
    def rec_id(self):
        raw = (self.root / '.ctx/records.jsonl').read_text().strip().splitlines()
        return json.loads(raw[-1])['id']

class ContextForgeTests(ContextForgeMixin, unittest.TestCase):
    def test_happy_path_and_handoff(self):
        (self.root / 'src').mkdir()
        (self.root / 'src' / 'handler.py').write_text('print(42)\n')
        self.init(scope='src')
        self.cmd('task', 'add', 'Investigate parser', '--scope', 'src', '--goal', 'Find root cause')
        self.cmd('scan')
        self.cmd('add', '--kind', 'evidence', '--status', 'verified', '--title', 'Parser trace',
                 '--body', 'Unit test fails on NULL input', '--path', 'src/handler.py',
                 '--proof', 'pytest tests/test_parser.py::test_null')
        first = self.rec_id()
        self.cmd('add', '--kind', 'decision', '--title', 'Use repro test', '--links', first)
        self.cmd('checkpoint', '--summary', 'Parser inspected', '--next', 'Run updated tests',
                 '--verified-by', 'Local test')
        self.cmd('handoff', '--budget', '600')
        out = (self.root / '.ctx/HANDOFF.md').read_text()
        self.assertIn('Parser inspected', out)
        self.assertIn('Parser trace', out)
        self.assertIn('src/handler.py', out)
        self.assertIn('R-', self.cmd('graph').stdout)
        self.cmd('check')

    def test_existing_agents_remains_untouched(self):
        (self.root / 'AGENTS.md').write_text('DO NOT OVERWRITE ME')
        self.init()
        self.assertEqual((self.root / 'AGENTS.md').read_text(), 'DO NOT OVERWRITE ME')
        self.assertTrue((self.root / '.ctx/SCOPE.md').is_file())

    def test_unsafe_paths_rejected(self):
        outside = Path(self.temp.name) / 'outside'
        outside.mkdir()
        (outside / 'flag').write_text('hello')
        (self.root / 'escape').symlink_to(outside, target_is_directory=True)
        self.init()
        self.assertNotEqual(self.cmd('task', 'add', 'bad', '--scope', '../outside', ok=False).returncode, 0)
        self.assertNotEqual(self.cmd('add', '--kind', 'note', '--title', 'bad', '--path', 'escape/flag', ok=False).returncode, 0)
        self.cmd('scan')
        inventory = json.loads((self.root / '.ctx/state.json').read_text())['inventory']
        self.assertNotIn('escape/flag', inventory)

    def test_verified_requires_proof_and_unknown_edge_rejected(self):
        self.init()
        self.assertNotEqual(self.cmd('add', '--kind', 'finding', '--status', 'verified', '--title', 'A', ok=False).returncode, 0)
        self.assertNotEqual(self.cmd('add', '--kind', 'decision', '--title', 'A', '--links', 'R-fake', ok=False).returncode, 0)

    def test_revision_hides_superseded_claim(self):
        self.init()
        self.cmd('task', 'add', 'Test')
        self.cmd('add', '--kind', 'hypothesis', '--title', 'Old hypothesis')
        first = self.rec_id()
        self.cmd('add', '--kind', 'finding', '--title', 'Corrected result', '--status', 'verified',
                 '--proof', 'Reproduced manually on local copy', '--supersedes', first, '--links', first)
        text = self.cmd('context').stdout
        self.assertIn('Corrected result', text)
        self.assertNotIn('Old hypothesis', text)
        self.cmd('check')

    def test_scoped_scan_preserves_unrelated_inventory(self):
        for d in ('a', 'b'):
            (self.root / d).mkdir()
            (self.root / d / 'file.txt').write_text('x')
        self.init()
        self.cmd('scan')
        self.cmd('task', 'add', 'Only A', '--scope', 'a')
        self.cmd('scan', '--task', self.tid())
        inventory = json.loads((self.root / '.ctx/state.json').read_text())['inventory']
        self.assertIn('a/file.txt', inventory)
        self.assertIn('b/file.txt', inventory)

    def test_secret_pattern_and_budget(self):
        self.init()
        self.assertNotEqual(self.cmd('add', '--kind', 'note', '--title', 'ghp_'+'a'*32, ok=False).returncode, 0)
        for i in range(8):
            self.cmd('add', '--kind', 'note', '--title', f'Step {i}', '--body', 'short content')
        out = self.cmd('context', '--budget', '130').stdout
        self.assertLessEqual(len(out), 130 * 4 + 1)

    def test_task_close(self):
        self.init()
        self.cmd('task', 'add', 'One')
        t = self.tid()
        self.cmd('task', 'close', t)
        self.assertIsNone(self.tid())

if __name__ == '__main__':
    unittest.main()

class ContextForgeAntiLoopTests(ContextForgeMixin, unittest.TestCase):
    def test_pinned_mission_and_rethink(self):
        self.init()
        self.cmd('task', 'add', 'Analyze local puzzle')
        card = self.root / '.ctx' / 'MISSION.md'
        self.assertIn('REPLACE_ME', card.read_text())
        card.write_text('# Mission\nObjective: emit precisely one blue token.\nRule: no live automated calls.\n')
        output = self.cmd('context', '--budget', '1200').stdout
        self.assertIn('emit precisely one blue token', output)
        self.assertIn('no live automated calls', self.cmd('rethink', '--budget', '1200').stdout)
        self.assertIn('RETHINK CHECKLIST', self.cmd('rethink', '--budget', '1200').stdout)

    def test_repeated_route_requires_new_evidence(self):
        self.init()
        self.cmd('task', 'add', 'Local parser analysis')
        self.cmd('lane', 'start', 'First hypothesis', '--route', 'cache-path',
                 '--hypothesis', 'Cache returns stale data on a local test fixture',
                 '--falsifier', 'Fresh data persists with cache disabled', '--max-attempts', '2')
        p = self.cmd('lane', 'gate', '--signature', 'Turn off cache and run fixture one time',
                     '--predict', 'Observed fixture changes cache result')
        attempt_id = p.stdout.split('GATE PASS ')[1].split(':')[0]
        self.cmd('lane', 'result', '--id', attempt_id, '--outcome', 'no-change',
                 '--observation', 'No result changed in controlled fixture')
        self.cmd('lane', 'pivot', '--reason', 'Test was nondiscriminating')
        failed = self.cmd('lane', 'start', 'Rename same hypothesis', '--route', 'cache-path',
                          '--hypothesis', 'Try the cache again', '--falsifier', 'Any cached response changes', ok=False)
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn('STOP: route already explored', failed.stderr)
        self.cmd('lane', 'start', 'Different hypothesis', '--route', 'serialization',
                 '--hypothesis', 'JSON serializer normalizes fixture values',
                 '--falsifier', 'Pre-serialization and post-serialization values match')
        failed = self.cmd('lane', 'gate', '--signature', 'Turn off cache and run fixture one time',
                          '--predict', 'Observed fixture changes cache result', ok=False)
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn('repeated test fingerprint', failed.stderr)

    def test_progress_rejects_old_evidence(self):
        self.init()
        self.cmd('task', 'add', 'Controlled testcase')
        self.cmd('add', '--kind', 'evidence', '--status', 'verified', '--title', 'Old baseline',
                 '--proof', 'Fixture output saved to test log')
        rid = self.rec_id()
        self.cmd('lane', 'start', 'Hypothesis', '--route', 'signal',
                 '--hypothesis', 'New output differs from baseline', '--falsifier', 'Outputs equal')
        p = self.cmd('lane', 'gate', '--signature', 'Compare baseline to fresh fixture with normalizer',
                     '--predict', 'Two outputs have different lengths')
        attempt_id = p.stdout.split('GATE PASS ')[1].split(':')[0]
        result = self.cmd('lane', 'result', '--id', attempt_id, '--outcome', 'progress',
                          '--observation', 'Model thinks change occurred', '--evidence', rid, ok=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('AFTER this attempt', result.stderr)
        self.cmd('add', '--kind', 'evidence', '--status', 'verified', '--title', 'New fixture comparison',
                 '--body', 'Different bytes from baseline', '--proof', 'Unit test fixture stored locally')
        self.cmd('lane', 'result', '--id', attempt_id, '--outcome', 'progress',
                 '--observation', 'New fixture output differed as asserted', '--evidence', self.rec_id())

    def test_context_budget_strict_even_when_unfilled(self):
        self.init()
        self.cmd('task', 'add', 'Test')
        for b in (100, 130, 300):
            out = self.cmd('context', '--budget', str(b)).stdout
            self.assertLessEqual(len(out), b * 4 + 1)
        self.assertIn('WARNING: Context incomplete', self.cmd('context', '--budget', '100').stdout)

    def test_upgrade_preserves_state(self):
        self.init()
        (self.root / '.ctx' / 'MISSION.md').unlink()
        before = (self.root / '.ctx/state.json').read_bytes()
        self.cmd('upgrade')
        self.assertTrue((self.root / '.ctx/MISSION.md').exists())
        self.assertEqual(before, (self.root / '.ctx/state.json').read_bytes())
