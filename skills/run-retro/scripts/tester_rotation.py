import json, sys
path = sys.argv[1]
# per-turn context, grouped by check (a check starts at each coordinator message)
turns = []  # (check_index, ctx)
check = 0
seen = set()  # one message spans several lines: count each id once
for line in open(path):
    try: o = json.loads(line)
    except: continue
    t = o.get('type'); msg = o.get('message') or {}; c = msg.get('content')
    if t == 'user':
        txt = c if isinstance(c, str) else ''.join(x.get('text','') for x in c if isinstance(x, dict) and x.get('type')=='text') if isinstance(c, list) else ''
        if 'The coordinator sent a message' in txt and ('Check' in txt or 'sweep' in txt or 're-check' in txt): check += 1
    elif t == 'assistant':
        if msg.get('id') in seen: continue
        if msg.get('id'): seen.add(msg['id'])
        u = msg.get('usage') or {}
        ctx = (u.get('input_tokens') or 0)+(u.get('cache_read_input_tokens') or 0)+(u.get('cache_creation_input_tokens') or 0)
        turns.append((check, ctx))
import collections
per = collections.OrderedDict()
for ch, ctx in turns:
    per.setdefault(ch, []).append(ctx)
print('check | turns | ctx at start | ctx at end | growth | sum ctx (M)')
tot = 0
growth = {}
for ch, cs in per.items():
    g = cs[-1]-cs[0]; growth[ch] = g; tot += sum(cs)
    print(ch, len(cs), cs[0], cs[-1], g, round(sum(cs)/1e6, 1))
print('total ctx-turns (M):', round(tot/1e6, 1))
# simulate: a fresh tester starts at START ctx (brief + skill + this-machine + README + handover), each check adds its measured turns and growth
START = int(sys.argv[2]) if len(sys.argv) > 2 else 70000
checks = [(len(cs), growth[ch]) for ch, cs in per.items() if ch >= 1]
def simulate(every, turn_scale=1.0):
    total = 0; ctx = START; n = 0; testers = 1
    for i, (nt, g) in enumerate(checks):
        if i > 0 and i % every == 0:
            ctx = START; testers += 1; total += START * 8  # handover write + fresh read, ~8 turns
        nt = int(nt * turn_scale)
        for k in range(nt):
            total += ctx + g * k / max(nt, 1)
        ctx += g
    return testers, round(total/1e6)
for every in (3, 4, 5, 6, 8, 99):
    print('rotate every', every, '-> testers, ctx-turns (M):', simulate(every))
print('with seed helper (turns x0.75, growth x0.8):')
checks = [(nt, int(g*0.8)) for nt, g in checks]
for every in (3, 4, 5, 6, 8, 99):
    print('rotate every', every, '->', simulate(every, 0.75))
