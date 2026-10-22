"""No-model tests: Codex trace metrics without leaking user data."""
import json
from pathlib import Path
import tempfile
import unittest

from benchmarks.trace_diagnostics import analyze


class TraceDiagnosticTests(unittest.TestCase):
    def make_log(self, rows, corrupted=False):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / 'private-rollout.jsonl'
        path.write_text('\n'.join(json.dumps(row) for row in rows) +
                        ('\n{invalid json' if corrupted else '') + '\n', encoding='utf-8')
        return path

    def test_saved_rollout_counts_no_raw_sensitive_content(self):
        secret = 'secret-NEVER-PUBLISH-911'
        call = {'type': 'response_item', 'payload': {
            'type': 'custom_tool_call', 'name': 'exec',
            'input': '{"cmd":"echo ' + secret + '"}'}}
        rows = [
            {'type': 'turn_context', 'payload': {'model': 'test-model', 'effort': 'medium'}},
            call,
            {'type': 'compacted', 'payload': {'replacement_history': secret}},
            {'type': 'response_item', 'payload': {'type': 'custom_tool_call',
                'name': 'exec', 'input': '{"cmd":"contextforge context --budget 800"}'}},
            call,
            {'type': 'response_item', 'payload': {
                'type': 'custom_tool_call_output', 'output': secret}},
            {'type': 'token_usage_record', 'payload': {
                'usage': {'input_tokens': 90, 'cached_input_tokens': 70,
                          'output_tokens': 4}}},
        ]
        report = analyze(self.make_log(rows))
        self.assertEqual(report['tool_calls'], 3)
        self.assertEqual(report['tool_calls_mentioning_contextforge'], 1)
        self.assertEqual(report['explicit_compactions'], 1)
        self.assertEqual(report['compactions_with_contextforge_in_next_10_calls'], 1)
        self.assertEqual(report['exact_input_repeat_calls'], 1)
        self.assertEqual(report['reported_usage']['input_tokens'], 90)
        self.assertNotIn(secret, json.dumps(report))
        self.assertNotIn('echo', json.dumps(report))

    def test_codex_exec_schema_no_double_count_and_no_thread_id_leak(self):
        rows = [
            {'type': 'thread.started', 'thread_id': 'private-session-id-999'},
            {'type': 'item.started', 'item': {'type': 'command_execution', 'command': 'ls -la'}},
            {'type': 'item.completed', 'item': {'type': 'command_execution', 'command': 'ls -la'}},
            {'type': 'turn.completed', 'usage': {'input_tokens': 120,
                'cached_input_tokens': 50, 'output_tokens': 35, 'reasoning_output_tokens': 4}},
        ]
        report = analyze(self.make_log(rows))
        self.assertEqual(report['tool_calls'], 1)
        self.assertEqual(report['reported_usage_schema'], 'codex_exec_turn_usage')
        self.assertEqual(report['reported_usage']['output_tokens'], 35)
        self.assertEqual(report['explicit_compactions'], 0)
        self.assertNotIn('private-session-id-999', json.dumps(report))

    def test_mixed_usage_is_not_combined_and_bad_line_counted(self):
        rows = [
            {'type': 'token_usage_record', 'payload': {'usage': {'input_tokens': 10}}},
            {'type': 'turn.completed', 'usage': {'input_tokens': 10}},
        ]
        report = analyze(self.make_log(rows, corrupted=True))
        self.assertEqual(report['reported_usage_schema'], 'mixed_ambiguous_not_summed')
        self.assertIsNone(report['reported_usage'])
        self.assertEqual(report['malformed_lines'], 1)


if __name__ == '__main__':
    unittest.main()
