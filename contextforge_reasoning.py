"""Optional global, reviewed, project-agnostic reasoning lessons for ContextForge.

No LLM API, network access, model setting changes, or automatic promotion.
"""
from __future__ import annotations

import datetime as dt
import contextlib
import difflib
import json
import os
import re
import tempfile
import uuid
from pathlib import Path

try:
    import fcntl
except ImportError:
    fcntl = None
    import msvcrt

SCHEMA = 1
MAX_APPROVED = 24
MAX_PROPOSED = 32
MAX_RENDERED = 3
PRIVATE_PATTERN = re.compile(
    r'(?:https?://\S+|\b[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}\b|'
    r'\b(?:\d{1,3}\.){3}\d{1,3}\b|-----BEGIN [A-Z ]*PRIVATE KEY-----|'
    r'\b(?:gh[pousr]_[A-Za-z0-9]{15,}|sk-[A-Za-z0-9_-]{15,})\b|'
    r'(?<!\w)(?:/home/|/tmp/|/etc/|[A-Za-z]:\\))', re.I)
STOP = {'the', 'this', 'that', 'from', 'then', 'than', 'with', 'when', 'what',
        'which', 'where', 'there', 'into', 'before', 'after', 'their', 'they',
        'have', 'been', 'were', 'and', 'for', 'are', 'not', 'its', 'you', 'your'}


def home():
    base = os.environ.get('XDG_CONFIG_HOME')
    return (Path(base).expanduser() if base else Path.home() / '.config') / 'contextforge'


def path():
    return home() / 'reasoning.json'


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')


def fail(message):
    raise ValueError(message)


@contextlib.contextmanager
def store_lock():
    """Serialize global lesson mutations across Codex processes."""
    directory = home()
    if directory.is_symlink():
        fail('Reasoning directory must not be a symlink')
    directory.mkdir(parents=True, mode=0o700, exist_ok=True)
    os.chmod(directory, 0o700)
    lock_path = directory / '.reasoning.lock'
    if lock_path.is_symlink():
        fail('Reasoning lock must not be a symlink')
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        if fcntl:
            fcntl.flock(fd, fcntl.LOCK_EX)
        else:
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
        yield
    finally:
        if fcntl:
            fcntl.flock(fd, fcntl.LOCK_UN)
        else:
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        os.close(fd)


def read_store():
    fp = path()
    if fp.is_symlink():
        fail('Global reasoning store is a symlink; refusing access')
    if not fp.exists():
        return {'schema': SCHEMA, 'lessons': []}
    state = json.loads(fp.read_text(encoding='utf-8'))
    if not isinstance(state, dict) or state.get('schema') != SCHEMA or not isinstance(state.get('lessons'), list):
        fail('Invalid reasoning store schema')
    return state


def write_store(state):
    directory = home()
    if directory.is_symlink():
        fail('Global reasoning directory is a symlink')
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path().is_symlink():
        fail('Global reasoning store is a symlink')
    descriptor, tmp = tempfile.mkstemp(prefix='.reasoning-', dir=directory)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
            f.write('\n')
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, path())
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def tokens(value):
    return {w for w in re.findall(r'[a-z0-9]+', value.lower()) if len(w) >= 3 and w not in STOP}


def normalized(value):
    return ' '.join(re.findall(r'[a-z0-9]+', value.lower()))


def sanitize(value, field, minimum=8, maximum=240):
    value = ' '.join(value.split())
    if not minimum <= len(value) <= maximum:
        fail(f'{field} must be {minimum}-{maximum} characters')
    if PRIVATE_PATTERN.search(value):
        fail(f'{field} contains possible project identifiers or secrets; abstract it first')
    if '\x00' in value:
        fail('NUL is not allowed')
    return value


def find_similar(state, principle, when):
    incoming = normalized(principle) + ' | ' + normalized(when)
    for item in state['lessons']:
        if item['status'] in ('rejected', 'retired'):
            continue
        existing = normalized(item['principle']) + ' | ' + normalized(item['when'])
        if difflib.SequenceMatcher(None, incoming, existing).ratio() >= 0.81:
            return item
    return None


