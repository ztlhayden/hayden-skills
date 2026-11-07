# Triage labels

A ticket's triage state is its `status:` label on the issue: exactly one per
open issue. `issues.py claim`, `release` and `close` change it; otherwise swap
it with `gh issue edit --remove-label --add-label`, then `issues.py board <n>`.

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

## Markdown tickets

Markdown tickets (archived features, and any not yet moved) keep the state as
a `Status:` line's value: the same roles without the `status:` prefix, plus
`blocked` (any ticket in its `Blocked by:` line is open) and `resolved` (done,
with where it landed after a dash: `resolved — merged to main, PR
owner/repo#12`).
