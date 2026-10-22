"""Long realistic user brief capture: no manual mission rewrite or silent truncation."""
import hashlib
import json
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile

CLI = Path(__file__).resolve().parents[1] / 'ctx.py'


class LongBriefTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'project'
        self.env = {**os.environ, 'XDG_CONFIG_HOME': str(Path(self.tmp.name)/'config')}
        self.run_cmd('init', '--mode', 'general')

    def run_cmd(self, *args, data=None, ok=True):
        p = subprocess.run([sys.executable, str(CLI), '--root', str(self.root), *args],
                           input=data, capture_output=True, text=True, env=self.env, timeout=35)
        if ok:
            self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
        return p

    def test_big_user_prompt_is_preserved_exactly_and_context_is_short(self):
        tail = 'IMPORTANT REQUIREMENT AT VERY END: BUILD A COMPLETE WORKING PRODUCT'
        brief = 'User needs a broad, messy project with lots of details.\n' * 2000 + '\n' + tail
        self.run_cmd('brief', '--stdin', data=brief)
        st = json.loads((self.root / '.ctx/state.json').read_text())
        meta = st['brief_sources']['__project__']
        stored = self.root / meta['path']
        self.assertEqual(stored.read_text(), brief)
        self.assertEqual(meta['sha256'], hashlib.sha256(brief.encode()).hexdigest())
        self.assertIn('Exact original brief:', self.run_cmd('context', '--budget', '800').stdout)
        self.assertIn(meta['path'], self.run_cmd('context', '--budget', '100').stdout)
        self.assertNotIn(tail, self.run_cmd('context', '--budget', '800').stdout)
        self.run_cmd('snapshot')
        snap = sorted((self.root / '.ctx/compactions').glob('*.zip'))[-1]
        with zipfile.ZipFile(snap) as z:
            self.assertEqual(z.read(meta['path'][5:]).decode(), brief)

    def test_tasks_can_have_distinct_full_original_prompts(self):
        a = self.run_cmd('task', 'add', 'Project A').stdout.split()[0]
        first = 'A original requirement\n' * 2200 + 'A-tail'
        self.run_cmd('brief', '--stdin', '--task', a, data=first)
        b = self.run_cmd('task', 'add', 'Project B', '--focus').stdout.split()[0]
        second = 'B distinct full request\n' * 2100 + 'B-tail'
        path = Path(self.tmp.name)/'source.txt'
        path.write_text(second)
        self.run_cmd('brief', '--file', str(path), '--task', b)
        st = json.loads((self.root / '.ctx/state.json').read_text())
        self.assertNotEqual(st['brief_sources'][a]['path'], st['brief_sources'][b]['path'])
        self.assertEqual((self.root/st['brief_sources'][a]['path']).read_text(), first)
        self.assertEqual((self.root/st['brief_sources'][b]['path']).read_text(), second)
        self.run_cmd('task', 'focus', a)
        self.assertIn(st['brief_sources'][a]['path'], self.run_cmd('context', '--budget', '350').stdout)

    def test_original_applies_to_subtasks_and_changes_do_not_overwrite(self):
        original = 'Large request scope applies across multiple work streams\\n' * 200
        self.run_cmd('brief', '--stdin', data=original)
        a = self.run_cmd('task', 'add', 'A').stdout.split()[0]
        b = self.run_cmd('task', 'add', 'B', '--focus').stdout.split()[0]
        for tid in (a, b):
            text = self.run_cmd('context', '--task', tid, '--budget', '800').stdout
            self.assertIn('Verbatim original user brief: .ctx/briefs/', text)
        bad = self.run_cmd('brief', '--stdin', data='Different new source', ok=False)
        self.assertNotEqual(bad.returncode, 0)
        self.run_cmd('brief', '--stdin', '--amend', data='Additional user requirement: support offline operation.')
        st = json.loads((self.root/'.ctx/state.json').read_text())
        self.assertEqual((self.root / st['brief_sources']['__project__']['path']).read_text(), original)
        self.assertEqual(len(st['brief_amendments']['__project__']), 1)
        text = self.run_cmd('context', '--budget', '900').stdout
        self.assertIn('Additional user instructions', text)

    def test_detects_common_private_tokens_without_writing(self):
        bad = 'Do not store ' + 'sk-' + 'abcdefghijklmnopqrstuvwxyz123456789012345'
        p = self.run_cmd('brief', '--stdin', data=bad, ok=False)
        self.assertNotEqual(p.returncode, 0)
        self.assertFalse(list((self.root/'.ctx').glob('briefs/*.txt')))

    def test_empty_invalid_and_missing_brief_are_not_invented(self):
        self.assertIn('Original prompt was not locally captured',
                      self.run_cmd('context', '--budget', '900').stdout)
        p = self.run_cmd('brief', '--stdin', data=' ', ok=False)
        self.assertNotEqual(p.returncode, 0)
        p = self.run_cmd('brief', '--file', '/nonexistent/original.txt', ok=False)
        self.assertNotEqual(p.returncode, 0)


if __name__ == '__main__':
    unittest.main()
