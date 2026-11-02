"""How long each agent's `git commit` took: the pre-commit hook's cost under the run's load.

Usage: python3 -I commit_durations.py <subagents folder>

A Bash tool call's duration is the time from the assistant message that issued it to the user
message that carried its result. Only commands containing `git commit` count; `--amend` and
`--no-verify` are listed separately since the hook may not run for them.
"""

import glob
import json
import os
import statistics
import sys
from datetime import datetime

folder = sys.argv[1]


def when(record):
    return datetime.fromisoformat(record["timestamp"].replace("Z", "+00:00"))


rows = []
for path in sorted(glob.glob(os.path.join(folder, "agent-*.jsonl"))):
    aid = os.path.basename(path)[6:14]
    pending = {}
    for line in open(path):
        try:
            record = json.loads(line)
        except Exception:
            continue
        message = record.get("message") or {}
        content = message.get("content")
        if not isinstance(content, list) or "timestamp" not in record:
            continue
        if record.get("type") == "assistant":
            for block in content:
                if block.get("type") == "tool_use" and block.get("name") == "Bash":
                    command = (block.get("input") or {}).get("command") or ""
                    if "git commit" in command:
                        pending[block["id"]] = (when(record), command)
        elif record.get("type") == "user":
            for block in content:
                if block.get("type") == "tool_result" and block.get("tool_use_id") in pending:
                    started, command = pending.pop(block["tool_use_id"])
                    seconds = (when(record) - started).total_seconds()
                    flag = "amend" if "--amend" in command else "no-verify" if "--no-verify" in command else ""
                    rows.append((aid, seconds, flag, command[:80].replace("\n", " ")))

print("agent | seconds | flag | command")
for aid, seconds, flag, command in rows:
    print(f"{aid} | {seconds:6.1f} | {flag:9} | {command}")
plain = [seconds for _, seconds, flag, _ in rows if not flag]
if plain:
    print()
    print(f"{len(plain)} plain commits: median {statistics.median(plain):.1f} s, "
          f"mean {statistics.mean(plain):.1f} s, max {max(plain):.1f} s")
    by_agent = {}
    for aid, seconds, flag, _ in rows:
        if not flag:
            by_agent.setdefault(aid, []).append(seconds)
    for aid, values in sorted(by_agent.items(), key=lambda kv: -statistics.median(kv[1])):
        print(f"  {aid}: {len(values)} commits, median {statistics.median(values):.1f} s")
