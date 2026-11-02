import json, sys, collections, glob, os, re

folder = sys.argv[1]
mode = sys.argv[2]

def iter_msgs(path):
    for line in open(path):
        try:
            o = json.loads(line)
        except Exception:
            continue
        yield o

if mode == 'hook':
    # commands that the PreToolUse hook blocked
    for path in sorted(glob.glob(os.path.join(folder, 'agent-*.jsonl'))):
        by_id = {}
        for o in iter_msgs(path):
            msg = o.get('message') or {}
            content = msg.get('content')
            if o.get('type') == 'assistant' and isinstance(content, list):
                for c in content:
                    if c.get('type') == 'tool_use':
                        by_id[c['id']] = c.get('input')
            if o.get('type') == 'user' and isinstance(content, list):
                for c in content:
                    if c.get('type') == 'tool_result':
                        body = c.get('content')
                        text = ''.join(x.get('text', '') for x in body if isinstance(x, dict)) if isinstance(body, list) else str(body or '')
                        if 'PreToolUse:Bash hook error' in text or 'auto mode classifier' in text or 'Blocked: sleep' in text:
                            inp = by_id.get(c.get('tool_use_id')) or {}
                            print(os.path.basename(path)[6:14], '|', text[:70].replace('\n', ' '), '|', (inp.get('command') or '')[:260].replace('\n', ' ⏎ '))
elif mode == 'readfirst':
    counts = collections.Counter()
    prev_cat = collections.Counter()
    for path in sorted(glob.glob(os.path.join(folder, 'agent-*.jsonl'))):
        aid = os.path.basename(path)[6:14]
        for o in iter_msgs(path):
            content = (o.get('message') or {}).get('content')
            if o.get('type') == 'user' and isinstance(content, list):
                for c in content:
                    if c.get('type') == 'tool_result' and c.get('is_error'):
                        body = c.get('content')
                        text = ''.join(x.get('text', '') for x in body if isinstance(x, dict)) if isinstance(body, list) else str(body or '')
                        if 'has not been read yet' in text:
                            counts[aid] += 1
    for k, v in counts.most_common():
        print(v, k)
elif mode == 'cmdlen':
    # distribution of Bash command lengths and heredoc use per agent
    for path in sorted(glob.glob(os.path.join(folder, 'agent-*.jsonl'))):
        aid = os.path.basename(path)[6:14]
        total = 0; n = 0; heredoc = 0; longest = 0; evals = 0
        for o in iter_msgs(path):
            content = (o.get('message') or {}).get('content')
            if o.get('type') == 'assistant' and isinstance(content, list):
                for c in content:
                    if c.get('type') == 'tool_use' and c.get('name') == 'Bash':
                        cmd = (c.get('input') or {}).get('command') or ''
                        n += 1; total += len(cmd); longest = max(longest, len(cmd))
                        if '<<' in cmd: heredoc += 1
                        if 'evaluate' in cmd or 'eval ' in cmd: evals += 1
        if n:
            print(f'{aid} bash={n} chars={total} avg={total//n} longest={longest} heredocs={heredoc} evaluates={evals}')
elif mode == 'phrases':
    pat = re.compile(sys.argv[3], re.I)
    for path in sorted(glob.glob(os.path.join(folder, 'agent-*.jsonl'))):
        aid = os.path.basename(path)[6:14]
        for o in iter_msgs(path):
            content = (o.get('message') or {}).get('content')
            if o.get('type') == 'assistant' and isinstance(content, list):
                for c in content:
                    if c.get('type') == 'text':
                        for m in pat.finditer(c.get('text', '')):
                            s = max(0, m.start() - 120); e = min(len(c['text']), m.end() + 160)
                            print(aid, '|', c['text'][s:e].replace('\n', ' '))