def get(state, lesson_id):
    for item in state['lessons']:
        if item['id'] == lesson_id:
            return item
    fail(f'Unknown lesson ID: {lesson_id}')


def propose(args):
    state = read_store()
    if sum(x['status'] == 'proposed' for x in state['lessons']) >= MAX_PROPOSED:
        fail('Pending lesson limit (32) reached; review or reject older proposals first')
    principle = sanitize(args.principle, 'principle')
    when = sanitize(args.when, 'when')
    response = sanitize(args.response, 'response')
    tags = sorted(tokens(args.tags or ''))[:10]
    conflict = find_similar(state, principle, when)
    if conflict:
        fail(f'Near-duplicate of {conflict["id"]} ({conflict["status"]}). Review or revise instead.')
    item = {'id': 'L-' + uuid.uuid4().hex[:10], 'status': 'proposed',
            'principle': principle, 'when': when, 'response': response, 'tags': tags,
            'created': utc(), 'reviewed': None}
    state['lessons'].append(item)
    write_store(state)
    print(f'PROPOSED {item["id"]}. Not globally active until explicitly approved.')


def review_digest(item):
    import hashlib
    fields = {key: item[key] for key in ('id', 'principle', 'when', 'response', 'tags')}
    return hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest()


def confirm_review(args):
    """Deliberate local operator step, never proof of human identity."""
    import sys
    if not sys.stdin.isatty():
        fail('Approving global lessons requires interactive review in a terminal')
    item = get(read_store(), args.id)
    if item['status'] != 'proposed':
        fail('Only proposed lessons can be approved')
    print(f'Principle: {item["principle"]}')
    print(f'When: {item["when"]}')
    print(f'Response: {item["response"]}')
    if input(f'Type {item["id"]} to activate this global lesson: ').strip() != item['id']:
        fail('Review confirmation did not match; lesson unchanged')
    args.review_digest = review_digest(item)


def review(args):
    state = read_store()
    item = get(state, args.id)
    if args.decision == 'approve':
        if item['status'] != 'proposed':
            fail('Only proposed lessons can be approved')
        if sum(x['status'] == 'approved' for x in state['lessons']) >= MAX_APPROVED:
            fail(f'Approved lesson limit ({MAX_APPROVED}) reached; retire or merge older lessons first')
        similar = find_similar({'lessons': [x for x in state['lessons'] if x['id'] != item['id'] and x['status'] == 'approved']}, item['principle'], item['when'])
        if similar:
            fail(f'Near-duplicate of approved {similar["id"]}; retire/merge rather than approve both')
        # CLI confirmation happens BEFORE taking the global lock, and is
        # bound to these exact lesson bytes to avoid a review/mutation race.
        if getattr(args, 'review_digest', None) != review_digest(item):
            fail('Approval needs interactive review of the current lesson text')
    elif args.decision == 'reject' and item['status'] != 'proposed':
        fail('Only proposed lessons may be rejected')
    elif args.decision == 'retire' and item['status'] != 'approved':
        fail('Only approved lessons may be retired')
    item['status'] = {'approve': 'approved', 'reject': 'rejected', 'retire': 'retired'}[args.decision]
    item['reviewed'] = utc()
    write_store(state)
    print(f'{item["status"].upper()} {item["id"]}')


def list_lessons(args):
    state = read_store()
    matching = [l for l in state['lessons'] if args.status == 'all' or l['status'] == args.status]
    for l in matching:
        print(f'{l["id"]} [{l["status"]}] {l["principle"]}')
    print(f'{len(matching)} lesson(s); store={path()}')


