# Ticket checklist: what a ticket settles before it is `ready-for-agent`

An unattended developer stops and reports where the ticket, its spec and its decisions
leave a gap. Each gap costs a round trip through the maintainer (`ready-for-human`) or a
finding to decide later. One early run left twelve findings for the maintainer; most were one
of the shapes below. Pass every ticket (the issue's body and comments) through this list
when writing it, and again before setting `status:ready-for-agent`.

1. **Every count or list says what it counts.** Direct children or all descendants; retired
   rows in or out; which edition's rows (the live one, the draft, both).
2. **Every new or changed field says whether it is served**, and in which document or
   catalogue, with its shape; or says it is not served.
3. **Every refusal names its message** and who gets it; where two rules can refuse the same
   action, which message wins.
4. **A box that depends on another ticket in the same run** names it (`#n`), and says which
   builds the shared thing if either could ("whichever lands first builds it"). The run
   sheet turns this into a lane order or a seam. A ticket that needs another finished first
   has a *blocked by* link to it.
5. **A box that needs another repo** is split: this repo's boxes, then the other repo's,
   marked as such, with a `repo:` label for each, so a one-repo run can leave the rest
   `ready-for-human` cleanly.
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
11. **A box that admits new rows** (an import keeping rows it used to skip, a copy, a bulk
    add) says how each required field is filled for them. An import that now keeps rows
    with no category can't land if the title comes from the category.
12. **A rule that reads another record says what happens when that record later changes or
    goes**: an invoice line whose discount code is deleted, an order line whose product is
    retired. Refused at save, refused at publish, or left as it is.
13. **A box that restates a decision's list** (what may be changed, what is refused) quotes
    the decision or cites it, and says where it allows less. "Nothing else" in a box that a
    decision's wider list contradicts is a question the developer will stop on.
14. **A new way to save a record** (a grid, a drawer, an inline form) says what happens when
    the record was saved by someone else since it was opened: refused like an existing
    screen that checks (name it), or last save wins.

A ticket that fails a line is not wrong; it is `status:needs-triage` until the maintainer
settles the line (ask on the issue, as `issue-tracker.md`'s triage says), or the line is
written into the ticket as "left out" so the developer builds around it.
