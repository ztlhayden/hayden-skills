---
name: run-sheet
description: "Draft the run sheet for an unattended ticket run from a feature's ready tickets: lanes, models, blockers, seams, scope, sweep."
argument-hint: "<milestone, e.g. shop/refunds, or a markdown feature folder, e.g. shop/tickets/refunds>"
disable-model-invocation: true
---

# Run sheet

Draft the **run sheet** an unattended ticket run starts from (`/ticket-run <sheet>`): the tickets of one feature grouped into **lanes**, a model per ticket, the **blocker walk**'s findings, the **seams** between lanes, what is out of scope, and what the final sweep opens. The orchestrator brief (`~/.claude/skills/ticket-run/briefs/orchestrator.md`) carries everything else.

The template is `run-sheet.template.md` beside this file. `<notes>` is the notes repo (`$NOTES_ROOT`, or `~/code/ai-notes` when unset); the previous sheets are `<notes>/sessions/*-run-sheet.md`. `<issues>` is `python3 ~/.claude/skills/project-notes/scripts/issues.py`, and `<scripts>` is `~/.claude/skills/project-notes/scripts/`.

## Process

### 1. Find the tracker

The user passes a milestone (`<project>/<feature>`) or a feature folder (`<project>/tickets/<feature>`); ask if neither. A folder with an `issues/` folder of open tickets is a markdown feature, not yet moved to issues. A folder holding only its `spec.md` has moved: its tickets are issues in the milestone `<project>/<feature>`. The sheet's Tickets line names whichever it is, and every step below takes that tracker's command.

### 2. Gather the tickets

From `<notes>`:

- The tickets, one line each. Issues: `<issues> list <milestone>`. Markdown: `python3 <scripts>/check-tickets.py --ready <folder>`. The `ready-for-agent` ones are the run's candidates; the rest (`ready-for-human`, `needs-*`, in progress) are listed as out of scope.
- Each candidate's boxes, blockers and last comment. Issues: `<issues> show <n>`. Markdown: `python3 <scripts>/ticket.py show <folder>`. Read whole (`show --all`) any ticket whose last comment or status line points at its earlier comments.
- The newest `sessions/*-run-sheet.md` for the same repo: its header lines (repo, branch, PR, desks, report name) carry over unless the user says otherwise; its model choices show what fitted.
- `~/.claude/skills/project-notes/ticket-checklist.md`. A candidate that fails a line of it is not in the run: list it under a "Checklist" heading in your reply with the failing line, and leave its status alone.

### 3. Walk the blockers

Every candidate's blockers, walked to the end of the chain. Issues: `<issues> survey <milestone>` (startable now, and blocker problems), `<issues> chain <n>` for each blocked candidate, and `<issues> check`. Markdown: `python3 <scripts>/check-tickets.py <folder>`, following each `Blocked by:` line. Every finding goes in the sheet's Blocker walk section, each with what the run does about it:

- a chain that ends on a person (`ready-for-human`, `needs-*`, the maintainer's in-progress work): the ticket waits, or leaves the run;
- a blocker outside the run that an agent is building elsewhere: the ticket waits, or leaves the run;
- a blocker with a lower priority than what waits on it, or a cycle: a question for the user in step 6. An issue whose blockers are all closed is unblocked.

Also list, from each candidate's `blocks:` line (issues) or `ticket.py refs` (markdown), the tickets outside the run that it unblocks.

### 4. Propose lanes

<lane-rules>

- Tickets that change the same collection, screen or served document share a lane, ordered so each ticket's blockers and the pattern it copies come first.
- A ticket that only reads what another lane changes is its own lane, and the shared thing is a seam (step 5).
- A helper every later ticket needs (a seed, a fixture, a script) is a phase-0 lane: it runs alone and merges before any other branch is cut.
- The longest lane is listed first, so it starts first.

</lane-rules>

Then a model per ticket:

<model-rules>

- Opus: a custom admin screen or component, a picker with its own label or search, framework internals, a migration that must stop with names, or the first ticket to build a pattern others copy.
- Sonnet: a rule, a field, a plain migration, a catalogue shape, or a ticket that copies a pattern already merged.
- The last sheets and `~/.claude/skills/ticket-run/briefs/README.md` say what fitted; a ticket shaped like one that overran its model moves up.

</model-rules>

### 5. Find seams and other-repo halves

A seam is one lane's change that another lane's code reads: a served value, a label, a shape in a document. For each, write the one-line check the second merger runs on the merged code and the page the sweep opens. A ticket whose repo (its `repo:` labels, or `Repo:` line) or boxes name a second repo keeps only this repo's boxes in the run and ends `ready-for-human` with the other half named.

### 6. Quiz the user

Present the draft as the sheet's tables and ask:

- Are the lanes right: does each one hold the tickets that truly share collections and screens, in the right order?
- Is each model right, given the ticket's shape?
- Each blocker finding: does the run wait, leave the ticket out, or does the user fix the blocker first?
- Is every seam caught, and does its named check say what to confirm?
- Anything to add to the out-of-scope list, and is the sweep list complete?

Iterate until the user approves.

### 7. Write the sheet

Write `<notes>/sessions/<today>-run-sheet.md` from the template, every line filled, none deleted. Commit it to the notes repo's `main`, staging only that file, and push. Reply with its path and the one command that starts the run:

```
/ticket-run <notes>/sessions/<today>-run-sheet.md
```
