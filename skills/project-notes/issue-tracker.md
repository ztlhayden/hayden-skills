# Issue tracker: GitHub issues on the notes repo

Tickets for every project are GitHub issues on the **issues repo**: the private
repo named by `issues_repo` in the notes repo's `project-notes.json` (see
[The config](#the-config)), normally the notes repo itself. Never in a code
repo: several may be public, and tickets may carry private detail. Specs, maps,
glossaries and decisions stay files in the notes repo. Start from the pinned
**Start here** issue (`start_here` in the config), which links a search for
each view. The repo is private: read it with `gh` or the helper, never by
fetching a link.

Issues are the tracker for agent work in every project, including ones that
also have a card in another tracker (Jira, say). Agents change that other
tracker only when the user asks in that session.

This file is the issue-tracker config that Matt Pocock's skills read; its
shape (the "When a skill says" and Wayfinding sections) follows his
`setup-matt-pocock-skills` templates.

## The config

`$NOTES_ROOT/project-notes.json` (`NOTES_ROOT` defaults to `~/code/ai-notes`):

```json
{"issues_repo": "acme/notes",
 "board": {"owner": "acme", "number": 3},
 "start_here": 1,
 "goals": [{"text": "Ship checkout"}, {"text": "Move to issues", "milestone": "shop/issues"}]}
```

Only `issues_repo` is required. Without `board`, nothing syncs a board; without
`start_here`, there is no Start here issue to rebuild. `goals` are the current
goals Start here lists (three or four), each optionally tied to a milestone.
Below, `<repo>` is `issues_repo`.

## The helper

`python3 ~/.claude/skills/project-notes/scripts/issues.py <command>` (from
any folder; called `issues.py` below) does the common jobs in a few lines of
output; `--help` gives each command's arguments. Use it wherever it has a
command; raw `gh` only for what it doesn't do (a milestone's due date, moving
an issue to another milestone, editing a body).

- `survey [<milestone>]`: one line per milestone with its count of each status
  and priority, the issues an agent can start, the `ready-for-human` ones
  waiting on a person, and any blocker problems.
  Start a survey here instead of reading issues.
- `list <milestone>`: every open issue in it, one line each, with its open
  blockers.
- `show <n>`: an issue with all but its last comment folded, for surveys.
  Before working on an issue, read it whole with `show --all <n>`: comments
  hold open questions, branches and handoff notes.
- `chain <n>` walks an issue's *blocked by* links to the end; `check` does it
  for every open issue and says when Start here is out of date.
- `claim <n>`, `release <n> <status> [--comment-file <file>]`, `close <n>
  --completed|--not-planned --comment-file <file>`: see below. All three keep
  the board in step.
- `comment <n> --comment-file <file>`: post a comment.
- `search [--all] <words>`: matching issues, one line each.
- `new ...`: create an issue with every label group, its milestone and its
  blockers (see New issues).
- `status <n> <status>`, `priority <n> now|soon|later`, `block [--remove] <n>
  <blocker>...`: triage changes, each with an optional `--comment-file`.
- `board [<n>...]`: copy labels onto the board, for issues changed with raw
  `gh`.
- `start-here [--dry-run]`: rebuild Start here from the labels, milestones
  and goals, after adding a project, repo, milestone or goal.

Tests: `python3 test_issues.py` in the scripts folder.

## Milestones and labels

- **A feature is a milestone** named `<project>/<feature>`, whose description
  links its spec at `<project>/specs/<feature>/spec.md` in the notes repo. A
  deadline is the milestone's due date.
- **Labels**, four groups on every issue: `org:` (the GitHub owner the work
  is for), `project:` (the notes folder), `repo:` (where the code lands, its
  GitHub name without the owner; one or more), `status:` (see
  `triage-labels.md`). Plus `type:` (`task`, `grilling`, `prototype`,
  `research`) and, once triaged, a priority.
- **Blocked** is GitHub's own *blocked by* link, not a label: give a blocked
  issue the status it takes once unblocked. Only open blockers count. **Done**
  is closed as completed; **wontfix** is closed as not planned.

## Working an issue

- **Claim** with `issues.py claim <n>` before any work: it sets
  `status:in-progress-agent` in place of the ready label, and refuses an issue
  already `in-progress-agent` or `in-progress-me` (the maintainer's), a closed
  one, and one with an open blocker. Leave an in-progress issue alone.
- **Stop** with `issues.py release <n> <status> --comment-file <file>`,
  setting the status the work left it in, with a comment saying where it got
  to.
- **Finish** with `issues.py close <n> --completed --comment-file <file>`: one
  comment saying what was built, where (commits, branch), how it was checked,
  and anything the maintainer should know. It says which issues that
  unblocks.
- **Change one thing at a time,** through the helper: `issues.py status <n>
  <status>` at triage, `priority <n> now|soon|later`, `block [--remove] <n>
  <blocker>...`, `comment <n> --comment-file <file>` (each takes
  `--comment-file` to say why). They keep the board in step and report any
  blocker below the issue's priority. Every ticket change an unattended run
  makes goes through them, so a run never stops for an approval. Raw `gh` is
  only for what they don't do (moving an issue to another milestone, editing
  a body: change the one line, keeping the rest as it is).
