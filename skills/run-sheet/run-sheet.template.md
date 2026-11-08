# Run sheet: <feature>, <date>

Everything particular to one unattended run; the orchestrator brief
(`~/.claude/skills/ticket-run/briefs/orchestrator.md`) holds the rest. Start the run with
`/ticket-run <this file>`. Copy to the notes repo's `sessions/<date>-run-sheet.md`, fill every
line, delete none.

- **Tickets:** issues in milestone `<project>/<feature>`, or, for a feature not yet moved to issues, the markdown folder `<project>/tickets/<feature>`.
- **Repo:** `<owner/repo>` at `~/code/<owner>/<repo>`.
- **Feature branch:** `<branch>`, worktree `~/code/<owner>/<repo>.<branch>`.
- **PR:** `<owner/repo#n>`, or "open a draft".
- **Desks:** <n>.
- **Report:** `sessions/<date>-<slug>.md`.

## Repo facts

The four role briefs hold only what is the same for every repo and read these entries by
name ("the sheet's Checks"); every agent's prompt names this sheet. An entry that doesn't
apply says "none". The example, in italics, is an invented Next.js shop on Postgres. Copy the
last sheet for the same repo where there is one.

- **Stack:** <one line>. _Example: a Next.js 16 shop on Postgres, its schema in Drizzle._
- **Install:** <command per new worktree; what the merger runs when the lockfile changes>. _Example: `npm ci`, in each worktree and after a merge that changes `package-lock.json`._
- **Checks:** <full set, in order; format fix; one test file; any check that already fails on `main`, its error count, and how agents count it as passing>. _Example: `npm run format:check` (fix with `npm run format`), `npm run lint`, `npm run typecheck`, `npm test`; one file: `npm test -- tests/orders/<file>.test.ts`. The pre-commit hook runs prettier, typecheck and lint._
- **Database:** <none, or: container, one database per worktree and its name, how the worktree points at it, reset command>. _Example: Postgres container `shop-db` (user and password `shop`, port 5432); databases `shop_t<NN>` per developer, `shop_check` for the tester, `shop_<feature>` for the feature worktree; each worktree's `.env` `DATABASE_URL` names its own. Reset: `docker exec shop-db psql -U shop -c 'drop database if exists <db>'`, then `-c 'create database <db>'`. Tests truncate the database they run against._
- **Generated files:** <each file and its regenerate command; migrations; what to do with each, and the lockfile, on a merge conflict>. _Example: `src/db/types.ts` (`npm run generate:types`). A schema change: `npm run generate:types`, then `npm run db:migration <name>`; read the SQL (a rename stays a rename, not a drop and an add) and check it on an empty database; a migration with guards gets a test of its refusal where the harness can seed old-shape rows, otherwise the report says how it was checked. On a conflict take either side of a generated file and regenerate; `package-lock.json`: the feature branch's side, then `npm install`, and commit what it writes. Two migrations from the same base: keep the feature branch's, delete the incoming one and its journal entry, generate it again on the merged code, and compare that it carries exactly the incoming schema change._
- **Developers read:** <README sections, code folders, library docs>. _Example: `README.md` (Orders, Local development, Tests); `src/orders/`, `src/components/admin/`, `tests/orders/` (prior art and helpers), `src/db/types.ts`; the ORM's docs for relations and transactions in `node_modules/drizzle-orm/`._
- **Standards:** <files and sections the reviewer checks against>. _Example: `CODING_STANDARDS.md`, and `README.md`'s Orders section for the rules the code keeps; a README rule the change alters changes in the same commit._
- **Tests:** <the seam tests drive, and their rules>. _Example: the spec's Testing Decisions: drive the app from outside (its route handlers through the test client, signed in as a user the rule refuses), assert the refusal messages, one test per endpoint or per role it refuses; made-up content._
- **Prototype:** <path and how to read it, or none>. _Example: `<project>/notes/<date>-admin-screens-prototype.html`, self-contained; the script at the bottom renders one `render*` function per question: read the one for the ticket's question. The check message names the anchor._
- **Browser:** <README sections to read; session name; start command; sign-in or reader switch; seed; sizes and schemes; per ticket, the pages the tester can't reach (signed in, a role it lacks)>. _Example: README Local development and Orders; session `-s=shop-run`; reset `shop_check`, then `(cd <worktree> && DATABASE_URL=postgres://shop:shop@127.0.0.1:5432/shop_check npm run dev -- -p <port>)`, opened at `http://localhost:<port>/admin` (at `127.0.0.1` Next refuses its own scripts). Seed: `scripts/seed-check.ts` from the worktree with the same `DATABASE_URL` where it exists (prints the admin and customer accounts and each record's admin URL; developers keep it in step with their schema); otherwise create a throwaway first admin (e.g. tester@example.test, kept in `<scratchpad>/tester/accounts.md`) and seed over the API with a copy of a script kept in the project's notes folder, named here. Sign in through the form; for another account sign out, then in, in the same session. Sizes: phone for a small change; all three when layout changed; light scheme only._

