# Repo maps

A project's notes live in the notes repo, apart from its code, because one project can span
several repos and some of those repos are public. From inside one repo an agent
cannot see where the rest of the work belongs. The **repo map** says.

## What the map is

A table in the project folder's `README.md`, one row per repo:

| Column | Holds |
| --- | --- |
| Codebase | GitHub name and local path |
| Role | What the repo is for, in one line |
| Where work lands | The branch, whether agents may push it, and whether a push deploys |
| Tooling | Package manager, and anything the tests need (a database container) |
| Its own notes | The repo's `CODING_STANDARDS.md`, README, or a notes folder |

For example:

| Codebase | Role | Where work lands | Tooling | Its own notes |
| --- | --- | --- | --- | --- |
| `acme/cms` at `~/code/acme/cms` | The CMS editors write lessons in | Feature branch, PR to `main`; `main` deploys | npm; Postgres container for tests | `CODING_STANDARDS.md` |
| `acme/library` at `~/code/acme/library` | Serves published lessons to readers | Agents may push `main`; a push deploys | pnpm | README |

## Keep it true

The map is only useful while it is current. In the session where a fact in it
changes (a repo is created or renamed, a branch merges, the user changes a push
rule, a deploy target moves), update the row and push the notes repo. When you read
a project README and find a line that is no longer true (a status, a "not built
yet", a rule that has served its purpose), correct the facts and tell the user
about the rules: rules are theirs to retire.

## Before building

Before `/implement`, `/implement-spec`, or any change that spans repos, settle
for every ticket and every repo it touches:

- **Repo**: the ticket's `Repo:` line.
- **Branch**: where the work lands, and whether you may push it.
- **Scope**: which tickets are in, and which the user has said to skip.

Take each from the user's command first, then the map, then the ticket. If any
is still open, or the command and the map disagree, ask before writing code:
one round, listing each open point with the default you would pick.

A subagent can't stop to ask, so its prompt names every repo it may read:
the ticket's `Repo:` line, plus any the ticket or its spec sends it to.
