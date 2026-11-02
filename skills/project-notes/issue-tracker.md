# Issue tracker: local markdown in the notes repo

Tickets for every project live as markdown files in the notes repo,
`~/code/ai-notes`, which is pushed to a private GitHub repo. Never in a code
repo: several are public, and tickets may carry private detail.

The scripts named below are in `~/.claude/skills/project-notes/scripts/`: run
them as `python3 ~/.claude/skills/project-notes/scripts/<script>`, from any
folder. They read the notes repo from `$NOTES_ROOT`, or `~/code/ai-notes` when
that is unset, and take ticket and folder paths relative to it.

## Where

`~/code/ai-notes/<project>/tickets/<feature-slug>/`, where `<project>` is the
project's notes folder (see `domain.md` for which one).

Local tickets are the tracker for agent work in every project, including
ones that also have a Jira card. Agents change Jira only when the user asks
in that session.

## Conventions

- One feature per directory. The spec is `spec.md` in it.
- One file per ticket at `issues/<NN>-<slug>.md`, numbered from `01`; never one
  combined tickets file.
- A closed ticket (`resolved` or `wontfix`) moves to `issues/archive/`, so a
  feature's `issues/` holds only open work. `ticket.py set-status` and
  `resolve` make the move (and move a reopened ticket back) and fix every
  path to it; `ticket.py archive [<folder>]` sweeps a folder. `Blocked by:`
  numbers still find a ticket in `archive/`. The checker reports a ticket on
  the wrong side.
- A `Status:` line near the top records triage state (see `triage-labels.md`).
  Building agents (`/implement`, `/implement-spec`) take only
  `ready-for-agent` tickets whose blockers are resolved; `ready-for-human`
  tickets stay with the user.
- `check-tickets.py` checks every ticket's `Status:` and
  `Blocked by:` lines and lists the tickets ready to work. The notes repo's
  pre-commit hook runs it: `scripts/pre-commit` here is that hook, and the
  notes repo's own `.githooks/pre-commit` calls it (a fresh clone turns it on
  with `git config core.hooksPath .githooks`); `--ready` prints only the list.
  After writing or changing one feature's tickets, pass its folder
  (`check-tickets.py <project>/tickets/<feature>`) to see only those, each
  with its status. `--summary` prints one line per feature with its count of
  each status, and marks features ready to archive.
- `ticket.py show <ticket or feature folder>` prints tickets
  with all but the last comment hidden, and says how many it hid. Use it to
  survey tickets (triage, picking what's ready, checking where a feature
  stands). Before working on a ticket, read the whole file: comments hold
  open questions, branches and handoff notes. `show` prints every comment
  when the `Status:` line mentions them, or with `--all`.
- `ticket.py refs <ticket or feature folder>` lists the
  tickets it blocks and the lines elsewhere that link to it by path. It
  misses prose mentions such as "identity facility-positions 01".
- `ticket.py set-status <ticket> "<status text>"` replaces
  the `Status:` line's value. `ticket.py resolve <ticket> --status "<text>"
  [--comment "<text>" | --comment-file <path>] [--tick]` also ticks every
  `- [ ]` box with `--tick` and appends the comment under `## Comments`.
  Both leave the rest of the file as it was; use them rather than Edit to
  close a ticket. When the ticket moves, they print its new path and every
  file whose paths they fixed: stage all of them. Tests: `test_ticket.py`.
- In a project with more than one repo, a `Repo:` line beside `Blocked by:`
  names the repo or repos the ticket changes, as the project's repo map names
  them (see `repo-map.md`).
- Comments append to the bottom under a `## Comments` heading.
- Once every ticket in a feature is `resolved` or `wontfix`, move the whole
  feature folder to `<project>/tickets/archive/<feature-slug>/` with `git mv`.
  Then add one `../` to each link in it that leaves the folder, and point
  links elsewhere (including `Blocked by:` lines) at the new path. The
  checker still reads archived tickets, so those blockers count as closed.
- A ticket turns `ready-for-agent` only after passing `ticket-checklist.md`:
  the gaps that stop an unattended developer, one line each.
- After writing or changing tickets, commit and push the notes repo straight
  to `main`.

## Writing tickets with `/to-tickets`

Only the user can start `/to-tickets`; an agent can't load it. When the
user asks for tickets by that name, ask them to type `/to-tickets`. Its
template puts tickets under `.scratch/` with a bold `**Status:**`; here they
go in `tickets/<feature-slug>/` with the plain `Status:` line above.

## When a skill says "publish to the issue tracker"

Create a file under the right `tickets/<feature-slug>/` folder, creating it if
needed.

## When a skill says "fetch the relevant ticket"

Read the file at the referenced path. The user normally passes the path or the
ticket number.

## Wayfinding operations

Used by `/wayfinder`, inside the same `tickets/<effort>/` folder:

- **Map**: `map.md` (Notes / Decisions so far / Fog).
- **Child ticket**: `issues/NN-<slug>.md` with the question in the body, a
  `Type:` line (`research`/`prototype`/`grilling`/`task`) and a `Status:` line
  (`claimed`/`resolved`).
- **Blocking**: a `Blocked by: NN, NN` line near the top. A ticket is unblocked
  when every file it lists is `resolved`.
- **Frontier**: open, unblocked, unclaimed files in `issues/`; lowest number
  first.
- **Claim**: set `Status: claimed` and save before any work.
- **Resolve**: append the answer under `## Answer`, set the status with
  `ticket.py set-status <ticket> resolved` (it moves the file to
  `issues/archive/`), and add a one-line pointer to `map.md`'s Decisions so far.