## Read, beyond the brief's list

- Tickets: issues <#n, #n, ...>, or the folder's `issues/` <NN, NN, ...>.
- Decisions: `<project>/decisions/<NNNN>`, ...
- Spec blocks: `<project>/tickets/<feature>/spec.md`, "<heading>" (stories <a> to <b>) and its implementation block.

## Blocker walk

Every ticket's blockers walked to the end of the chain (`issues.py survey <milestone>`, `chain
<n>`, `check`; or `check-tickets.py <folder>`), when the sheet was written. The orchestrator
walks them again before the first agent and reports what changed.

- <ticket>: waits on <ticket> (<a person: ready-for-human / an agent: built in this run or elsewhere>). The run: <waits / leaves it out / the user fixes it first>.
- Problems (a blocker with a lower priority than what waits on it, a cycle): <each, and what the user decided>, or "none".

## Lanes

| Lane | Tickets, in order | Model | Blockers outside the lane | Notes |
| --- | --- | --- | --- | --- |
| Phase 0 (optional) | <NN> | Sonnet | | merges before any other branch is cut; no browser check |
| <name> | <NN> → <NN> | <Opus/Sonnet per ticket> | | |

A ticket left `ready-for-human` only for a check by eye: its dependents start <on its merge / once it is closed>.

Longest lane first. Opus for a custom admin screen or framework internals; Sonnet for a rule, a field or a migration.

## Gates

Which checks each ticket passes through, and how its work lands. Each option names its choice; the first is the default, the full set. A lighter choice saves agents, and every agent saved also saves the orchestrator three to five turns. The Lanes table's Notes column marks the tickets an option singles out.

- **Per-ticket review:** <every ticket / marked only>. _Marked only: a ticket marked "review" in Notes gets its own reviewer (mark Opus tickets, and any that set a pattern others copy); the rest go from developer to merger, and the whole-run review covers them. Example: "marked only: 04 and 07"._
- **Browser checks:** <every ticket / screens only>. _Screens only: a ticket whose boxes change no page (a server rule, an import, a refusal its tests pin) gets no per-ticket check, marked "no check" in Notes; the final sweep still opens what it lists._
- **Branches:** <per ticket / per lane>. _Per lane: a lane with more than one ticket is built on one branch, `<feature>-<lane-slug>`, in one worktree, each ticket by its own developer starting from the last one's head; each gets its review and check there, and the lane merges once, when its last ticket passes, or earlier when a ticket in another lane waits on it. A lane of one ticket is per ticket either way._
- **Final sweep:** <all listed / changed since checked>. _Changed since checked: the sweep opens only the listed screens whose code changed after their own check passed (a later merge, a seam, the whole-run fixes), and every seam; the report names the screens it skipped and the check that covered each._

## Seams

- <Ticket A> changes <thing>; <ticket B> reads it. Named check for the second merger: "<what to confirm on the merged code>". The sweep opens <page> on <data>.
- A check that greps names the file it greps, not a folder that holds files outside the run's tickets (a `grep 'confirm(' src/routes/account` also catches `account/history/`, which no ticket changed).

## Out of scope, even if shown as ready

- <tickets or folders>
- <ticket NN> names <other repo> too: build this repo's boxes only; it ends `ready-for-human`.

## Tickets elsewhere that this run unblocks

- Issues: <#n> (from the `blocks:` line of `issues.py chain`), blocked by <#n>. Closing the blocker clears the link; the issue keeps its status, and a comment says it waits on this PR reaching `main`.
- Markdown: <project/feature NN> (from `ticket.py refs`), blocked by <NN>; when they resolve it becomes `ready-for-human — waits on this PR reaching main` (the notes repo's hook refuses a commit that leaves it `blocked`).
- PR: if `gh pr create` is refused, the run goes on and the report asks the user to open it.

## Final sweep

- <screen>, <screen>, <screen>: three sizes.
