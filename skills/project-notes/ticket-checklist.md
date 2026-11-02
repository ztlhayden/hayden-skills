# Ticket checklist: what a ticket settles before it is `ready-for-agent`

An unattended developer stops and reports where the ticket, its spec and its decisions
leave a gap. Each gap costs a round trip through the maintainer (`ready-for-human`) or a
finding to decide later. One early run left twelve findings for the maintainer; most were one
of the shapes below. Pass every ticket through this list when writing it, and again when
turning it `ready-for-agent`.

1. **Every count or list says what it counts.** Direct children or all descendants; retired
   rows in or out; which edition's rows (the live one, the draft, both).
2. **Every new or changed field says whether it is served**, and in which document or
   catalogue, with its shape; or says it is not served.
3. **Every refusal names its message** and who gets it; where two rules can refuse the same
   action, which message wins.
4. **A box that depends on another ticket in the same run** names it, and says which builds
   the shared thing if either could ("whichever lands first builds it"). The run sheet turns
   this into a lane order or a seam.
5. **A box that needs another repo** is split: this repo's boxes, then the other repo's,
   marked as such, so a one-repo run can leave the rest `ready-for-human` cleanly.
6. **A prototype screen is cited by anchor**, and the ticket says which of its details are
   binding; the rest are a difference to report, not a failure.
7. **A create, edit or delete route that the screen hides** says whether it is also refused
   or merely unlinked.
8. **Data migrations say what happens to existing rows**: carried, dropped, or the migration
   stops and names them.
9. **Recorded facts the screen shows** ("last imported", "published on") are named as fields
   with who sets them, or explicitly left out.
10. **Tests are listed by seam** (which endpoint or read, as which user, which refusal), so a
    reviewer can tick them.

A ticket that fails a line is not wrong; it is `needs-triage` until the maintainer settles the
line, or the line is written into the ticket as "left out" so the developer builds around it.
