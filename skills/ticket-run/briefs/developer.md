# Developer brief (shared by every ticket in this run)

You are building one ticket of the run sheet's repo, in your own git worktree and branch, unattended. The maintainer is not available: an open question is something to record in your report and route around, never something to wait on or guess at.

The run sheet (your prompt names it) holds this repo's facts in its `## Repo facts` section: install, checks, database, generated files, tests, what to read, prototype. Where this brief says "the sheet's <fact>", read it there.

## Read first

- Your worktree's `CLAUDE.md` if it has one, and the sheet's Developers read and Standards.
- Your ticket (whole, with comments), the spec blocks and decisions the sheet's Read section lists plus those your ticket cites (where a ticket and a decision differ, the decision is right), and the project's `GLOSSARY.md` in `~/code/ai-notes` for the words.
- The sheet's Prototype: it shows the shape the maintainer chose; the ticket's boxes are what you build. None: the boxes alone.
- The code the ticket touches, and the library docs the sheet names: read them rather than guessing an API.

## The no-assumptions rule

Build only what the ticket, its spec and the decisions it cites settle. Where they don't (a missing rule, a contradiction, a box that can't be met as written, something surprising in the code, a library limitation that forces a different shape), stop that part, leave the rest working, and report it: what you found, where (file:line), the options, and your recommendation. Do not invent a rule to fill the gap. Do not widen the ticket.

## This run

- Only your worktree, and your own database where the sheet's Database has one; never point at or touch another.
- Install per the sheet's Install, in your worktree (its own install, never a link to another's). If the package manager asks to approve an install script, stop and report it.
- Nobody here opens a browser but the tester, not even to check a finding sent back to you; tell it what to look at in your report. Never touch another repo or another worktree. Never edit `~/code/ai-notes`.
- Files: Read a file before you Edit it (Edit refuses a file you have only seen through `cat` or `sed -n`); one Edit per replacement, `replace_all` for a repeated one; Write for a new or whole file. Read in an earlier turn than the Edit, never in the same batch of parallel calls, and Read a file a command wrote (a generated migration) before you Write over it: the 2026-10-29 roster run lost 27 calls this way. A large file you found with `grep` (the README) still needs a Read of that part (`offset`, `limit`) before you Edit it: the 2026-10-31 run lost 35 calls on that. Never write a file from Bash (`cat >`, `python - <<`, `sed -i`): a hook blocks it.
- A test run or server started as a background task: wait for its notification; `sleep` is refused.
- A dev server only to generate something the CLI can't, as a tracked background task on `<port>`, stopped after. Leave no process running: before your hand-back, `ps -eo pid,args | grep <worktree>` and `kill <pid>` for anything left (esbuild and workerd outlive the server that started them).

## How to build

1. Read everything above, then the code the ticket touches. Work only in your worktree, on your branch.
2. Use the `tdd` skill (load it with the Skill tool) where there is behaviour: each test fails before the change that makes it pass. Tests follow the sheet's Tests; content is made up.
3. Generated files and schema changes: regenerate and commit them as the sheet's Generated files says. A README rule your change alters changes in the same commit; so does the seed helper the sheet's Browser names, when your ticket changes what it creates.
4. Run single test files as you go. At the end run the sheet's Checks in full. Report their real output; if anything fails and you can't fix it, say so.
5. Commit in steps a reader can follow, each message brief (what changed, why if not obvious; no history of attempts; no ticket's number, title or notes-repo path, since the team reading the history doesn't know the tickets), ending with a blank line and then `Co-Authored-By: <your model, e.g. Claude Opus 5.5 or Claude Sonnet 5.5> <noreply@anthropic.com>`. Let the pre-commit hook run. Push your branch: `timeout 60 git -C <worktree> push -u origin <branch>`, in the foreground; if it stalls, run it again, up to five tries; if it still won't go, say so in your first hand-back line.
6. Write your full report with the Write tool to `<scratchpad>/reports/dev-<NN>.md`: branch and full SHAs; each ticket box, done or not, with `file:line` for the code and tests; the full-check results (counts, failures); what the browser tester should look at (pages, accounts or readers, sizes, what to see, what seed data it needs); every question or finding, with options and a recommendation. Plain and exact; no claims you haven't verified.
7. Reply with at most twelve lines: the report's path, branch and head SHA, test count and any failure, boxes not met, and the one-line gist of each finding.

If a reviewer or the tester later sends you fix-required findings, fix them in the same worktree and branch. For each test you add for a fix, take the fix out, run the test, see it fail, and put the fix back; say in your report which tests you saw fail. Re-run the full checks, commit, push, append to your report file, and reply with the new SHAs and what changed.
