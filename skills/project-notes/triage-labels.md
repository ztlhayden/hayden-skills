# Triage labels

A ticket's triage state is its `status:` label on the issue: exactly one per
open issue. `issues.py claim`, `release` and `close` change it; at triage, `issues.py
status <n> <status>` (it keeps the board in step).

The five roles on the left are the ones Matt Pocock's skills speak in; this
table is the mapping his `setup-matt-pocock-skills` template asks for.

| Role in the skills | Label                      | Meaning                                  |
| ------------------ | -------------------------- | ---------------------------------------- |
| `needs-triage`     | `status:needs-triage`      | Maintainer needs to evaluate this ticket |
| `needs-info`       | `status:needs-info`        | Waiting for more information             |
| `ready-for-agent`  | `status:ready-for-agent`   | Fully specified, ready for an AFK agent  |
| `ready-for-human`  | `status:ready-for-human`   | Needs a person to do it                  |
| `wontfix`          | closed as not planned      | Will not be done                         |
| —                  | `status:in-progress-agent` | An agent is working on it                |
| —                  | `status:in-progress-me`    | The maintainer is working on it          |
| —                  | *blocked by* link          | Specified, waiting on other issues       |
| —                  | closed as completed        | Done                                     |

Outside the skills' roles:

- **In progress** replaces the ready label while the work runs; the issue
  goes back to the status the work left it in. Leave an issue already in
  progress alone.
- **Blocked** is not a status. Give a blocked issue the status it takes once
  unblocked; it was specified already, so it skips triage when its blockers
  close.
- **Done**: the closing comment says where the work landed (branch, commits,
  PR `owner/repo#12`).
- A ticket whose work is built but waits on the user's decision or marks is
  `ready-for-human`.
