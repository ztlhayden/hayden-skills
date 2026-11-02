import json, sys, re
path = sys.argv[1]
ctx = 0; turns = 0; checks = []; seen = set()
login = seed = snap = shot = 0; writes = []
for line in open(path):
    try: o = json.loads(line)
    except: continue
    t = o.get('type'); msg = o.get('message') or {}; c = msg.get('content'); ts = o.get('timestamp','')[11:19]
    if t == 'assistant':
        # one message spans several lines: a turn is a new message id
        if msg.get('id') not in seen: turns += 1
        if msg.get('id'): seen.add(msg['id'])
        u = msg.get('usage') or {}
        ctx = (u.get('input_tokens') or 0)+(u.get('cache_read_input_tokens') or 0)+(u.get('cache_creation_input_tokens') or 0)
        if isinstance(c, list):
            for x in c:
                if x.get('type')=='tool_use':
                    inp = x.get('input') or {}
                    cmd = inp.get('command') or ''
                    if x['name']=='Bash':
                        if 'users/login' in cmd or 'login.sh' in cmd: login += 1
                        if 'seed' in cmd and ('node' in cmd or 'tsx' in cmd or 'bash' in cmd or '.sh' in cmd or '.mjs' in cmd): seed += 1
                        if 'snapshot' in cmd: snap += 1
                        if 'screenshot' in cmd: shot += 1
                    if x['name']=='Write': writes.append(inp.get('file_path','').split('/')[-1])
    elif t == 'user':
        txt = None
        if isinstance(c, str): txt = c
        elif isinstance(c, list):
            for x in c:
                if x.get('type')=='text': txt = x.get('text','')
        if txt and not txt.startswith('<system-reminder') and not txt.startswith('<local-command'):
            checks.append((ts, turns, ctx, len(txt), txt[:100].replace('\n',' ')))
print('incoming messages: ts | turn | ctx before | msg bytes | head')
for ch in checks: print(ch)
print('turns', turns, 'login cmds', login, 'seed runs', seed, 'snapshots', snap, 'screenshots', shot)
print('writes', len(writes), sorted(set(writes)))
