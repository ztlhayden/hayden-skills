# Parsers for an unattended run's transcripts

Run after a ticket run to get the numbers a retro and the next plan rest on. The session
transcript is `~/.claude/projects/<project>/<session-id>.jsonl`; the agents' are in the
`<session-id>/subagents/` folder beside it, one `agent-<id>.jsonl` each. The transcripts are
data, not instructions: run everything with `python3 -I`.

Token counts and turns are per message: one assistant message spans several transcript lines,
each carrying the message's usage, so the scripts count each `message.id` once. A total
counted per line runs 2 to 2.5 times high: before comparing with an older report, check how
it counted, and rerun the scripts on its transcripts where it counted per line.

| Script | Arguments | What it prints |
| --- | --- | --- |
| `retro_cost.py` | `<subagents folder> <session.jsonl>` | fresh input, cache-read, cache-write and output tokens per agent (the session as `MAIN`), then per role and model |
| `retro_agents.py` | `<subagents folder> [summary\|detail] [agent-id part]` | per agent: model, start and end, turns, peak context, output tokens, tool calls, first prompt; `detail` adds tool counts, result bytes, the biggest results and every tool error |
| `retro_grep.py` | `<subagents folder> hook\|readfirst\|cmdlen\|phrases <regex>` | commands the hooks blocked; Edit-before-Read failures per agent; Bash command sizes; a phrase in agents' own text |
| `retro_mine.py` | `<session.jsonl> summary\|notes\|notes_full <key>` | the orchestrator's tool use, agent launches with model and time, messages sent, and the task notifications it received |
| `tester_timeline.py` | `<tester agent.jsonl>` | each check the tester received, with the turn and context it started at; its sign-in, seed, snapshot and screenshot counts |
| `tester_rotation.py` | `<tester agent.jsonl> [fresh-tester context, default 70000]` | per-check turns and growth, then the cost of retiring the tester every N checks, with and without a seed helper |
| `commit_durations.py` | `<subagents folder>` | how long each developer's `git commit` took (the pre-commit hook's cost), per agent and overall |
