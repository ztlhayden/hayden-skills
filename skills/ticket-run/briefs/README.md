# Briefs for an unattended ticket run

The four role briefs an orchestrator hands to worker agents when it builds a project's
`ready-for-agent` tickets in parallel: one developer per ticket in its own worktree, a fresh
reviewer, a browser tester retired every six checks, and a merger. Written for a first run on
a Payload CMS repo, and revised after each later run from its retro (`/run-retro`), which
measures every agent's cost and turns from the transcripts.

The role briefs hold only what is the same for every repo. Each repo's tooling (install,
checks, database, generated files, tests, standards, prototype, browser recipe) lives in the
run sheet's `## Repo facts` section, which the briefs read by entry name; the template
(`~/.claude/skills/run-sheet/run-sheet.template.md`) shows a Payload repo's as a worked
example. Scripts particular to one repo, such as a tester's seed and sign-in scripts, live with
that project's notes, and the sheet's Browser entry names them. The orchestrator copies each brief into its session
scratchpad, fills the angle-bracket slots (`<scratchpad>`, `<NN>`, `<port>`), and names the
file and the run sheet in each agent's prompt. The briefs repeat nothing `~/.claude/CLAUDE.md`
already loads for every agent; machine rules live there.

| File | Who reads it | Model that fitted |
| --- | --- | --- |
| `orchestrator.md` | the orchestrator, started by `/ticket-run <run sheet>`; holds what is the same every run | Fable for the first run; Opus from the second, measured |
| `../../run-sheet/run-sheet.template.md` | `/run-sheet <feature folder>`, once per run, or the user by hand: copied to the notes repo's `sessions/<date>-run-sheet.md` and filled with the repo facts, tickets, lanes, models, seams, scope and sweep | |
| `developer.md` | one agent per ticket | Opus for a custom screen or framework internals; Sonnet for a rule, a field, a migration or a page restyle |
| `reviewer.md` | a fresh agent per ticket branch | Sonnet; Opus for the whole-run review, over the run's range only |
| `merger.md` | a fresh agent per merge; the message may name one check to run after the merge | Sonnet |
| `tester.md` | one agent per six checks, or fewer when a task notification shows it past 150k tokens; a fresh one for the final sweep | Sonnet |

After a run, the parsers in `~/.claude/skills/run-retro/scripts/` give the numbers per agent
and role from the transcripts.
