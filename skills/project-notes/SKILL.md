---
name: project-notes
description: "Conventions for the private notes repo (~/code/ai-notes) that holds every project's tickets, glossary, decisions and repo map, with scripts to survey, check and close tickets. Use when reading, writing, triaging, building from or closing a ticket; when a skill says to publish to or fetch from the issue tracker; and before recording a glossary term or decision."
---

# Project notes

Each project's notes live in one private notes repo, `~/code/ai-notes`, apart from the code, because one project can span several repos and some of those repos are public. A project's folder there holds its `README.md` (with the repo map), `GLOSSARY.md`, `decisions/` and `tickets/`.

Read the file for what you are doing:

| Doing | Read |
| --- | --- |
| Reading, writing, moving or closing tickets | `issue-tracker.md` |
| Setting or reading a ticket's `Status:` | `triage-labels.md` |
| Turning a ticket `ready-for-agent` | `ticket-checklist.md` |
| Finding a project's folder, glossary or decisions | `domain.md` |
| Building across repos, or a repo fact changes | `repo-map.md` |

The scripts are in `scripts/` (run them from any folder; the notes repo is `$NOTES_ROOT`, or `~/code/ai-notes`):

- `check-tickets.py [--ready | --summary] [folder]`: checks every ticket's `Status:` and `Blocked by:` lines and lists what is ready. Start a survey with `--summary` instead of reading tickets.
- `ticket.py show <ticket or folder>`: tickets with all but the last comment hidden, for surveys only. Read the whole file before working on a ticket.
- `ticket.py refs <ticket or folder>`: the tickets it blocks and the files that link to it, before moving or renaming one.
- `ticket.py set-status`, `ticket.py resolve`, `ticket.py archive`: change a status or close a ticket, moving the file and fixing paths to it.
- `pre-commit`: the notes repo's pre-commit hook.
