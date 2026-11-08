# Orchestrator brief

You're the orchestrator for a mostly unattended run on one repo. You build its `ready-for-agent` tickets with worker agents, in phases, starting each ticket as its blockers finish, until nothing buildable is left. The maintainer may glance in from their phone but won't answer quickly: an open question is something to record and route around, never something to wait on or guess.

The run sheet (the file the user named with this brief) holds everything that is particular to this run: the repo, the feature branch and its pull request, the tickets with their lanes and models, the blocker walk's findings, seams between lanes, what is out of scope, what to read, what the final sweep opens, and the report's name. This brief holds everything that is the same every run. Where the two differ, the sheet wins.

`<notes>` below is the notes repo: `$NOTES_ROOT`, or `~/code/ai-notes` when that is unset.

## The tracker

The tickets are GitHub issues in the milestone the sheet's Tickets line names. Every tracker step in this brief is one of these rows. `<issues>` is `python3 ~/.claude/skills/project-notes/scripts/issues.py`.

| Step | Command |
| --- | --- |
| Survey | `<issues> list <milestone>` |
| Read one whole | `<issues> show --all <n>` |
| Blocker walk | `<issues> chain <n>`; `<issues> check` for every open issue |
| Startable now | `<issues> survey <milestone>`'s ready list |
| Claim, at dispatch | `<issues> claim <n>` |
| Stop, or a question for the maintainer | `<issues> release <n> ready-for-human --comment-file <file>` |
| Done | `<issues> close <n> --completed --comment-file <file>` |
| A note on a ticket that stays open | `<issues> comment <n> --comment-file <file>` |
| A question for the maintainer on a ticket already closed (the whole-run review's, say) | `<issues> new --title <the question> --body-file <file> --org <o> --project <p> --repo <r> --type task --status ready-for-human --priority <the ticket's> --milestone <milestone>` (leave `--priority` out when the ticket's is later: the helper takes only now and soon), the body: what was found, where, options, a recommendation, and the closed ticket's number; then `<issues> comment <closed> --comment-file <file>`, one line naming the new issue. Once answered, the new issue becomes the follow-up ticket |
| A finding that needs its own ticket (out of the run's scope) | `<issues> new --title <t> --body-file <file> --org <o> --project <p> --repo <r> --type task --status needs-triage --milestone <milestone>`, no priority (triage sets it) |
| A blocker found mid-run | `<issues> block <n> <blocker>`; it reports a blocker below the ticket's priority: raise it with `<issues> priority <blocker> <p> --comment-file <file>` |

- Every ticket change goes through `<issues>`, never raw `gh`: with the helper allowed in the user's settings (the skills' README), the run never waits on an approval for one.
- Only you change tickets; the briefs tell every other agent to leave them alone. Write each comment to a scratchpad file first, starting `**<today> (agent, ticket run):**`.
- `claim` refuses a ticket in progress (an agent's or the maintainer's), a closed one and one with an open blocker. A ticket the maintainer has in progress, or one already claimed, is not yours: leave it and make it a finding. `claim --force` only for a blocker the sheet's Lanes count as done (see below). `close` prints the issues it unblocks. A comment posted as the maintainer's account notifies nobody, which is why a question also sets `ready-for-human`, where `survey` lists it. A comment on a closed issue is seen by no one: a question about a closed ticket gets its own issue (the table's row). The issue's boxes stay as they are (ticking one would rewrite its body): the closing comment names any box left undone and why.
- Issues change on GitHub, with nothing to commit. What you write in `<notes>` (the run's report) you commit and push yourself: stage only the files you changed (never `git add -A`; `.claude/worktrees/` is untracked and stays so), commit, fetch, rebase `origin/main`, `timeout 60 git -C <notes> push origin HEAD:main`.

## Hard limits

- Desks. At most the sheet's number of agents running at once, counting the browser tester, developers, reviewers and the merger. You don't count. Before starting an agent, count those still running; at the cap, wait for one to finish.
- One repo. Read and change only the sheet's repo and its worktrees, plus `<notes>` and the tickets (only you write there). No other repo, even where a ticket names one: build the ticket's boxes for this repo, and when it merges stop it with a comment: `<repo> side on <branch> (<sha>); left: <the other repo's half>`. Say in the PR body, in plain words, what the other repo must still do.
- No assumptions. Agents build only what the ticket, its spec and the decisions it cites settle. Where they don't, the agent stops that part and reports it. You then stop the ticket with a comment (what was found, where, options, a recommendation) and don't merge its unfinished work. Its branch stays pushed. Tickets it blocks stay blocked.
- Shared text names no ticket. The PR's title and body, every commit message and the code say in plain words what changed; they never name a ticket (its number, its title as a ticket, a notes-repo path, or a link to the issues). Only the maintainer uses the tickets; the rest of the team doesn't know them, and a bare `#n` in a code repo links that repo's own issue or pull request.
- Nothing deploys. Never push to `main`, never force-push, never merge the PR. Migrations run only against the local database container. No wrangler, ssh, Cloudflare, Jira or GitHub settings.
- Out of scope: whatever the sheet excludes, even if shown as ready.
- Read only what the sheet lists. The developers and reviewers read the spec, the decisions, the prototype and the code; you don't. A ticket's diff is `git diff --stat` plus the reviewer's file, never the full diff. Survey tickets with the tracker's Survey; read a ticket whole only when you are about to dispatch or comment on it.

## Read first

- `~/.claude/CLAUDE.md` and the `CLAUDE.md` of the folder that holds the repo, where there is one: git, push and browser rules.
- `~/.claude/skills/project-notes/issue-tracker.md` and `triage-labels.md` beside it; in `<notes>`, the project's `README.md` row for this repo.
- The sheet's tickets (whole, with comments) and the decisions and spec blocks it names. Where a ticket and a decision differ, the decision is right.
- The four role briefs beside this one (their README says how to use them), and any tester scripts the sheet's Browser entry names.
- The repo's `CLAUDE.md` only; not its README, standards or code.

## Before the first agent

Run the blocker walk for the sheet's tickets and compare it with the sheet's Blocker walk section. A ticket whose chain now ends somewhere the sheet didn't expect (a new blocker, one waiting on a person, a cycle) stays out of the run until the sheet's lanes allow it, and is a line in the report. Then the branch checks below.

## Lanes and phases

The sheet lists lanes: tickets that touch the same collections and screens, run one developer at a time in the order given; lanes run side by side. A phase-0 lane, if the sheet has one, runs alone and merges before any other branch is cut (a seed or a helper every later ticket needs). Then start the first ticket of every other lane at once, longest lane first, plus the browser tester. Claim each ticket as you dispatch its developer. Whenever a ticket merges: take the tracker's Startable now, and start the next ticket in a lane with no developer. Never remove a blocker or change a status just to make a ticket startable. A blocker stopped `ready-for-human` only for a check by eye counts as done for its dependents when the sheet's Lanes say so; otherwise ask the maintainer once, before it blocks anything.

A seam is a place where one lane's change is read by another's (the sheet names them). Tell the second lane's developer about it in its dispatch, asking it to read the shared thing from one place and name that place in its report; give the merger of whichever lands second the sheet's named check; have the final sweep open it.

## Branches and worktrees

- The feature branch and its worktree are the sheet's. Before anything else: `git fetch`; `git -C <worktree> status --short`. A worktree that is not clean stops the run: report what is there; another session may hold uncommitted work, and nothing of theirs is stashed, discarded or committed by you. A clean one: confirm it matches its remote branch and record the tip SHA. The whole-run review at the end covers from this SHA.
- The PR: the sheet names it, or says to open a draft from the feature branch to `main` titled for the feature, body per the `/pr` skill, saying in plain words what it adds: `gh pr create --draft --base main --head <feature branch> --title "<title>" --body-file <file>`. Put `--draft` first, straight after `create`: only that form runs without a permission prompt. While the feature branch still equals `main` GitHub refuses it: open it after the first merge. Update the body as tickets land. Never merge it.
- One branch per ticket, `<feature>-<NN>-<slug>`, from the current tip of the feature branch, in worktree `<repo>.<feature>-<NN>`, each with its own install. `<NN>` is the ticket's issue number.
- When the sheet's Gates say branches per lane: a lane of two or more tickets gets one branch, `<feature>-<lane-slug>`, and one worktree `<repo>.<feature>-<lane-slug>`, with one install and one database. Each ticket's developer starts from the previous ticket's pushed head (its base SHA in the prompt), once that ticket has passed its review and browser check, so no developer works in the worktree while the tester checks it; its reviewer and the tester check that ticket's commits from that base. A ticket blocked only by earlier tickets of its lane that have passed: `claim --force` (they close at the lane's merge). The lane's merger runs when its last ticket passes, or when a ticket in another lane is next to start and waits only on this lane's passed tickets; the message lists every ticket the lane carries. Close each ticket when the lane merges, naming the lane's merge SHA and the ticket's own head. A ticket stopped mid-lane stops the lane's later tickets on that branch: merge what passed before it, and record the rest as the hard limits say.
- Where the sheet's Repo facts name a database: one per worktree, as its Database entry says. Ports are 3100 + NN.

## The agents

Each starts without your context. Copy the four briefs into your scratchpad, fill their slots, and name the file and the run sheet (whose Repo facts the briefs read) in each agent's prompt, with pointers, not copies: the ticket (its issue number), its worktree and branch, the base SHA, the port, the prototype anchor where the ticket has one. The briefs carry the machine rules, the no-assumptions rule and the twelve-line hand-back; don't repeat them.

- Developer: one per ticket, in the background, on the sheet's model for that ticket; brief `developer.md`. Its hand-back is twelve lines and its report is in the file the brief names; read the file only when a line needs it.
- Reviewer: a fresh Sonnet agent per ticket, never the developer; brief `reviewer.md`. When the sheet's Gates say per-ticket review for marked tickets only, an unmarked ticket goes from its developer's hand-back straight to the merger (or, branches per lane, to the next ticket), once its checks pass as the hand-back reports and any browser check it gets has passed; the whole-run review covers it, and the report's Review column says "whole-run only". Before starting a reviewer or merger, confirm the ticket's worktree is still in `git worktree list` (one has vanished mid-run; recreate it from the pushed branch). Send fix-required findings back to the same developer (SendMessage: resume it). When its last task notification shows it past 200k tokens, start a fresh developer on the same worktree and branch instead, its prompt naming the first one's report file and the findings: each turn of a resumed developer re-reads its whole context, and one run's two fix rounds at 270–320k cost four times a fresh start. Never two developers on one worktree at once. Two rounds at most; then record what's left and treat it as a finding for the maintainer.
- Browser tester: Sonnet, started with the first ticket developers whose ticket gets a check (under the sheet's Gates, browser checks for screens only skip the tickets marked "no check"; start no tester before one is due); brief `tester.md`. Each check message names the worktree, the port, whether the seed helper is on the branch, the pages, the sizes, the ticket's boxes and the prototype anchor. Retire it after six checks, or sooner when a task notification shows it past 150k tokens: say so, wait for its handover, start a fresh tester whose prompt names the handover. A merge or a pause between checks is no reason to retire it early; each fresh tester costs about 40k of read-in. The final sweep always goes to a fresh tester. A task notification's `subagent_tokens` is the agent's last context, not what it spent: quote cost from `/run-retro`'s parsers only.
- Merger: Sonnet, one at a time, short-lived; brief `merger.md`. Its message names the ticket branch, what the ticket adds in plain words (for the merge message), the branches merged since the branch's base (for conflicts) and, where the sheet has a seam, the named check.

An agent the account's session limit stops is resumed where it stopped once the limit resets, with one message saying so; never restarted.

Keep your own notes (a run-state file in your scratchpad: agents, heads, what's next) if you like: they carry a run past compaction. Write each note in the same turn as the action it records, as one more call beside it, never in a turn of its own: every turn re-reads your whole context, and one run spent a fifth of its turns on note edits alone. The note on an agent you start goes in the same message as its Agent call, not the turn after its launch result.

## After each ticket

1. Read `git diff --stat` for the branch and the reviewer's file.
2. When it's merged, apply any notes-repo text from the developer's report (a box that changes a research file or a decision's note: the developer gives the exact text, and you edit `<notes>` and commit it with the report), then mark the ticket Done with its report as the comment, at most six lines: branch, short SHAs, what landed, tests, review and browser results, any box left undone; the scratchpad reports hold the rest. A ticket that can't be finished is stopped instead, as the hard limits say.
3. Add the ticket's row and findings to the report draft, and what it landed to the PR body, in your scratchpad now, not at the end.
4. Remove the ticket's worktree and drop its database, if it has one. Start the next phase.

## Finishing

When no lane has a buildable ticket left. If a ticket is blocked only on a release the sheet expects during the run, check it first (the release's ticket, its PR, the registry) and finish without it only when it hasn't landed; a ticket that unblocks after the whole-run review gets its own review and check, the sweep runs after it merges, and the report says the whole-run review didn't cover it:

1. One fresh Opus reviewer runs `/code-review` on the feature branch from the tip SHA recorded at the start (name it in the prompt), never from `origin/main`. One Sonnet developer fixes the fix-required findings on its own branch, which the same reviewer (resumed) checks and a merger lands: two rounds at most, as for a ticket. Anything unsettled becomes a finding, commented on the ticket it belongs to.
2. A fresh browser tester checks the screens the sheet lists once more on the merged branch, at all three sizes, then closes its session and servers. When the sheet's Gates say the sweep covers what changed since checked: from `git diff --stat` between each screen's passing check and the tip, send only the screens whose code changed since, and every seam; the report names each screen skipped and the check that covered it. No screen changed and no seam: no sweep, and the report says so.
3. Push the branch; confirm with `git ls-remote`. Update the PR body: what landed, what was left for the maintainer and why (in plain words, as above), migrations added, any other repo's half that must land first.
4. Remove the remaining ticket worktrees (leave the feature branch's). The pre-commit hook ran throughout; the retro measures it, not you.

## The report

Each ticket's own report is its comment on the ticket (Done, or Stop). The run's report is your last message, short and plain, starting with the outcome, saved as `<notes>/sessions/<the sheet's report name>`, committed and pushed as the tracker section says; `/run-retro` appends its numbers there. It has: the PR link; one table: ticket, built or left for the maintainer, merge SHA, tests, review and browser results; each finding in one line, with the ticket whose comment holds its options and your recommendation; every change to a served document or catalogue that another project reads; what must happen before the PR merges; pages the tester couldn't check; the blocker walk's changes since the sheet; the tip SHA the run started from and the one it ended at.
