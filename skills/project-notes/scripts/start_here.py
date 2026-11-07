"""The body of the pinned "Start here" issue: one-tap searches at each zoom level.

issues.py start-here calls render() with the live labels and milestones, the
goals from project-notes.json, and the board's title and link.
"""
import urllib.parse

HELPER = "~/.claude/skills/project-notes/scripts/issues.py"


def render(repo: str, orgs: list[str], projects: list[str], repos: list[str], milestones: list[str],
           goals: list[dict], board: dict | None) -> str:
    """repo is owner/name; goals are {"text", "milestone"?}; board is {"title", "url", "public"} or None."""
    issues = f"https://github.com/{repo}/issues"
    notes = repo.split("/", 1)[1]

    def link(text, q):
        return f"[{text}]({issues}?q={urllib.parse.quote('is:issue ' + q)})"

    out = ["Every ticket on GitHub is an issue here. Tap a search; on the phone they open in the GitHub app.", ""]
    if board:
        out += [f"**Board:** [{board['title']}]({board['url']}), the same issues in columns"
                + ("" if board.get("public") else " (private)") + ".", ""]
    out += ["## Current goals", "",
            "Work that moves one of these forward is `priority:soon` even with no deadline. Keep it to three or four.",
            ""]
    for k, g in enumerate(goals, 1):
        m = g.get("milestone")
        out.append(f"{k}. {g['text']}" + (" (" + link(m, 'milestone:"' + m + '"') + ")" if m else ""))
    if not goals:
        out.append("_None yet: list them under \"goals\" in the notes repo's `project-notes.json`._")
    out += [
        "",
        "## What needs attention",
        "",
        "- " + link("Now", 'is:open label:"priority:now" -is:blocked sort:created-asc') + ": deadline close, someone blocked, something broken, a broken promise, privacy or security; only what can be acted on",
        "- " + link("Blocked and urgent", 'is:open label:"priority:now" is:blocked') + ": urgent but waiting; look at what blocks it",
        "- " + link("Soon", 'is:open label:"priority:soon" -is:blocked sort:created-asc') + ": a later deadline, or moves a goal forward",
        "- " + link("Unblocks others", "is:open is:blocking") + ": finishing it frees other work",
        "- " + link("Needs me", 'is:open label:"status:ready-for-human" sort:created-asc') + ": a person has to do it or decide, oldest first",
        "- " + link("Needs triage", 'is:open label:"status:needs-triage"') + ": not yet judged",
        "- " + link("Agents can start", 'is:open label:"status:ready-for-agent" -is:blocked') + ": specified, nothing in the way",
        "- " + link("Blocked", "is:open is:blocked") + ": waiting on another issue",
        "- " + link("Later", 'is:open -label:"priority:now" -label:"priority:soon" label:"status:ready-for-agent","status:ready-for-human","status:needs-info"') + ": triaged, no priority; it can wait",
        "- " + link("Everything open", "is:open"),
        "- " + link("Recently closed", "is:closed sort:updated-desc"),
        "",
        "## Zoom",
        "",
        "**By org:** " + " · ".join(link(o, f'is:open label:"org:{o}"') for o in orgs),
        "",
        f"**By project** (the {notes} folder): " + " · ".join(link(p, f'is:open label:"project:{p}"') for p in projects),
        "",
        "**By repo** (where the code lands): " + " · ".join(link(r, f'is:open label:"repo:{r}"') for r in repos),
        "",
        f"**By feature** ([all milestones](https://github.com/{repo}/milestones)): "
        + " · ".join(link(m, f'milestone:"{m}"') for m in milestones),
        "",
        "Filters combine: add `label:\"status:ready-for-human\"` to any search above to see only what needs you there.",
        "",
        "## How the labels work",
        "",
        "| Group | Meaning |",
        "| --- | --- |",
        "| `org:` | The GitHub org or account the work is for |",
        f"| `project:` | The {notes} folder that holds the feature's spec and decisions |",
        "| `repo:` | Where the code lands; a ticket can have more than one |",
        "| `status:` | needs-triage, needs-info, ready-for-agent, ready-for-human. Blocked is GitHub's own *blocked by* link; done is closed |",
        "| `type:` | task, grilling, prototype or research |",
        "| `priority:` | now or soon, set at triage; no label means later |",
        "",
        "A feature is a milestone named `project/feature`; its description links the spec.",
        "",
        f"_Agents: after adding a project, repo or milestone, run `python3 {HELPER} start-here`; it rebuilds this from the labels and milestones._",
    ]
    return "\n".join(out) + "\n"