- **Your comments don't notify the maintainer** when agents act as the
  maintainer's account: GitHub notifies no one of their own actions. So a
  question for them also sets `status:ready-for-human`, which puts it in
  Start here's "Needs me"; in a live session, say it there too.
- **Search** with `issues.py search [--all] <words>`: one line per match,
  open only unless `--all`.
- Shared text (commits, PRs, code) leaves these issues unnamed: the people
  who read it can't see them.

## New issues

- **From an agent:** `issues.py new --title ... --body-file <file> --org <o>
  --project <p> [--repo <r>]... --type <t> --status <s> [--priority now|soon]
  --milestone <project>/<feature> [--blocked-by <n>]...`. It refuses a label or
  milestone the repo doesn't have, so a typo can't make one; for a new
  project, repo, type or feature add `--create` (and
  `--milestone-description <spec link>`), which makes them and rebuilds
  Start here.
- **From a form** (an issue template in the notes repo, for the phone, say):
  it applies only `status:needs-triage`, and its answers sit in the body.
  Triage reads them, then adds the label groups and milestone.
- **A deadline** is the milestone's due date: `gh api -X PATCH
  repos/<repo>/milestones/<number> -f due_on=<date>T00:00:00Z` (raw `gh`, so
  it asks; deadlines are set at triage, with the maintainer).

## Triage and priority

**Priority** is `priority:now`, `priority:soon`, or no label (later, by
decision). It is always set at triage, so a triaged issue with no priority
label is later, and one still `status:needs-triage` is not assessed yet.

**Triage asks the maintainer, on the issue.** Comment with the triage
questions and these six, answered as far as you can with evidence (read the
code, the live site, the data) and a suggested status and priority; ask them
to confirm, so they can answer from their phone. The next agent applies the
answer. In a live session, ask the same as a round instead.

1. Is there a deadline? (Within about two weeks: `now`; later: `soon`, and the
   date goes on the milestone's due date.)
2. Does it block another team member? (`now`)
3. Does it break a feature users actively rely on? (`now`)
4. Is it an open broken promise? (`now`)
5. Is it a privacy or security issue? (`now`, whatever else is true)
6. If none of these: does it move one of the current goals forward?
   (`soon`; otherwise no label)

## Blockers

- **Priority and blocked are separate.** A blocked issue keeps its priority;
  Start here's working lists ("Now", "Soon") hide blocked issues, and
  "Blocked and urgent" shows them.
- **A blocker's priority is at least the highest priority of what it
  blocks.** Whenever you set or raise a priority, run `issues.py chain <n>`
  and raise any blocker it reports below the issue, with a comment saying why.
- **Every helper probes blockers.** Any script, skill or run tool built for
  these issues walks the whole *blocked by* chain, not one step, and reports:
  blockers with a lower priority than what waits on them, cycles, and for
  each blocked issue what it ultimately waits on and whether that is a person
  (`ready-for-human`) or an agent's work. An issue whose blockers are all
  closed is unblocked (GitHub keeps closed blockers on the link; its
  `is:blocked` ignores them). `issues.py chain` and `check` are the model.

## The board and the snapshot

- **The board** (`board` in the config, a GitHub Project) holds every
  labelled issue; its single-select fields Triage, Project, Org and Code repo
  copy the labels, and Status is Todo, In Progress or Done. `claim`,
  `release` and `close` keep it in step; after any other label change, run
  `issues.py board <n>`. A `!` line means the board has no option for that
  label yet: add it on the board.
- **The snapshot** `issues/snapshot.json` in the notes repo holds every issue
  (comments, labels, milestone, blockers), written nightly by the "Issues
  snapshot" Action (`templates/issues-snapshot.yml` in the skills repo). It is
  for offline reading and recovery only: normal work reads the issues with
  `gh`.

## When a skill says...

- **"publish to the issue tracker"**: create an issue as in
  [New issues](#new-issues), in the feature's milestone.
- **"fetch the relevant ticket"**: `issues.py show --all <n>`. The user
  normally passes the number or link.
- **`/to-tickets`**: only the user can start it; an agent can't load it. When
  the user asks for tickets by that name, ask them to type `/to-tickets`. Its
  output becomes issues in the feature's milestone, its blockers *blocked by*
  links, and its status labels.

## Wayfinding operations

Used by `/wayfinder`, for one effort's milestone:

- **Map**: `map.md` (Notes / Decisions so far / Fog), a file in
  `<project>/specs/<effort>/` beside the spec.
- **Child ticket**: an issue in the milestone with the question in the body
  and its `type:` label.
- **Blocking**: *blocked by* links. A ticket is unblocked when every blocker
  is closed as completed.
- **Frontier**: `issues.py survey <milestone>`'s startable list; lowest
  number first.
- **Claim**: `issues.py claim <n>` before any work.
- **Resolve**: the answer as the closing comment (`issues.py close <n>
  --completed --comment-file <file>`), and a one-line pointer in `map.md`'s
  Decisions so far.

## The feature folder

A feature's folder in the notes repo, `<project>/specs/<feature>/`, holds
its `spec.md` (and `map.md`, for a wayfinding effort) and nothing else: its
tickets are issues in its milestone. A finished feature's folder moves to
`<project>/specs/archive/`.

After changing anything in the notes repo, commit and push it straight to
`main`.
