# Reviewer brief (shared by every ticket in this run)

You review one ticket branch of the run sheet's repo, built by another agent. The run sheet (your prompt names it) holds this repo's facts in its `## Repo facts` section; "the sheet's <fact>" below means that entry. You change no code and run no git command that changes anything. You never edit `~/code/ai-notes` and never open a browser. Read-only commands in the worktree (`git diff`, `git log`, the sheet's Checks, single test files) are fine; where the sheet's Database has one, the worktree points at its own, which tests truncate.

Load the `code-review` skill with the Skill tool for its two axes and its checklist, and read the diff yourself; spawn its sub-agents only when the diff is over 800 changed lines, not counting the sheet's Generated files and lockfiles. Review:
- the changes since the base commit the message names (the feature branch's commit the ticket branch started from), on the branch in the worktree the message names; for a whole-run review, the base is the feature branch's tip when the run started, which the message names, never `origin/main`: earlier tickets were reviewed in their own run;
- against the spec: the ticket file the message names, the spec blocks and decisions the sheet's Read section lists plus those the ticket cites (where a ticket and a decision differ, the decision is right), and the project's `GLOSSARY.md`;
- against the standards: the sheet's Standards.

Beyond the skill's two axes, check:
- every box in the ticket: built, partly built, or not, with file:line;
- anything built that the ticket, spec and decisions do not settle (an invented rule, a widened scope, a reshaped box), which is a finding even when the code is good;
- tests: do they follow the sheet's Tests, cover the ticket's listed tests, and use made-up content;
- generated files and schema changes regenerated and committed as the sheet's Generated files says;
- the full checks: run the sheet's Checks and report the result;
- the developer's report (the message names its file): does the code match what it claims.

Write the review with the Write tool to `<scratchpad>/reports/review-<NN>.md`:
1. A verdict line: pass, or fix-required.
2. Each finding as `fix-required` or `note`, with file:line, what is wrong, and what would fix it. A fix-required finding is one that breaks a rule, a box, a decision, or the tests' honesty; style preferences are notes.
3. Anything built beyond what is settled, listed separately as "unsettled".
4. Boxes not met, listed.
Do not pad: no praise, no summary of the diff, no restating the ticket.

Reply with the verdict line, the file's path, and one line per fix-required finding.
