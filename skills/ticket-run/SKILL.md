---
name: ticket-run
description: "Start an unattended ticket run from a run sheet: the orchestrator brief plus the sheet's tickets, lanes and models."
argument-hint: "<path to the run sheet in the notes repo's sessions/>"
disable-model-invocation: true
---

You are the orchestrator of an unattended ticket run. The argument is the run sheet.

1. Read `briefs/orchestrator.md` beside this file (`~/.claude/skills/ticket-run/briefs/orchestrator.md`) whole: it is your brief, and it says what else to read. `run-cycle.md` beside it describes the loop a run sits in.
2. Read the run sheet the user named. No argument, or a path that does not exist: stop and ask for the sheet; never start a run from memory of an earlier one.
3. Follow the brief, with the sheet supplying every run-specific value. Where the two differ, the sheet wins.

The first line of your reply names the sheet, its milestone and the feature branch's tip SHA the run starts from, before any agent starts.

Credit: the run's loop (a frontier of unblocked tickets, one implementer per ticket in its own worktree, a merger agent, a closing `/code-review`) is adapted from Matt Pocock's `implement-spec` skill, and the developer brief from his `implement` (https://github.com/mattpocock/skills).
