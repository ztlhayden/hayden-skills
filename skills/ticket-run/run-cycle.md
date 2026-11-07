# The ticket-run cycle

How work alternates between hands-on sessions and unattended runs. One loop per feature,
repeated until its tickets are all closed. The tickets are issues in the feature's milestone,
or files in its folder for a feature not yet moved to issues; the decisions, run sheets,
reports and retros are files in the private notes repo (`$NOTES_ROOT`, by default
`~/code/ai-notes`). The `project-notes` skill describes both.

1. **Settle** (hands-on, the user present). Findings first: every open finding from the last
   report and every `ready-for-human` ticket gets a decision (`decisions/`) or a comment on the
   ticket saying it is left out. Then tickets: new ones through `/to-tickets`, each passed
   through [`ticket-checklist.md`](../project-notes/ticket-checklist.md) before it turns
   `ready-for-agent`. Last, the run sheet: `/run-sheet <milestone or feature folder>` drafts it
   from the ready tickets (lanes, models, the blocker walk, seams, scope, sweep) and asks you
   to confirm the judgement calls; by hand, copy
   [`run-sheet.template.md`](../run-sheet/run-sheet.template.md) to the notes repo's
   `sessions/<date>-run-sheet.md` and fill it.
2. **Run** (unattended). From the repo, on the orchestrator's model: `/ticket-run <sheet>`.
   The orchestrator follows [`briefs/orchestrator.md`](briefs/orchestrator.md) and hands the
   four role briefs to its agents. It ends with the PR updated, each ticket's report as a
   comment on it, and the run's report in `sessions/`.
3. **Review** (hands-on). Read the report's outcome line and findings; review the PR; merge it
   or send findings back into step 1. Then `/run-retro <session>` for the numbers, appended to
   the run's report; a brief changes only when a number or a finding says so.

When to run, and when not to: a run carries about an hour of fixed cost (setup, whole-run
review, sweep, report) plus the orchestrator. With one to three tickets and the user around,
start one developer per ticket by hand with `briefs/developer.md`, review, and merge: no
orchestrator. Use the run for four or more tickets, or whenever the user will be away for a
few hours regardless. A run that would exceed the account's session window starts just after
a reset.

The runs so far, with their plans and retros, are in the notes repo's `sessions/`.
