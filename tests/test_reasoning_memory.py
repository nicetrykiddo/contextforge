"""Cross-project reasoning memory regression tests (offline; no target calls)."""
import json
import os
import pty
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CLI = ROOT / 'ctx.py'


class GlobalReasoningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = pathlib.Path(self.temp.name)
        self.env = dict(os.environ, XDG_CONFIG_HOME=str(self.base / 'config'))

    def run_cli(self, *args, project=None, expected=0):
        cmd = [sys.executable, str(CLI)]
        if project:
            cmd += ['--root', str(project)]
        if tuple(args[:2]) == ('reasoning', 'approve') and expected == 0:
            # Simulate the documented operator confirmation in a PTY. This
            # tests the interaction, NOT real-world human identity.
            master, slave = pty.openpty()
            try:
                process = subprocess.Popen(cmd + list(args), env=self.env,
                                           stdin=slave, text=True,
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE)
                os.close(slave)
                os.write(master, (args[2] + '\n').encode())
                stdout, stderr = process.communicate(timeout=15)
                result_code = process.returncode
            finally:
                os.close(master)
        else:
            result = subprocess.run(cmd + list(args), env=self.env,
                                    text=True, capture_output=True)
            stdout, stderr, result_code = result.stdout, result.stderr, result.returncode
        self.assertEqual(result_code, expected, stdout + stderr)
        return stdout + stderr

    def propose(self):
        out = self.run_cli('reasoning', 'propose', '--principle',
                           'Tool acceptance must not be mistaken for completed work',
                           '--when', 'a tool reports successful acceptance with no visible effect',
                           '--response', 'request independent proof of the downstream result',
                           '--tags', 'tools proof progress')
        return out.split('PROPOSED ')[1].split('.')[0]

    def test_explicit_review_and_project_isolation(self):
        a, b = self.base / 'A', self.base / 'B'
        for project in (a, b):
            self.run_cli('init', '--mode', 'bugbounty', project=project)
            self.run_cli('task', 'add', 'Investigate', '--goal',
                         'Verify whether a tool reports acceptance with no visible effect',
                         project=project)
        self.run_cli('checkpoint', '--summary', 'Specific finding exists only in project A',
                     '--next', 'Compare observed result', project=a)
        lesson = self.propose()
        self.assertNotIn('independent proof', self.run_cli('context', '--budget', '2000', project=b))
        self.run_cli('reasoning', 'approve', lesson)
        self.assertIn('independent proof', self.run_cli('context', '--budget', '2000', project=b))
        self.assertNotIn('Specific finding exists only in project A',
                         self.run_cli('context', '--budget', '2000', project=b))
        self.assertIn('Specific finding exists only in project A',
                      self.run_cli('context', '--budget', '2000', project=a))
        self.run_cli('reasoning', 'retire', lesson)
        self.assertNotIn('independent proof', self.run_cli('context', '--budget', '2000', project=b))

    def test_duplicates_and_sensitive_data_rejected(self):
        lesson = self.propose()
        same = self.run_cli('reasoning', 'propose', '--principle',
                            'Tool acceptance must not be mistaken for completed work',
                            '--when', 'a tool reports successful acceptance with no visible effect',
                            '--response', 'request independent proof of the downstream result',
                            expected=2)
        self.assertIn('Near-duplicate', same)
        sensitive = self.run_cli('reasoning', 'propose', '--principle',
                                 'The IP 10.129.84.227 made the server fail',
                                 '--when', 'a service returns an unexpected response',
                                 '--response', 'investigate observable evidence',
                                 expected=2)
        self.assertIn('project identifiers', sensitive)
        self.run_cli('reasoning', 'reject', lesson)
        self.assertIn('Only proposed', self.run_cli('reasoning', 'approve', lesson, expected=2))

    def test_relevance_budget_and_permissions(self):
        lesson = self.propose()
        stored = self.base / 'config' / 'contextforge' / 'reasoning.json'
        self.assertEqual(stored.stat().st_mode & 0o777, 0o600)
        self.assertEqual(json.loads(stored.read_text())['lessons'][0]['status'], 'proposed')
        self.run_cli('reasoning', 'approve', lesson)
        self.assertIn('No relevant', self.run_cli('reasoning', 'select', '--query', 'watering garden'))
        project = self.base / 'garden'
        self.run_cli('init', '--mode', 'general', project=project)
        self.run_cli('task', 'add', 'Garden', '--goal', 'Create a watering plan', project=project)
        self.assertNotIn('independent proof', self.run_cli('context', '--budget', '1500', project=project))
        self.assertNotIn('Optional global reasoning', self.run_cli('context', '--budget', '350', project=project))


if __name__ == '__main__':
    unittest.main()