# Small conceptual vocabulary rather than pretending literal keywords capture meaning.
# Curated, reviewable, deterministic; NOT embedding-based semantic search.
CONCEPTS = {
    'completion_vs_acceptance': {'accept', 'accepted', 'acceptance', '202', 'queued',
        'queue', 'success', 'successful', 'received', 'finish', 'finished',
        'completion', 'complete', 'completed', 'execute', 'executed', 'processed',
        'effect', 'effects', 'downstream', 'delivered', 'confirmed', 'confirm'},
    'hypothesis_vs_fact': {'assume', 'assumed', 'assumption', 'guess', 'guessed',
        'hypothesis', 'premise', 'inferred', 'inference', 'confidence',
        'confident', 'speculative', 'evidence', 'proof', 'observed', 'uncertain'},
    'repetition_without_progress': {'loop', 'looping', 'repeated', 'repeat',
        'retry', 'retries', 'rerun', 'again', 'stuck', 'stalled',
        'unproductive', 'progress', 'hours', 'iteration', 'iterations'},
    'generalization_scope': {'scope', 'generalize', 'generalized', 'sample',
        'tested', 'unseen', 'negative', 'absence', 'impossible', 'surface'},
    'context_recovery': {'memory', 'context', 'compaction', 'forgot',
        'forget', 'recovery', 'resume', 'handoff', 'checkpoint', 'lost'},
}


def concept_keys(value):
    words = set(re.findall(r'[a-z0-9]+', value.lower()))
    return {key for key, terms in CONCEPTS.items() if words & terms}


def relevance(lesson, query):
    q = tokens(query)
    if not q:
        return 0
    trigger = tokens(lesson['when'] + ' ' + ' '.join(lesson['tags']))
    principle = tokens(lesson['principle'])
    overlap = len(q & trigger)
    concepts = concept_keys(query) & concept_keys(lesson['when'] + ' ' + lesson['principle'])
    return overlap * 4 + len(q & principle) + (4 * len(concepts))


def selected(query, *, max_items=MAX_RENDERED, budget=240):
    """Read-only, strict relevance filter; no global data written on lookup."""
    if budget < 80 or not query.strip():
        return []
    items = [l for l in read_store()['lessons'] if l['status'] == 'approved']
    scored = [(relevance(l, query), l) for l in items]
    scored = [(score, l) for score, l in scored if score >= 4]
    scored.sort(key=lambda pair: (-pair[0], pair[1]['id']))
    result, used = [], 0
    for _score, l in scored[:max_items]:
        line = f'- [{l["id"]}] If {l["when"]}, consider: {l["response"]} (principle: {l["principle"]})'
        need = (len(line) + 3) // 4
        if used + need > budget:
            continue
        used += need
        result.append(line)
    return result


def show_selected(args):
    lines = selected(args.query, max_items=args.limit, budget=args.budget)
    if lines:
        print('## Optional, human-reviewed reasoning reminders (not agent policies)')
        print('\n'.join(lines))
    else:
        print('No relevant approved lessons. No generic reminders injected.')


def register(sub):
    """Register optional global reasoning-memory CLI under `contextforge reasoning`."""
    x = sub.add_parser('reasoning', help='Human-reviewed global reasoning memory, separate from project data')
    actions = x.add_subparsers(dest='reasoning_action', required=True)
    p = actions.add_parser('propose', help='Draft a GENERAL reasoning lesson (not activated)')
    p.add_argument('--principle', required=True)
    p.add_argument('--when', required=True, help='General trigger that can apply across projects')
    p.add_argument('--response', required=True, help='What mental check to consider')
    p.add_argument('--tags', default='', help='Small comma-separated conceptual tags')
    p.set_defaults(func=propose)
    for decision in ('approve', 'reject', 'retire'):
        p = actions.add_parser(decision, help=f'Explicitly {decision} a reviewed lesson')
        p.add_argument('id'); p.set_defaults(func=review, decision=decision)
    p = actions.add_parser('list')
    p.add_argument('--status', default='all', choices=['all', 'proposed', 'approved', 'rejected', 'retired'])
    p.set_defaults(func=list_lessons)
    p = actions.add_parser('select', help='Read only lessons that match current conceptual trigger')
    p.add_argument('--query', required=True)
    p.add_argument('--limit', default=3, type=int)
    p.add_argument('--budget', default=240, type=int)
    p.set_defaults(func=show_selected)
