---
name: run-sheet
description: "Draft the run sheet for an unattended ticket run from a feature's ready tickets: lanes, models, seams, scope, sweep."
argument-hint: "<feature folder in ~/code/ai-notes, e.g. courseware/tickets/first-course>"
disable-model-invocation: true
---

# Run sheet

Draft the **run sheet** an unattended ticket run starts from (`/ticket-run <sheet>`): the tickets of one feature grouped into **lanes**, a model per ticket, the **seams** between lanes, what is out of scope, and what the final sweep opens. The orchestrator brief (`~/.claude/skills/ticket-run/briefs/orchestrator.md`) carries everything else.

The template is `run-sheet.template.md` beside this file; the previous sheets are in the notes repo, `~/code/ai-notes/sessions/*-run-sheet.md`. The ticket scripts below are `~/.claude/skills/project-notes/scripts/`, written `<scripts>`.

## Process

### 1. Gather the tickets

From `~/code/ai-notes`, with the feature folder the user passed (ask if none):

- `python3 <scripts>/check-tickets.py --ready <folder>`: the `ready-for-agent` tickets are the run's candidates; `ready-for-human` ones are listed as out of scope.
- `python3 <scripts>/ticket.py show <folder>`: every ticket's boxes, blockers and last comment. Read whole any ticket whose status line mentions its comments.
- The newest `sessions/*-run-sheet.md` for the same repo: its header lines (repo, branch, PR, desks, report name) carry over unless the user says otherwise; its model choices show what fitted.
- `~/.claude/skills/project-notes/ticket-checklist.md`. A candidate that fails a line of it is not in the run: list it under a "Checklist" heading in your reply with the failing line, and leave its status alone.

### 2. Propose lanes

<lane-rules>

- Tickets that change the same collection, screen or served document share a lane, ordered so each ticket's blockers and the pattern it copies come first.
- A ticket that only reads what another lane changes is its own lane, and the shared thing is a seam (step 4).
- A helper every later ticket needs (a seed, a fixture, a script) is a phase-0 lane: it runs alone and merges before any other branch is cut.
- The longest lane is listed first, so it starts first.

</lane-rules>

### 3. Propose a model per ticket

<model-rules>

- Opus: a custom admin screen or component, a picker with its own label or search, framework internals, a migration that must stop with names, or the first ticket to build a pattern others copy.
- Sonnet: a rule, a field, a plain migration, a catalogue shape, or a ticket that copies a pattern already merged.
- The last sheets and `~/.claude/skills/ticket-run/briefs/README.md` say what fitted; a ticket shaped like one that overran its model moves up.

</model-rules>

### 4. Find seams and other-repo halves

A seam is one lane's change that another lane's code reads: a served value, a label, a shape in a document. For each, write the one-line check the second merger runs on the merged code and the page the sweep opens. A ticket whose `Repo:` line or boxes name a second repo keeps only this repo's boxes in the run and ends `ready-for-human` with the other half named.

### 5. Quiz the user

Present the draft as the sheet's tables and ask:

- Are the lanes right: does each one hold the tickets that truly share collections and screens, in the right order?
- Is each model right, given the ticket's shape?
- Is every seam caught, and does its named check say what to confirm?
- Anything to add to the out-of-scope list, and is the sweep list complete?

Iterate until the user approves.

### 6. Write the sheet

Write `~/code/ai-notes/sessions/<today>-run-sheet.md` from the template, every line filled, none deleted. Commit it to ai-notes `main`, staging only that file, and push. Reply with its path and the one command that starts the run:

```
/ticket-run ~/code/ai-notes/sessions/<today>-run-sheet.md
```
