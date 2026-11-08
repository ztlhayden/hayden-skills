---
name: project-notes
description: "Conventions for the private notes repo ($NOTES_ROOT, default ~/code/ai-notes) that holds every project's specs, glossary, decisions and repo map, with its tickets as GitHub issues and scripts to survey, claim and close them. Use when reading, writing, triaging, building from or closing a ticket; when a skill says to publish to or fetch from the issue tracker; and before recording a glossary term or decision."
---

# Project notes

Each project's notes live in one private notes repo, `$NOTES_ROOT` (default `~/code/ai-notes`), apart from the code, because one project can span several repos and some of those repos are public. A project's folder there holds its `README.md` (with the repo map), `GLOSSARY.md`, `decisions/` and `specs/<feature>/spec.md`. The tickets are GitHub issues on the repo that the notes repo's `project-notes.json` names.

Read the file for what you are doing:

| Doing | Read |
| --- | --- |
| Reading, writing, claiming or closing tickets; triage and priority | `issue-tracker.md` |
| Setting or reading a ticket's status | `triage-labels.md` |
| Turning a ticket `ready-for-agent` | `ticket-checklist.md` |
| Finding a project's folder, glossary or decisions | `domain.md` |
| Building across repos, or a repo fact changes | `repo-map.md` |

The scripts are in `scripts/`; run them from any folder. Each one's docstring is its manual.

- `issues.py`: the issues, through `gh`: `survey`, `list`, `show`, `chain`, `check`, `claim`, `release`, `comment`, `close`, `board`, `start-here`. Start a survey with `issues.py survey` instead of reading issues.
- `issues-snapshot.py`: writes every issue to `issues/snapshot.json`, for the nightly Action.
