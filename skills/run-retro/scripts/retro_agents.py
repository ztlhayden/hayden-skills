import json, sys, collections, glob, os, re

folder = sys.argv[1]
mode = sys.argv[2] if len(sys.argv) > 2 else 'summary'
only = sys.argv[3] if len(sys.argv) > 3 else None

all_errors = collections.Counter()
rows = []
for path in sorted(glob.glob(os.path.join(folder, 'agent-*.jsonl'))):
    aid = os.path.basename(path)[6:-6]
    if only and only not in aid:
        continue
    uses = collections.Counter()
    bytes_by_tool = collections.Counter()
    by_id = {}
    errors = []
    big = []
    first_prompt = ''
    max_input = 0
    # One message spans several lines, each with its usage: count each id once.
    out_by_msg = {}
    ts_first = ts_last = ''
    model = ''
    for line in open(path):
        try:
            o = json.loads(line)
        except Exception:
            continue
        t = o.get('type')
        msg = o.get('message') or {}
        content = msg.get('content')
        ts = o.get('timestamp', '')
        if ts:
            ts_first = ts_first or ts
            ts_last = ts
        if t == 'assistant':
            model = msg.get('model') or model
            u = msg.get('usage') or {}
            total_in = (u.get('input_tokens') or 0) + (u.get('cache_read_input_tokens') or 0) + (u.get('cache_creation_input_tokens') or 0)
            max_input = max(max_input, total_in)
            out_by_msg[msg.get('id') or (len(out_by_msg), ts)] = u.get('output_tokens') or 0
            if isinstance(content, list):
                for c in content:
                    if c.get('type') == 'tool_use':
                        uses[c.get('name')] += 1
                        by_id[c['id']] = (c.get('name'), c.get('input'))
        elif t == 'user':
            if isinstance(content, str):
                first_prompt = first_prompt or content[:160].replace('\n', ' ')
            elif isinstance(content, list):
                for c in content:
                    if c.get('type') == 'text' and not first_prompt:
                        first_prompt = c.get('text', '')[:160].replace('\n', ' ')
                    if c.get('type') == 'tool_result':
                        name, inp = by_id.get(c.get('tool_use_id'), ('?', None))
                        body = c.get('content')
                        if isinstance(body, list):
                            text = ''.join(x.get('text', '') for x in body if isinstance(x, dict))
                        else:
                            text = str(body or '')
                        bytes_by_tool[name] += len(text)
                        desc = ''
                        if isinstance(inp, dict):
                            desc = inp.get('command') or inp.get('file_path') or inp.get('pattern') or inp.get('skill') or ''
                        big.append((len(text), name, str(desc)[:100].replace('\n', ' ')))
                        if c.get('is_error'):
                            errors.append((name, str(desc)[:80].replace('\n', ' '), text[:200].replace('\n', ' ')))
                            all_errors[text[:90].replace('\n', ' ')] += 1
    big.sort(reverse=True)
    turns, out_tokens = len(out_by_msg), sum(out_by_msg.values())
    rows.append((aid, model, ts_first[11:16], ts_last[11:16], turns, max_input, out_tokens, sum(uses.values()), uses, bytes_by_tool, errors, big[:6], first_prompt))

if mode == 'summary':
    print('agent | model | start-end | turns | peak ctx | out tok | tool calls | first prompt')
    for r in sorted(rows, key=lambda r: r[2]):
        aid, model, a, b, turns, mi, ot, n, uses, bb, errors, big, fp = r
        print(f'{aid[:8]} | {model[:18]} | {a}-{b} | {turns} | {mi} | {ot} | {n} | {fp[:90]}')
    print()
    print('ALL ERRORS (deduped by prefix):')
    for k, v in all_errors.most_common(60):
        print(v, k)
elif mode == 'detail':
    for r in rows:
        aid, model, a, b, turns, mi, ot, n, uses, bb, errors, big, fp = r
        print('=====', aid, model, a, b, 'turns', turns, 'peak ctx', mi, 'out', ot)
        print('  prompt:', fp)
        print('  uses:', uses.most_common())
        print('  bytes:', bb.most_common())
        print('  big results:')
        for x in big:
            print('    ', x)
        print('  errors:')
        for e in errors:
            print('    ', e)
