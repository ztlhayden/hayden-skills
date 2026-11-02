# Domain docs

Glossaries and decision records live in the notes repo, `~/code/ai-notes`, one
folder per project, never in the code repos.

## Which folder

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

## Use the glossary's vocabulary

When your output names a domain concept (a ticket title, a test name, a
proposal), use the term as `GLOSSARY.md` defines it, and not a synonym it lists
under _Avoid_. If the concept you need isn't there, either you're inventing
language the project doesn't use, or there is a real gap to note for
`/domain-modeling`.

## Flag decision conflicts

If your output contradicts a decision, say so rather than silently overriding:

> _Contradicts courseware 0028 (advancing needs the minimum), but worth reopening because…_

where `courseware` is the project folder and `0028` the decision's number.
