import json, sys, glob, os, collections

folder = sys.argv[1]
main = sys.argv[2]
rows = []

def cost(path):
    # One assistant message spans several transcript lines (one per content
    # block), each carrying the message's usage: count each message id once.
    usage = {}
    model = ''
    first = ''
    for n, line in enumerate(open(path)):
        try:
            o = json.loads(line)
        except Exception:
            continue
        if o.get('type') == 'assistant':
            msg = o.get('message') or {}
            usage[msg.get('id') or n] = msg.get('usage') or {}
            model = msg.get('model') or model
        elif o.get('type') == 'user' and not first:
            c = (o.get('message') or {}).get('content')
            if isinstance(c, str):
                first = c[:70]
            elif isinstance(c, list):
                for x in c:
                    if x.get('type') == 'text':
                        first = x['text'][:70]; break
    def total(key):
        return sum(u.get(key) or 0 for u in usage.values())
    inp, cr = total('input_tokens'), total('cache_read_input_tokens')
    cc, out = total('cache_creation_input_tokens'), total('output_tokens')
    return model, inp, cr, cc, out, first.replace('\n', ' ')

for path in sorted(glob.glob(os.path.join(folder, 'agent-*.jsonl'))):
    rows.append((os.path.basename(path)[6:14],) + cost(path))
rows.append(('MAIN',) + cost(main))

# role buckets
def role(first):
    f = first.lower()
    # The role sentence that opens each brief's prompt, most specific first.
    if 'whole-run reviewer' in f or 'axis of a code review' in f: return 'whole-run review'
    if 'developer fixing' in f: return 'fix pass'
    if 'you are the developer' in f: return 'developer'
    if 'you are the reviewer' in f: return 'reviewer'
    if 'you are the merger' in f: return 'merger'
    if f.startswith('build ticket'): return 'developer'
    if f.startswith('review ticket'): return 'reviewer'
    if f.startswith('merge ticket'): return 'merger'
    if 'browser tester' in f: return 'tester'
    if 'review' in f: return 'branch review'
    if 'fix' in f: return 'fix pass'
    return 'orchestrator' if first == '' or 'orchestrator' in f else 'other'

print('agent | model | role | fresh in | cache read | cache write | out | first')
tot = collections.defaultdict(lambda: [0, 0, 0, 0, 0])
for r in sorted(rows, key=lambda r: -(r[2] + r[3] + r[4])):
    aid, model, inp, cr, cc, out, first = r
    rl = role(first) if aid != 'MAIN' else 'orchestrator'
    print(f'{aid} | {model[-10:]} | {rl} | {inp} | {cr} | {cc} | {out} | {first[:50]}')
    key = (rl, model[-10:])
    tot[key][0] += inp; tot[key][1] += cr; tot[key][2] += cc; tot[key][3] += out; tot[key][4] += 1
print()
print('role | model | agents | fresh in | cache read | cache write | out')
for k, v in sorted(tot.items(), key=lambda kv: -(kv[1][1])):
    print(k[0], '|', k[1], '|', v[4], '|', v[0], '|', v[1], '|', v[2], '|', v[3])
