# hayden-skills

Claude Code skills for building a feature's tickets with unattended agent runs, and the conventions they rest on.

| Skill | Started by | What it does |
| --- | --- | --- |
| `project-notes` | Claude, when it works with tickets or project notes | The layout of the private notes repo that holds every project's specs, glossary, decisions and repo map, with its tickets as GitHub issues, and scripts to survey, claim and close them |
| `run-sheet` | you: `/run-sheet <feature>` | Drafts a run's sheet from a feature's `ready-for-agent` tickets: lanes, a model per ticket, seams between lanes, scope, the final sweep |
| `ticket-run` | you: `/ticket-run <run sheet>` | An orchestrator builds the sheet's tickets with developer, reviewer, browser-tester and merger agents, each from its own brief, and ends with a draft PR and a report |
| `run-retro` | you: `/run-retro <session>` | Measures a finished run from its transcripts (tokens and turns per role, tester growth, hook blocks, commit times) and changes the briefs where the numbers say so |

`skills/ticket-run/run-cycle.md` describes the loop they make: settle findings and tickets by hand, run unattended, review, retro.

## Install

Install all four. They refer to each other through `~/.claude/skills/<name>/`.

```bash
npx skills add ztlhayden/hayden-skills
```

To change the briefs from a retro, link the skills from a clone instead, so `/run-retro` edits and pushes the clone. Remove any copies already in `~/.claude/skills` first; `ln` would put the link inside an existing folder.

```bash
git clone git@github.com:ztlhayden/hayden-skills.git ~/code/ztlhayden/hayden-skills
for s in ~/code/ztlhayden/hayden-skills/skills/*/; do ln -sfn "${s%/}" ~/.claude/skills/; done
```

Install [Matt Pocock's skills](https://github.com/mattpocock/skills) too: these build on them (see [Credits](#credits)).

## What the skills expect

- **A private notes repo at `~/code/ai-notes`** (or wherever `NOTES_ROOT` points), apart from the code, because tickets carry private detail and one project can span several repos. One folder per project, holding `README.md` (with its repo map), `GLOSSARY.md`, `decisions/` and `specs/<feature>/spec.md`; run sheets and reports go in `sessions/`. `skills/project-notes/` describes each part.
- **`project-notes.json` at the notes repo's root**, naming where the tickets live. Only `issues_repo` is required:

  ```json
  {
    "issues_repo": "acme/notes",
    "board": {"owner": "acme", "number": 3},
    "start_here": 1,
    "goals": [
      {"text": "Ship the new checkout"},
      {"text": "Move the tickets to issues", "milestone": "shop/issues"}
    ]
  }
  ```

  `issues_repo` is the private GitHub repo whose issues are the tickets (usually the notes repo itself). `board` is an optional GitHub Project kept in step with the labels; its single-select fields Triage, Project, Org, Code repo and Status need an option for each value. `start_here` is an optional pinned issue that `issues.py start-here` rebuilds with one-tap searches, listing `goals`.
- **`gh` logged in** with access to the issues repo (and `project` scope for a board). The scripts call it for everything.
- **The helper allowed in Claude Code's settings**, so an unattended run can change its tickets without stopping for an approval. Every ticket change goes through `issues.py`, which only ever touches the issues repo, so allowing it is narrower than allowing `gh`. In `~/.claude/settings.json`:

  ```json
  "permissions": { "allow": [
    "Bash(python3 ~/.claude/skills/project-notes/scripts/*)",
    "Bash(python3 /home/<you>/.claude/skills/project-notes/scripts/*)"
  ] }
  ```

  Link `scripts/issues.py` onto your `PATH` as `issues` to run it by hand, and allow `Bash(issues *)` too.
- **The nightly snapshot Action**, optional: copy `templates/issues-snapshot.yml` to the notes repo's `.github/workflows/`. It checks out this repo to run `issues-snapshot.py` and commits `issues/snapshot.json`, a backup of every issue. Pin its `ref` to a commit SHA you have read.
- **A `~/.claude/CLAUDE.md` that points at `project-notes`**, so Matt Pocock's skills (`/to-tickets`, `/triage`, `/implement`, `/domain-modeling`, `/wayfinder`) put tickets and decisions where these skills look. For example:

  ```markdown
  ### Issue tracker
  GitHub issues on the notes repo's issues repo. See `~/.claude/skills/project-notes/issue-tracker.md`.
  ### Triage labels
  See `~/.claude/skills/project-notes/triage-labels.md`.
  ### Domain docs
  See `~/.claude/skills/project-notes/domain.md`.
  ```

- **`playwright-cli`** for the browser tester, and git worktrees for the developers. The run sheet's Repo facts say how to install, check and seed each repo.

Python 3.10 or later runs the scripts; they need nothing beyond the standard library. Tests: `python3 test_issues.py` in `skills/project-notes/scripts/`.

## Credits

These skills lean on [Matt Pocock's skills](https://github.com/mattpocock/skills) and point to them rather than repeat them.

- `project-notes` is the config his skills read. `issue-tracker.md`'s shape (ticket layout, the "When a skill says publish / fetch" sections, the Wayfinding operations) comes from his `setup-matt-pocock-skills` templates; `triage-labels.md` maps his five triage roles, as his template asks; `domain.md`'s "Before exploring" follows his `domain.md` and defers to it for using the glossary and flagging decision conflicts.
- `ticket-run`'s loop (a task graph's frontier, one implementer per ticket in its own worktree, a merger agent, a closing `/code-review`) is adapted from Matt Pocock's `implement-spec`, and its developer brief from his `implement`; `run-retro`'s brief changes follow his `retro`.
- The run briefs load his `tdd`, `code-review`, `resolving-merge-conflicts` and `pr` skills by name.
