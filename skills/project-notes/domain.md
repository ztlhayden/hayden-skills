# Domain docs

Glossaries and decision records live in the notes repo, `$NOTES_ROOT`
(default `~/code/ai-notes`), one folder per project, never in the code repos.

## Which folder

- An issue's `project:` label names it, and so does its milestone's first
  part (`shop/checkout`).
- The project's own `CLAUDE.md` usually names it.
- Each repo normally has its own folder. A feature that spans several repos
  is the exception and gets one folder of its own.
- The notes repo's own `README.md` may list exceptions (a subject that uses
  one folder whichever repo the work is in); they win over the line above.
- If no folder fits, ask before creating one.

## Before exploring, read these

- The folder's `README.md`.
- Its `GLOSSARY.md`, if it has one.
- Its `decisions/` that touch the area you are working in.

If a file doesn't exist, proceed silently. `/domain-modeling` creates glossary
entries and decisions as they are settled, in the project's folder.
Decisions are numbered and append-only.

## Using them

Follow the consumer rules in Matt Pocock's
[`domain.md`](https://github.com/mattpocock/skills/blob/main/skills/engineering/setup-matt-pocock-skills/domain.md)
(use the glossary's vocabulary, flag a conflict with a decision), reading the project folder's `GLOSSARY.md` for his
`CONTEXT.md` and its `decisions/` for his `docs/adr/`. Name a decision as
`<project folder> <number>` (`shop 0012`).
