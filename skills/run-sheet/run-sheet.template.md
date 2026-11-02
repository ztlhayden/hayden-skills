# Run sheet: <feature>, <date>

Everything particular to one unattended run; the orchestrator brief
(`~/.claude/skills/ticket-run/briefs/orchestrator.md`) holds the rest. Start the run with
`/ticket-run <this file>`. Copy to the notes repo's `sessions/<date>-run-sheet.md`, fill every
line, delete none.

- **Repo:** `<owner/repo>` at `~/code/<owner>/<repo>`.
- **Feature branch:** `<branch>`, worktree `~/code/<owner>/<repo>.<branch>`.
- **PR:** `<owner/repo#n>`, or "open a draft".
- **Desks:** <n>.
- **Report:** `sessions/<date>-<slug>.md`.

## Repo facts

The four role briefs hold only what is the same for every repo and read these entries by
name ("the sheet's Checks"); every agent's prompt names this sheet. An entry that doesn't
apply says "none". The example, in italics, is a Payload CMS repo's
([`Indy-Center/payload`](https://github.com/Indy-Center/payload)); its paths into the notes
repo are that project's. Copy the last sheet for the same repo where there is one.

- **Stack:** <one line>. _Payload: the Indy Center CMS, Payload CMS 3.90, Next.js 16, Postgres._
- **Install:** <command per new worktree; what the merger runs when the lockfile changes>. _Payload: `npm ci`, in each worktree and after a merge that changes `package-lock.json`._
- **Checks:** <full set, in order; format fix; one test file; any check that already fails on `main`, its error count, and how agents count it as passing>. _Payload: `npm run format:check` (fix with `npm run format`), `npm run lint`, `npm run typecheck`, `npm test`; one file: `npm test -- tests/int/courseware/<file>.int.spec.ts`. The pre-commit hook runs prettier, typecheck and lint._
- **Database:** <none, or: container, one database per worktree and its name, how the worktree points at it, reset command>. _Payload: Postgres container `payload-db` (user and password `payload`, port 5432); databases `payload_t<NN>` per developer, `payload_check` for the tester, `payload_<feature>` for the feature worktree; each worktree's `.env` `DATABASE_URL` names its own. Reset: `docker exec payload-db psql -U payload -c 'drop database if exists <db>'`, then `-c 'create database <db>'`. Tests truncate the database they run against._
- **Generated files:** <each file and its regenerate command; migrations; what to do with each, and the lockfile, on a merge conflict>. _Payload: `src/payload-types.ts` (`npm run generate:types`); `src/app/(payload)/admin/importMap.js` (`npm run generate:importmap`, after registering an admin component by path). A schema change: `npm run generate:types`, then `npm run payload migrate:create <name>` (a rename or a dropped column stops at a prompt that `-- --forceAcceptWarning` skips; read the SQL: a rename stays a rename); check it on an empty database (drop the schema, `npm run payload migrate`); a migration with guards gets a test of its refusal where the harness can seed old-shape rows, otherwise the report says how it was checked. On a conflict take either side of a generated file and regenerate; `package-lock.json`: the feature branch's side, then `npm install`, and commit what it writes. Two migrations from the same base: keep the feature branch's, delete the incoming one (`.ts`, `.json`, its line in `src/migrations/index.ts`), `migrate:create` on the merged code, and compare that it carries exactly the incoming schema change._
- **Developers read:** <README sections, code folders, library docs>. _Payload: `README.md` (Courseware, Local development, Tests); `src/collections/courseware/`, `src/courseware/`, `src/components/admin/`, `tests/int/courseware/` (prior art and helpers), `src/payload-types.ts`; Payload's docs for admin components, views, list views, joins, drawers and endpoints in `node_modules/payload/` and `node_modules/@payloadcms/ui/`._
- **Standards:** <files and sections the reviewer checks against>. _Payload: `CODING_STANDARDS.md`, and `README.md`'s Courseware section for the rules the code keeps; a README rule the change alters changes in the same commit._
- **Tests:** <the seam tests drive, and their rules>. _Payload: the spec's Testing Decisions: drive the CMS from outside (the Local API as a signed-in user with `overrideAccess: false`, or the endpoints through `callEndpoint`), assert refusal messages from `error.data.errors`, one test per endpoint or read as a user it refuses; made-up content._
- **Prototype:** <path and how to read it, or none>. _Payload: `courseware/notes/2026-10-26-cms-screens-prototype.html`, self-contained; the script at the bottom renders one `render*` function per question: read the one for the ticket's question. The check message names the anchor._
- **Browser:** <README sections to read; session name; start command; sign-in or reader switch; seed; sizes and schemes; per ticket, the pages the tester can't reach (signed in, a role it lacks)>. _Payload: README Local development and Courseware; session `-s=payload-run`; reset `payload_check`, then `(cd <worktree> && DATABASE_URL=postgres://payload:payload@127.0.0.1:5432/payload_check npm run dev -- -p <port>)`, opened at `http://localhost:<port>/admin` (at `127.0.0.1` Next refuses its own scripts). Seed: `scripts/seed-check.ts` from the worktree with the same `DATABASE_URL` where it exists (prints the admin, lead and author accounts and each record's admin URL; developers keep it in step with their schema); otherwise create a throwaway first admin (e.g. tester@example.test, kept in `<scratchpad>/tester/accounts.md`), give it `training:admin`, and seed over the REST API with a copy of `~/code/ai-notes/payload/tester-scripts/seed.mjs` (`Authorization: JWT <token>` from `POST /api/users/login`). Sign in with a copy of its `login.sh <port> <email> <password>`; for another account sign out, then in, in the same session. Sizes: phone for a small change; all three when layout changed; light scheme only._

## Read, beyond the brief's list

- Tickets: `<project>/tickets/<feature>/issues/` <NN, NN, ...>.
- Decisions: `<project>/decisions/<NNNN>`, ...
- Spec blocks: `<project>/tickets/<feature>/spec.md`, "<heading>" (stories <a> to <b>) and its implementation block.

## Lanes

| Lane | Tickets, in order | Model | Blockers outside the lane | Notes |
| --- | --- | --- | --- | --- |
| Phase 0 (optional) | <NN> | Sonnet | | merges before any other branch is cut; no browser check |
| <name> | <NN> → <NN> | <Opus/Sonnet per ticket> | | |

A ticket left `ready-for-human` only for a check by eye: its dependents start <on its merge / once it is resolved>.

Longest lane first. Opus for a custom admin screen or framework internals; Sonnet for a rule, a field or a migration.

## Seams

- <Ticket A> changes <thing>; <ticket B> reads it. Named check for the second merger: "<what to confirm on the merged code>". The sweep opens <page> on <data>.
- A check that greps names the file it greps, not a folder that holds files outside the run's tickets (2026-10-31: `grep 'confirm(' src/routes/teach` also caught `teach/report/[id]`, which no ticket changed).

## Out of scope, even if shown as ready

- <tickets or folders>
- <ticket NN> names <other repo> too: build its payload boxes only; it ends `ready-for-human`.

## Tickets elsewhere that this run unblocks

- <project/feature NN> (from `ticket.py refs`): blocked by <NN>; when they resolve it becomes `ready-for-human — waits on this PR reaching main` (the ai-notes hook refuses a commit that leaves it `blocked`).
- PR: if `gh pr create` is refused, the run goes on and the report asks the user to open it.

## Final sweep

- <screen>, <screen>, <screen>: three sizes.
