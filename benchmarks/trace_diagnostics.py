#!/usr/bin/env python3
"""Privacy-safe descriptive Codex JSONL analysis. NOT an agent efficacy score.

Supports saved Codex rollout JSONL and codex exec --json. Emits only aggregate
metrics; never emits prompts, commands, file paths, tool output, or thread IDs.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

CTX = re.compile(r'(?<![\w-])(?:contextforge|ctx\.py)(?![\w-])', re.I)
TOKEN_KEYS = ('input_tokens', 'cached_input_tokens', 'output_tokens', 'reasoning_output_tokens')


def analyze(path: Path) -> dict:
    count = Counter()
    hashes = Counter()
    stored_usage = Counter()
    exec_usage = Counter()
    models, efforts, schemas = set(), set(), set()
    waiting_for_recovery = False
    since_compaction = 0
    with path.open(encoding='utf-8') as source:
        for line in source:
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except (ValueError, UnicodeError):
                count['malformed_lines'] += 1
                continue
            if not isinstance(event, dict):
                count['malformed_lines'] += 1
                continue
            count['valid_events'] += 1
            kind = event.get('type')
            payload = event.get('payload')
            p = payload if isinstance(payload, dict) else {}
            if kind in ('response_item', 'token_usage_record', 'turn_context', 'compacted'):
                schemas.add('stored_rollout')
            if kind in ('thread.started', 'turn.completed', 'item.started', 'item.completed'):
                schemas.add('codex_exec_json')
            if kind == 'turn_context':
                if isinstance(p.get('model'), str):
                    models.add(p['model'])
                if isinstance(p.get('effort'), str):
                    efforts.add(p['effort'])
            if kind in ('compacted', 'thread.compacted', 'turn.compacted'):
                count['explicit_compactions'] += 1
                waiting_for_recovery = True
                since_compaction = 0
            if kind in ('token_usage_record', 'turn.completed'):
                usage = p.get('usage') if kind == 'token_usage_record' else event.get('usage')
                if isinstance(usage, dict):
                    dest = stored_usage if kind == 'token_usage_record' else exec_usage
                    for key in TOKEN_KEYS:
                        if isinstance(usage.get(key), (int, float)):
                            dest[key] += usage[key]
            raw, tool = None, None
            if kind == 'response_item' and p.get('type') == 'custom_tool_call':
                tool = p.get('name') or 'unknown'
                raw = p.get('input') or ''
            elif kind == 'item.started' and isinstance(event.get('item'), dict):
                item = event['item']
                if item.get('type') in ('command_execution', 'mcp_tool_call', 'web_search'):
                    tool = item['type']
                    raw = item.get('command') or json.dumps(item, sort_keys=True)
            if tool is not None:
                count['tool_calls'] += 1
                raw = raw if isinstance(raw, str) else json.dumps(raw, sort_keys=True)
                if raw.strip():
                    fingerprint = hashlib.sha256((tool + ':' + raw.strip()).encode()).hexdigest()
                    hashes[fingerprint] += 1
                    if CTX.search(raw):
                        count['tool_calls_mentioning_contextforge'] += 1
                if waiting_for_recovery:
                    since_compaction += 1
                    if since_compaction <= 10 and CTX.search(raw):
                        count['compactions_with_contextforge_in_next_10_calls'] += 1
                        waiting_for_recovery = False
    if stored_usage and exec_usage:
        usage_label, usage = 'mixed_ambiguous_not_summed', None
    elif stored_usage:
        usage_label, usage = 'stored_rollout_response_usage', {k: int(stored_usage[k]) for k in TOKEN_KEYS}
    elif exec_usage:
        usage_label, usage = 'codex_exec_turn_usage', {k: int(exec_usage[k]) for k in TOKEN_KEYS}
    else:
        usage_label, usage = 'unavailable', None
    return {
        'kind': 'DESCRIPTIVE_TRACE_DIAGNOSTIC_NOT_MODEL_BENCHMARK',
        'schema_version': 1,
        'observed_schemas': sorted(schemas),
        'valid_events': count['valid_events'],
        'malformed_lines': count['malformed_lines'],
        'tool_calls': count['tool_calls'],
        'tool_calls_mentioning_contextforge': count['tool_calls_mentioning_contextforge'],
        'exact_input_repeat_calls': sum(n - 1 for n in hashes.values() if n > 1),
        'unique_tool_input_fingerprints': len(hashes),
        'explicit_compactions': count['explicit_compactions'],
        'compactions_with_contextforge_in_next_10_calls': count['compactions_with_contextforge_in_next_10_calls'],
        'model_names_observed': sorted(models),
        'reasoning_efforts_observed': sorted(efforts),
        'reported_usage_schema': usage_label,
        'reported_usage': usage,
        'interpretation_limits': [
            'Exact repeated tool inputs do not imply wasted work.',
            'Mentioning ContextForge in a call is not proof that durable state is correct.',
            'Reported token counts include cached inputs; they are not Plus quota consumption.',
            'No recorded compaction event does not prove that compaction did not happen.',
            'No task success, vulnerability validity, or skill benefit is established.'
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rollout', type=Path, help='Local private JSONL input')
    parser.add_argument('--output', type=Path, help='Aggregate-only JSON output')
    args = parser.parse_args()
    report = json.dumps(analyze(args.rollout), indent=2) + '\n'
    if args.output:
        args.output.write_text(report, encoding='utf-8')
    else:
        sys.stdout.write(report)


if __name__ == '__main__':
    main()
