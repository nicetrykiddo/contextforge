import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('ctx', Path(__file__).resolve().parents[1] / 'ctx.py')
ctx = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ctx)

class CompactionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'project'
        self.root.mkdir()
        with redirect_stdout(io.StringIO()):
            ctx.init(type('A', (), {'root': str(self.root), 'mode': 'ctf', 'name': None, 'scope': '.'})())
            ctx.task_add(type('A', (), {'root': str(self.root), 'title': 'test', 'scope': None, 'goal': 'evaluate evidence'})())
        (self.root / '.ctx/MISSION.md').write_text('# Mission\nExactly one result; no external requests.\n')

    def pin(self, *, verified=True):
        a = dict(root=str(self.root), title='Important edge case',
                 body='Fixture 2 differs only when cache is empty.',
                 status='verified' if verified else 'unverified',
                 proof='test-output.log:4' if verified else None,
                 path=None, links=None, task=None, supersedes=None)
        with redirect_stdout(io.StringIO()):
            ctx.pin(type('A', (), a)())

    def test_pin_survives_bounded_handoff_and_compaction_snapshot(self):
        self.pin()
        state = ctx.load(self.root)
        handoff = ctx.context_text(self.root, state, state['active_task'], '', 1500)
        self.assertIn('Fixture 2 differs', handoff)
        self.assertIn('verified', handoff)
        self.assertIn('proof=test-output.log:4', handoff)
        snap, stale = ctx.compaction_snapshot(self.root)
        self.assertTrue(stale)  # no checkpoint created yet
        self.assertEqual(snap.stat().st_mode & 0o777, 0o600)
        with zipfile.ZipFile(snap) as z:
            self.assertIn('records.jsonl', z.namelist())
            self.assertIn('MISSION.md', z.namelist())
            self.assertIn('Fixture 2 differs', z.read('records.jsonl').decode())
            self.assertTrue(json.loads(z.read('manifest.json'))['checkpoint_stale'])

    def test_hook_does_not_capture_transcript_and_handles_nonproject(self):
        self.pin()
        outside = Path(self.tmp.name) / 'outside'
        outside.mkdir()
        payload = {'hook_event_name': 'PreCompact', 'cwd': str(self.root),
                   'session_id': 'test-session', 'trigger':'auto',
                   'transcript_path': '/some/private/transcript.jsonl'}
        capture = io.StringIO()
        with patch('sys.stdin', io.StringIO(json.dumps(payload))), redirect_stdout(capture):
            ctx.hook(type('A', (), {})())
        self.assertIn('saved', json.loads(capture.getvalue())['systemMessage'])
        snap = sorted((self.root/'.ctx/compactions').glob('*.zip'))[-1]
        with zipfile.ZipFile(snap) as z:
            self.assertNotIn('transcript.jsonl', z.namelist())
        payload['cwd'] = str(outside)
        with patch('sys.stdin', io.StringIO(json.dumps(payload))), redirect_stdout(capture := io.StringIO()):
            ctx.hook(type('A', (), {})())
        self.assertEqual(json.loads(capture.getvalue()), {})

    def test_hook_installer_preserves_other_events_and_idempotent(self):
        home = Path(self.tmp.name) / 'home'
        (home/'.local/bin').mkdir(parents=True)
        (home/'.local/bin/contextforge').write_text('# tool stub')
        (home/'.codex').mkdir()
        old = {'hooks': {'Stop': [{'hooks': [{'type': 'command', 'command': 'echo unchanged'}]}]}}
        (home/'.codex/hooks.json').write_text(json.dumps(old))
        with patch.object(ctx.Path, 'home', return_value=home), redirect_stdout(io.StringIO()):
            ctx.hooks_install(type('A', (), {})())
            ctx.hooks_install(type('A', (), {})())
        data = json.loads((home/'.codex/hooks.json').read_text())
        self.assertEqual(data['hooks']['Stop'], old['hooks']['Stop'])
        self.assertEqual(len(data['hooks']['PreCompact']), 1)
        self.assertEqual(len(data['hooks']['PostCompact']), 1)
        self.assertEqual(len(data['hooks']['SessionStart']), 1)
        self.assertEqual(len(list((home/'.codex').glob('hooks.json.backup-*'))), 1)

    def test_bounded_context_warns_when_pins_cannot_fit(self):
        self.pin()
        state = ctx.load(self.root)
        text = ctx.context_text(self.root, state, state['active_task'], '', 100)
        self.assertLessEqual(len(text), 400)
        self.assertIn('WARNING: Context incomplete', text)

if __name__ == '__main__':
    unittest.main()
