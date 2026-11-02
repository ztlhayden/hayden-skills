# Triage labels

Tickets are local files, so a label is the value of the ticket's `Status:`
line.

| Role in the skills | Status value      | Meaning                                  |
| ------------------ | ----------------- | ---------------------------------------- |
| `needs-triage`     | `needs-triage`    | Maintainer needs to evaluate this ticket |
| `needs-info`       | `needs-info`      | Waiting for more information             |
| `ready-for-agent`  | `ready-for-agent` | Fully specified, ready for an AFK agent  |
| `ready-for-human`  | `ready-for-human` | Needs a person to do it                  |
| `wontfix`          | `wontfix`         | Will not be done                         |
| —                  | `blocked`         | Specified, waiting on its `Blocked by:` tickets |
| —                  | `resolved`        | Done                                     |

`blocked` and `resolved` are this tracker's own states, outside the skills'
roles:

- **blocked**: a ticket starts `blocked` when any ticket in its `Blocked by:`
  line is open (the default for `/to-tickets` output with blockers). Once
  every blocker is `resolved`, move it to `ready-for-agent` or
  `ready-for-human`; it was specified already, so it skips triage.
- **resolved**: the work is done or the decision recorded. Add where it
  landed after a dash: `resolved — merged to main, PR Org/repo#12`.
- A ticket whose work is built but waits on the user's decision or marks is
  `ready-for-human`.
