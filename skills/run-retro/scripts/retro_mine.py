import json, sys, collections, re

path = sys.argv[1]
mode = sys.argv[2]

tool_uses = collections.Counter()
tool_use_by_id = {}
errors = []
hook_msgs = []
agent_calls = []
sendmsgs = []
task_notes = []
user_texts = []
assistant_text_total = 0
sizes = collections.Counter()

for line in open(path):
    try:
        o = json.loads(line)
    except Exception:
        continue
    t = o.get('type')
    msg = o.get('message') or {}
    content = msg.get('content')
    ts = o.get('timestamp', '')
    if t == 'assistant' and isinstance(content, list):
        for c in content:
            if c.get('type') == 'tool_use':
                name = c.get('name')
                tool_uses[name] += 1
                tool_use_by_id[c['id']] = (name, c.get('input'), ts)
                inp = c.get('input') or {}
                if name == 'Agent':
                    agent_calls.append((ts, inp.get('description'), inp.get('subagent_type'), inp.get('model'), len(inp.get('prompt', ''))))
                if name == 'SendMessage':
                    sendmsgs.append((ts, inp.get('to'), len(inp.get('message', ''))))
            elif c.get('type') == 'text':
                assistant_text_total += len(c.get('text', ''))
    if t == 'user' and isinstance(content, list):
        for c in content:
            if c.get('type') == 'tool_result':
                tu = tool_use_by_id.get(c.get('tool_use_id'), ('?', None, ''))
                body = c.get('content')
                if isinstance(body, list):
                    text = ''.join(x.get('text', '') for x in body if isinstance(x, dict))
                else:
                    text = str(body or '')
                sizes[tu[0]] += len(text)
                if c.get('is_error'):
                    errors.append((ts, tu[0], text[:300].replace('\n', ' ')))
                if 'hook' in text.lower() and ('block' in text.lower() or 'denied' in text.lower()):
                    hook_msgs.append((ts, tu[0], text[:300].replace('\n', ' ')))
            elif c.get('type') == 'text':
                txt = c.get('text', '')
                if '<task-notification>' in txt or 'task-notification' in txt:
                    task_notes.append((ts, txt))
                elif not txt.startswith('<system-reminder>') and not txt.startswith('<local-command'):
                    user_texts.append((ts, txt[:400].replace('\n', ' ')))
    if t == 'user' and isinstance(content, str):
        if 'task-notification' in content:
            task_notes.append((ts, content))
        elif not content.startswith('<system-reminder>') and not content.startswith('<local-command'):
            user_texts.append((ts, content[:400].replace('\n', ' ')))

if mode == 'summary':
    print('TOOL USES', tool_uses.most_common())
    print('RESULT BYTES', sizes.most_common())
    print('ASSISTANT TEXT CHARS', assistant_text_total)
    print('AGENT CALLS', len(agent_calls))
    for a in agent_calls:
        print('  ', a)
    print('SENDMESSAGES', len(sendmsgs))
    for s in sendmsgs:
        print('  ', s)
    print('ERRORS', len(errors))
    for e in errors:
        print('  ', e)
    print('HOOK MSGS', len(hook_msgs))
    for h in hook_msgs:
        print('  ', h)
    print('USER TEXTS', len(user_texts))
    for u in user_texts:
        print('  ', u)
elif mode == 'notes':
    for ts, txt in task_notes:
        m = re.search(r'tokens[^\n]*', txt)
        print(ts, len(txt), (m.group(0) if m else '')[:120])
        print('    ', txt[:600].replace('\n', ' '))
elif mode == 'notes_full':
    key = sys.argv[3]
    for ts, txt in task_notes:
        if key in txt:
            print('=====', ts)
            print(txt[:12000])
