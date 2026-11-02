# hayden-skills

Claude Code skills for building a feature's tickets with unattended agent runs, and the conventions they rest on.

| Skill | Started by | What it does |
| --- | --- | --- |
| `project-notes` | Claude, when it works with tickets or project notes | The layout of the private notes repo that holds every project's tickets, glossary, decisions and repo map, with scripts to survey, check and close tickets |
| `run-sheet` | you: `/run-sheet <feature folder>` | Drafts a run's sheet from a feature's `ready-for-agent` tickets: lanes, a model per ticket, seams between lanes, scope, the final sweep |
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

## What the skills expect

- **A private notes repo at `~/code/ai-notes`** (or wherever `NOTES_ROOT` points), apart from the code, because tickets carry private detail and one project can span several repos. One folder per project, holding `README.md` (with its repo map), `GLOSSARY.md`, `decisions/` and `tickets/<feature>/` (`spec.md`, `issues/NN-slug.md`); run sheets and reports go in `sessions/`. `skills/project-notes/` describes each part.
- **The notes repo's pre-commit hook** set to the ticket checker, in its `.githooks/pre-commit`:

  ```sh
  #!/bin/sh
  exec ~/.claude/skills/project-notes/scripts/pre-commit
  ```

  then `git config core.hooksPath .githooks`.
- **A `~/.claude/CLAUDE.md` that points at `project-notes`**, so Matt Pocock's [skills](https://github.com/mattpocock/skills) (`/to-tickets`, `/triage`, `/implement`, `/domain-modeling`) put tickets and decisions in the notes repo. For example:

  ```markdown
  ### Issue tracker
  Local markdown tickets under `~/code/ai-notes/<project>/tickets/`. See `~/.claude/skills/project-notes/issue-tracker.md`.
  ### Triage labels
  See `~/.claude/skills/project-notes/triage-labels.md`.
  ### Domain docs
  See `~/.claude/skills/project-notes/domain.md`.
  ```

- **`playwright-cli`** for the browser tester, and git worktrees for the developers. The run sheet's Repo facts say how to install, check and seed each repo.

Python 3.10 or later runs the scripts; they need nothing beyond the standard library.
