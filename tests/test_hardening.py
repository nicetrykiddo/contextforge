"""Adversarial regressions: every exploit here must FAIL safely after hardening.

Uses only local synthetic fixtures. Never touches real target code or accounts.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

CLI = Path(__file__).resolve().parents[1] / 'ctx.py'


class HardeningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='cf-hardening-')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.project = self.base / 'project'
        self.env = dict(os.environ, XDG_CONFIG_HOME=str(self.base / 'config'))
        self.cli('init', '--mode', 'general')

    def cli(self, *args, ok=True):
        p = subprocess.run([sys.executable, str(CLI), '--root', str(self.project), *args],
                           capture_output=True, text=True, env=self.env, timeout=25)
        if ok:
            self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
        return p

    def test_handoff_symlink_does_not_modify_external_file(self):
        outside = self.base / 'private-canary'
        outside.write_text('PRESERVE-ME')
        (self.project / '.ctx/HANDOFF.md').symlink_to(outside)
        p = self.cli('handoff', ok=False)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('symlinked', p.stderr)
        self.assertEqual(outside.read_text(), 'PRESERVE-ME')

    def test_snapshot_symlinked_handoff_does_not_modify_external_file(self):
        outside = self.base / 'private-canary'
        outside.write_text('PRESERVE-ME')
        (self.project / '.ctx/HANDOFF.md').symlink_to(outside)
        p = self.cli('snapshot', ok=False)
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(outside.read_text(), 'PRESERVE-ME')

    def test_snapshot_directory_symlink_does_not_write_external_archive(self):
        external = self.base / 'outside'
        external.mkdir()
        (self.project / '.ctx/compactions').symlink_to(external, target_is_directory=True)
        p = self.cli('snapshot', ok=False)
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(list(external.glob('*.zip')), [])

    def test_mission_symlink_does_not_expose_external_content(self):
        private = self.base / 'outside-canary'
        private.write_text('SECRET-TEST-911')
        mission = self.project / '.ctx/MISSION.md'
        mission.unlink()
        mission.symlink_to(private)
        p = self.cli('context', ok=False)
        self.assertNotEqual(p.returncode, 0)
        self.assertNotIn('SECRET-TEST-911', p.stdout + p.stderr)

    def test_symlinked_state_and_records_refused(self):
        state_path = self.project / '.ctx/state.json'
        state_contents = state_path.read_bytes()
        state_path.unlink()
        external = self.base / 'external.json'
        external.write_bytes(state_contents)
        state_path.symlink_to(external)
        p = self.cli('status', ok=False)
        self.assertNotEqual(p.returncode, 0)
        state_path.unlink()
        state_path.write_bytes(state_contents)
        rec = self.project / '.ctx/records.jsonl'
        rec.unlink()
        payload = self.base / 'external.jsonl'
        payload.write_text('{"id":"R-evil"}\n')
        rec.symlink_to(payload)
        p = self.cli('context', ok=False)
        self.assertNotEqual(p.returncode, 0)

    def test_hardlinked_record_file_cannot_modify_unrelated_file(self):
        records = self.project / '.ctx/records.jsonl'
        records.unlink()
        outside = self.base / 'external-hardlink'
        outside.write_text('EXTERNAL-CANARY')
        os.link(outside, records)
        p = self.cli('add', '--kind', 'note', '--title', 'should not append', ok=False)
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(outside.read_text(), 'EXTERNAL-CANARY')

    def test_nonregular_records_file_is_refused(self):
        if not hasattr(os, 'mkfifo'):
            self.skipTest('requires POSIX FIFOs')
        records = self.project / '.ctx/records.jsonl'
        records.unlink()
        os.mkfifo(records)
        p = self.cli('context', ok=False)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('non-regular', p.stderr)

    def test_focused_task_search_does_not_cross_tasks(self):
        a = self.cli('task', 'add', 'A', '--goal', 'A').stdout.split()[0]
        self.cli('add', '--kind', 'note', '--title', 'TASK-A-CANARY-111')
        b = self.cli('task', 'add', 'B', '--goal', 'B').stdout.split()[0]
        self.assertNotEqual(a, b)
        self.assertNotIn('TASK-A-CANARY-111', self.cli('search', 'TASK-A-CANARY').stdout)
        self.assertIn('TASK-A-CANARY-111', self.cli('search', 'TASK-A-CANARY', '--all-tasks').stdout)
        self.assertIn('TASK-A-CANARY-111', self.cli('search', 'TASK-A-CANARY', '--task', a).stdout)

    def test_task_add_focuses_new_task_to_avoid_record_misfile(self):
        a = self.cli('task', 'add', 'A', '--goal', 'A').stdout.split()[0]
        b = self.cli('task', 'add', 'B', '--goal', 'B').stdout.split()[0]
        self.cli('add', '--kind', 'note', '--title', 'B-NOTE')
        record = json.loads((self.project / '.ctx/records.jsonl').read_text().splitlines()[-1])
        self.assertEqual(record['task'], b)
        self.assertNotEqual(record['task'], a)

    def test_scan_preserves_existing_other_task_inventory(self):
        for name in ('a', 'b'):
            folder = self.project / name
            folder.mkdir()
            (folder / (name+'-canary.txt')).write_text(name)
        a = self.cli('task', 'add', 'A', '--scope', 'a').stdout.split()[0]
        self.cli('scan')
        b = self.cli('task', 'add', 'B', '--scope', 'b').stdout.split()[0]
        self.cli('scan')
        state = json.loads((self.project / '.ctx/state.json').read_text())
        self.assertIn('a/a-canary.txt', state['inventory'])
        self.assertIn('b/b-canary.txt', state['inventory'])

    def test_unrelated_task_record_does_not_stale_checkpoint(self):
        a = self.cli('task', 'add', 'A').stdout.split()[0]
        self.cli('add', '--kind', 'evidence', '--title', 'A evidence')
        self.cli('checkpoint', '--summary', 'A saved', '--next', 'A next')
        self.cli('task', 'add', 'B')
        self.cli('add', '--kind', 'note', '--title', 'B unrelated')
        self.cli('task', 'focus', a)
        output = self.cli('snapshot').stdout
        self.assertNotIn('checkpoint missing/stale', output)
        self.cli('add', '--kind', 'evidence', '--title', 'A new evidence')
        output = self.cli('snapshot').stdout
        self.assertIn('checkpoint missing/stale', output)

    def test_irrelevant_query_does_not_emit_false_relevance(self):
        self.cli('task', 'add', 'A')
        self.cli('add', '--kind', 'note', '--title', 'IRRELEVANT-TEST-123',
                 '--body', 'Unrelated blueberry signal')
        output = self.cli('context', '--budget', '1500',
                          '--query', 'xxxxxxxxunknownkeywordxyz').stdout
        self.assertNotIn('IRRELEVANT-TEST-123', output)

    def test_deleted_file_disappears_only_from_own_task_scan(self):
        for name in ('a', 'b'):
            folder = self.project / name
            folder.mkdir()
            (folder / 'canary.txt').write_text(name)
        a = self.cli('task', 'add', 'A', '--scope', 'a').stdout.split()[0]
        self.cli('scan')
        self.cli('task', 'add', 'B', '--scope', 'b')
        self.cli('scan')
        (self.project / 'b/canary.txt').unlink()
        self.cli('scan')
        state = json.loads((self.project / '.ctx/state.json').read_text())
        self.assertIn('a/canary.txt', state['inventory'])
        self.assertNotIn('b/canary.txt', state['inventory'])
        self.cli('task', 'focus', a)
        self.assertIn('a/canary.txt', self.cli('search', 'canary').stdout)

    def test_tampered_scope_cannot_scan_parent_folder(self):
        external = self.base / 'external'
        external.mkdir()
        (external / 'secret-canary.txt').write_text('PRESERVE')
        state_path = self.project / '.ctx/state.json'
        state = json.loads(state_path.read_text())
        state['scopes'] = ['../external']
        state_path.write_text(json.dumps(state))
        p = self.cli('scan', ok=False)
        self.assertNotEqual(p.returncode, 0)
        self.assertNotIn('secret-canary.txt', p.stdout)

    def test_symlinked_tasks_directory_is_not_scanned_in_snapshot(self):
        outside = self.base / 'external'
        outside.mkdir()
        (outside / 'private.md').write_text('KEEP-PRIVATE')
        (self.project / '.ctx/tasks').symlink_to(outside, target_is_directory=True)
        p = self.cli('snapshot', ok=False)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('symlinked', p.stderr)

    def test_new_agents_file_uses_current_task_source(self):
        text = (self.project / 'AGENTS.md').read_text()
        self.assertIn('ACTIVE task', text)
        self.assertNotIn('Recover from `.ctx/HANDOFF.md` after compaction', text)


if __name__ == '__main__':
    unittest.main()
