#!/usr/bin/env python3
"""Work the tickets that are GitHub issues on the notes repo, cheaply, through gh.

Usage:
  python3 issues.py survey [MILESTONE]
  python3 issues.py list MILESTONE
  python3 issues.py show [--all] N
  python3 issues.py chain N
  python3 issues.py check
  python3 issues.py claim [--force] N
  python3 issues.py release N STATUS [--comment-file FILE]
  python3 issues.py comment N --comment-file FILE
  python3 issues.py close N (--completed | --not-planned) --comment-file FILE
  python3 issues.py search [--all] WORDS...
  python3 issues.py new --title T --body-file F --org O --project P --type T --status S
                        --milestone M [--repo R]... [--priority now|soon] [--blocked-by N]...
                        [--create [--milestone-description D]]
  python3 issues.py block [--remove] N BLOCKER...
  python3 issues.py status N STATUS [--comment-file FILE]
  python3 issues.py priority N (now | soon | later) [--comment-file FILE]
  python3 issues.py board [N...]
  python3 issues.py start-here [--dry-run]

The notes repo is $NOTES_ROOT, or ~/code/ai-notes when that is unset. Its
project-notes.json names the issues repo and, optionally, the board, the
Start here issue and the current goals:

  {"issues_repo": "acme/notes",
   "board": {"owner": "acme", "number": 3},
   "start_here": 1,
   "goals": [{"text": "Ship checkout"}, {"text": "Move to issues", "milestone": "shop/issues"}]}

Without "board", claim, release and close skip the board and board refuses;
without "start_here", start-here refuses and check skips it.

survey prints one line per milestone with its count of each status and
priority, then the issues an agent can start (ready-for-agent, no open
blocker), then any blocker problems. list prints every open issue in
MILESTONE, one line each by number: `#12 ready-for-agent soon  Title`, with
`blocked-by #3,#5` before the title when it has open blockers. show prints
an issue with all but its last comment folded (--all prints them all).
chain walks an issue's *blocked by* links to the end; check does it for
every open issue. Only open blockers count: GitHub keeps closed issues in
*blocked by*, and its is:blocked filter ignores them too. Both report
blockers with a lower priority than what waits on them, cycles, and what
each blocked issue ultimately waits on: a person (ready-for-human, in-progress-me, needs-info,
needs-triage) or an agent (ready-for-agent, in-progress-agent).

claim sets status:in-progress-agent in place of the issue's status label. It
refuses an issue already in progress, a closed one, and (without --force) a
blocked one. release swaps status:in-progress-agent for status:STATUS,
posting FILE first if given (say why you stopped); comment just posts FILE,
for a run report on an issue that stays open. close
posts FILE as a comment, closes the issue, drops any in-progress label, and
says which issues that unblocks. All three keep the board in step for the
issue they change; board does it for the issues named, or for every
labelled issue. The board's single-select fields Triage, Project, Org and
Code repo copy the status:, project:, org: and repo: labels, and its Status
field is Todo, In Progress or Done.

search prints the issues matching GitHub search WORDS, open ones (--all
adds closed), one line each: `#12 ready-for-agent soon [shop/checkout]
Title`. new creates an issue with every label group and its milestone,
adds its blockers, syncs the board and reports any blocker below its
priority; it refuses a label or milestone the repo doesn't have unless
--create, which makes the missing org:, project:, repo: or type: labels and
the milestone, then rebuilds Start here. block adds (--remove: removes)
*blocked by* links and reports what N now waits on and any blocker below
its priority: raise that blocker's priority, with a comment saying why.
status sets a status label at triage (not an in-progress one: claim and
release do those), posting FILE first if given, and syncs the board.
priority sets priority:now or priority:soon in place of the old one (later
removes it), posting FILE first if given, and reports the same findings.

Together these cover every ticket change an unattended run makes, so a run
never needs raw gh on the issues repo.

start-here rebuilds the pinned Start here issue from the org:, project:
and repo: labels, the open milestones and the config's goals (start_here.py
is the template), and edits it only if that changes it. Run it after adding
a project, repo, milestone or goal; check says when it's out of date.

Set ISSUES_GH to run another gh (the tests use a fake). Tests:
python3 test_issues.py.
"""
import argparse
import importlib.util
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
NOTES_ROOT = Path(os.environ.get("NOTES_ROOT") or "~/code/ai-notes").expanduser()
CONFIG_FILE = NOTES_ROOT / "project-notes.json"
EXAMPLE = '{"issues_repo": "acme/notes", "board": {"owner": "acme", "number": 3}, "start_here": 1, "goals": []}'
# Set by configure() from project-notes.json.
REPO: str = ""
OWNER: str | None = None
BOARD: str | None = None
START_HERE: int | None = None
GOALS: list[dict] = []
STATUSES = ["needs-triage", "needs-info", "ready-for-agent", "ready-for-human",
            "in-progress-me", "in-progress-agent"]
IN_PROGRESS = {"in-progress-me", "in-progress-agent"}
AGENT = {"ready-for-agent", "in-progress-agent"}
RANK = {"now": 2, "soon": 1, "later": 0, "untriaged": 0}
BOARD_FIELDS = {"status": "Triage", "project": "Project", "org": "Org", "repo": "Code repo"}
LIST_FIELDS = "number,title,state,labels,milestone,blockedBy"


# --- the config -------------------------------------------------------------

def load_config(path: Path = CONFIG_FILE) -> dict:
    """project-notes.json, checked; exits with what's wrong."""
    if not path.is_file():
        sys.exit(f"No {path}. The issue helpers read the notes repo's settings from it; create it, e.g.\n"
                 f"  {EXAMPLE}\n(Set NOTES_ROOT if the notes repo is elsewhere.)")
    try:
        cfg = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        sys.exit(f"{path} is not valid JSON: {e}")
    if not isinstance(cfg, dict) or not re.fullmatch(r"[\w.-]+/[\w.-]+", str(cfg.get("issues_repo", ""))):
        sys.exit(f'{path}: "issues_repo" must be "owner/name"')
    board = cfg.get("board")
    if board is not None and not (isinstance(board, dict) and board.get("owner") and str(board.get("number", "")).isdigit()):
        sys.exit(f'{path}: "board" must be {{"owner": "...", "number": N}}, or left out')
    if cfg.get("start_here") is not None and not str(cfg["start_here"]).isdigit():
        sys.exit(f'{path}: "start_here" must be an issue number, or left out')
    goals = cfg.get("goals") or []
    if not isinstance(goals, list) or not all(isinstance(g, dict) and g.get("text") for g in goals):
        sys.exit(f'{path}: "goals" must be a list of {{"text": "...", "milestone": "..."}} (milestone optional)')
    return cfg


def configure(cfg: dict | None = None) -> dict:
    """Set REPO, OWNER, BOARD, START_HERE and GOALS from the config (read from disk if not given)."""
    global REPO, OWNER, BOARD, START_HERE, GOALS
    cfg = load_config() if cfg is None else cfg
    REPO = cfg["issues_repo"]
    board = cfg.get("board")
    OWNER, BOARD = (board["owner"], str(board["number"])) if board else (None, None)
    START_HERE = int(cfg["start_here"]) if cfg.get("start_here") is not None else None
    GOALS = cfg.get("goals") or []
    return cfg


def gh(*args: str) -> str:
    cmd = shlex.split(os.environ.get("ISSUES_GH", "gh")) + list(args)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        sys.exit(f"gh {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout.strip()


def gh_json(*args: str):
    out = gh(*args)
    return json.loads(out) if out else None


# --- issues -------------------------------------------------------------

def issue(raw: dict) -> dict:
    """gh's JSON for an issue, flattened to what the commands use."""
    labels = [l["name"] for l in raw.get("labels", [])]
    bb = raw.get("blockedBy") or {"nodes": [], "totalCount": 0}
    if bb.get("totalCount", 0) > len(bb["nodes"]):
        print(f"! #{raw['number']}: gh returned {len(bb['nodes'])} of {bb['totalCount']} blockers", file=sys.stderr)
    return {
        "number": raw["number"],
        "title": raw.get("title", ""),
        "state": raw.get("state", "OPEN"),
        "labels": labels,
        "milestone": (raw.get("milestone") or {}).get("title"),
        "blockers": [(b["number"], b["state"]) for b in bb["nodes"]],
        "raw": raw,
    }


def status(i: dict) -> str:
    return next((l.split(":", 1)[1] for l in i["labels"] if l.startswith("status:")), "")


def priority(i: dict) -> str:
    p = next((l.split(":", 1)[1] for l in i["labels"] if l.startswith("priority:")), "")
    if p:
        return p
    return "untriaged" if status(i) == "needs-triage" else "later"


def who(i: dict | None) -> str:
    if i is None:
        return "elsewhere"
    return "agent" if status(i) in AGENT else "person"


def load_open() -> dict[int, dict]:
    raws = gh_json("issue", "list", "-R", REPO, "--state", "open", "--limit", "1000", "--json", LIST_FIELDS)
    return {r["number"]: issue(r) for r in raws}


def view(n: int, fields: str = LIST_FIELDS) -> dict:
    return issue(gh_json("issue", "view", str(n), "-R", REPO, "--json", fields))


# --- the blocker walk -----------------------------------------------------

class Blockers:
    """The open issues' *blocked by* graph, walked to the end."""

    def __init__(self, issues: dict[int, dict]):
        self.issues = issues
        self.cycles: list[list[int]] = []
        self._leaves: dict[int, set[int]] = {}
        self._reach: dict[int, set[int]] = {}

    def open_blockers(self, n: int) -> list[int]:
        i = self.issues.get(n)
        return [b for b, s in i["blockers"] if s == "OPEN"] if i else []

    def _walk(self, n: int, path: list[int]) -> None:
        """Fill _leaves and _reach for n; record any cycle met on the way."""
        if n in self._leaves:
            return
        if n in path:
            cyc = path[path.index(n):]
            k = cyc.index(min(cyc))
            cyc = cyc[k:] + cyc[:k]
            if cyc not in self.cycles:
                self.cycles.append(cyc)
            return
        leaves, reach = set(), set()
        for b in self.open_blockers(n):
            reach.add(b)
            if b not in self.issues or not self.open_blockers(b):
                leaves.add(b)
                continue
            self._walk(b, path + [n])
            leaves |= self._leaves.get(b, set())
            reach |= self._reach.get(b, set())
        self._leaves[n], self._reach[n] = leaves, reach - {n}

    def leaves(self, n: int) -> set[int]:
        self._walk(n, [])
        return self._leaves[n]

    def reach(self, n: int) -> set[int]:
        self._walk(n, [])
        return self._reach[n]

    def low_priority(self, among: set[int] | None = None) -> list[str]:
        """Blockers below the highest priority of anything that waits on them."""
        need: dict[int, int] = {}
        for a in sorted(self.issues if among is None else among):
            if a not in self.issues:
                continue
            for b in self.reach(a):
                if b in self.issues and RANK[priority(self.issues[b])] < RANK[priority(self.issues[a])]:
                    if b not in need or RANK[priority(self.issues[a])] > RANK[priority(self.issues[need[b]])]:
                        need[b] = a
        return [f"! #{b} is {priority(self.issues[b])}, below #{a} ({priority(self.issues[a])}) that waits on it"
                for b, a in sorted(need.items())]

    def waits(self, n: int) -> str:
        parts = []
        for b in sorted(self.leaves(n)):
            i = self.issues.get(b)
            parts.append(f"#{b} {who(i)}" + (f" ({status(i)})" if i else ""))
        return ", ".join(parts) or "nothing outside a cycle"

    def blocked(self) -> list[int]:
        return [n for n in sorted(self.issues) if self.open_blockers(n)]

    def problems(self, among: set[int] | None = None) -> list[str]:
        for n in (self.issues if among is None else among):
            if n in self.issues:
                self._walk(n, [])
        cyc = [f"! cycle " + " > ".join(f"#{x}" for x in c + c[:1]) for c in self.cycles
               if among is None or set(c) & among]
        return self.low_priority(among) + cyc


def line(i: dict) -> str:
    return f"#{i['number']} {priority(i)} {status(i) or 'no-status'}  {i['title']}"


# --- commands -------------------------------------------------------------

def cmd_survey(a) -> None:
    issues = load_open()
    g = Blockers(issues)
    groups: dict[str, list[dict]] = {}
    for i in issues.values():
        if not any(l.startswith("project:") for l in i["labels"]):
            continue  # not a ticket: Start here, say
        if a.milestone and i["milestone"] != a.milestone:
            continue
        groups.setdefault(i["milestone"] or "(no milestone)", []).append(i)
    for m in sorted(groups):
        its = groups[m]
        st = {}
        for i in its:
            st[status(i) or "no-status"] = st.get(status(i) or "no-status", 0) + 1
        pr = {}
        for i in its:
            pr[priority(i)] = pr.get(priority(i), 0) + 1
        nb = sum(1 for i in its if g.open_blockers(i["number"]))
        s = ", ".join(f"{st[k]} {k}" for k in STATUSES + ["no-status"] if k in st)
        p = ", ".join(f"{pr[k]} {k}" for k in RANK if k in pr)
        print(f"{m} ({len(its)}): {s}; {p}" + (f"; {nb} blocked" if nb else ""))
    shown = {i["number"] for its in groups.values() for i in its}
    ready = [issues[n] for n in shown if status(issues[n]) == "ready-for-agent" and not g.open_blockers(n)]
    ready.sort(key=lambda i: (-RANK[priority(i)], i["number"]))
    print("ready:" + ("" if ready else " none"))
    for i in ready:
        print(f"  #{i['number']} {priority(i)}  {i['title']}")
    for p in g.problems(None if not a.milestone else shown):
        print(p)


def cmd_list(a) -> None:
    issues = load_open()
    for n in sorted(issues):
        i = issues[n]
        if i["milestone"] != a.milestone:
            continue
        by = [b for b, s in i["blockers"] if s == "OPEN"]
        blocked = (" blocked-by " + ",".join(f"#{b}" for b in by)) if by else ""
        print(f"#{n} {status(i) or 'no-status'} {priority(i)}{blocked}  {i['title']}")


def cmd_search(a) -> None:
    state = "all" if a.all else "open"
    raws = gh_json("issue", "list", "-R", REPO, "--state", state, "--limit", "50", "--search", " ".join(a.words),
                   "--json", LIST_FIELDS)
    for i in sorted((issue(r) for r in raws), key=lambda i: i["number"]):
        st = (status(i) or "no-status") if i["state"] == "OPEN" else "closed"
        m = f" [{i['milestone']}]" if i["milestone"] else ""
        print(f"#{i['number']} {st} {priority(i)}{m}  {i['title']}")
    if not raws:
        print("none")


LABEL_COLORS = {"org": "5319e7", "project": "0e8a16", "repo": "c5def5", "type": "bfdadc",
                "status": "fbca04", "priority": "d93f0b"}


def blocker_findings(n: int) -> None:
    """After a blocker change: what n waits on, and any blocker below its priority."""
    issues = load_open()
    g = Blockers(issues)
    if g.open_blockers(n):
        print(f"#{n} waits on {g.waits(n)}")
    for p in g.problems({n} | g.reach(n)):
        print(p)


def cmd_new(a) -> None:
    if not os.path.isfile(a.body_file):
        sys.exit(f"No such file: {a.body_file}")
    if a.status not in STATUSES or a.status in IN_PROGRESS:
        sys.exit(f"--status must be one of {', '.join(s for s in STATUSES if s not in IN_PROGRESS)}")
    labels = [f"org:{a.org}", f"project:{a.project}", f"type:{a.type}", f"status:{a.status}"]
    labels += [f"repo:{r}" for r in a.repo]
    if a.priority:
        labels.append(f"priority:{a.priority}")
    have = {l["name"] for l in gh_json("label", "list", "-R", REPO, "--limit", "500", "--json", "name")}
    missing = [l for l in labels if l not in have]
    titles = {m["title"] for m in gh_json("api", f"repos/{REPO}/milestones?state=all&per_page=100")}
    new_milestone = a.milestone not in titles
    if (missing or new_milestone) and not a.create:
        what = missing + ([f"milestone {a.milestone}"] if new_milestone else [])
        sys.exit("Not on the repo yet: " + ", ".join(what) + ". Check the spelling; for a new project, repo, "
                 "type or feature, run again with --create.")
    for l in missing:
        g, _, v = l.partition(":")
        if g in ("status", "priority"):
            sys.exit(f"No label {l}: the status and priority labels are fixed")
        gh("label", "create", l, "-R", REPO, "--color", LABEL_COLORS[g], "--description",
           {"org": f"Work for {v} on GitHub", "project": f"Notes folder: {v}", "repo": f"Code lands in {v}",
            "type": v}[g])
        print(f"created label {l}")
    if new_milestone:
        gh("api", f"repos/{REPO}/milestones", "-f", f"title={a.milestone}", "-f",
           f"description={a.milestone_description or ''}")
        print(f"created milestone {a.milestone}")
    args = ["issue", "create", "-R", REPO, "--title", a.title, "--body-file", a.body_file, "--milestone", a.milestone]
    for l in labels:
        args += ["--label", l]
    n = int(gh(*args).rstrip("/").rsplit("/", 1)[1])
    for b in a.blocked_by:
        gh("issue", "edit", str(n), "-R", REPO, "--add-blocked-by", str(b))
    if BOARD is not None:
        sync_board([n])
    print(f"created #{n}  {a.title}")
    if a.blocked_by:
        blocker_findings(n)
    if (missing or new_milestone) and START_HERE is not None:
        cmd_start_here(argparse.Namespace(dry_run=False))


def cmd_block(a) -> None:
    flag = "--remove-blocked-by" if a.remove else "--add-blocked-by"
    for b in a.blockers:
        if b == a.n:
            sys.exit(f"#{a.n} can't block itself")
        gh("issue", "edit", str(a.n), "-R", REPO, flag, str(b))
    names = ", ".join(f"#{b}" for b in a.blockers)
    print(f"#{a.n} no longer blocked by {names}" if a.remove else f"#{a.n} blocked by {names}")
    blocker_findings(a.n)


def cmd_status(a) -> None:
    new = a.status.removeprefix("status:")
    if new not in STATUSES or new in IN_PROGRESS:
        sys.exit(f"STATUS must be one of {', '.join(s for s in STATUSES if s not in IN_PROGRESS)} "
                 "(claim and release handle in-progress)")
    i = view(a.n)
    if i["state"] != "OPEN":
        sys.exit(f"#{a.n} is closed")
    if status(i) in IN_PROGRESS:
        sys.exit(f"#{a.n} is {status(i)}; release it instead, or leave it alone")
    if a.comment_file:
        post_comment(a.n, a.comment_file)
    set_status(a.n, [l for l in i["labels"] if l.startswith("status:")], new)
    if BOARD is not None:
        sync_board([a.n])
    print(f"#{a.n} is now {new} (was {status(i) or 'no-status'})")


def cmd_priority(a) -> None:
    i = view(a.n)
    old = [l for l in i["labels"] if l.startswith("priority:")]
    want = [] if a.priority == "later" else [f"priority:{a.priority}"]
    if old == want:
        print(f"#{a.n} is already {priority(i)}")
        return
    if a.comment_file:
        post_comment(a.n, a.comment_file)
    args = ["issue", "edit", str(a.n), "-R", REPO]
    for l in old:
        args += ["--remove-label", l]
    for l in want:
        args += ["--add-label", l]
    gh(*args)
    print(f"#{a.n} is now {a.priority}")
    blocker_findings(a.n)


def cmd_show(a) -> None:
    raw = gh_json("issue", "view", str(a.n), "-R", REPO, "--json",
                  "number,title,state,stateReason,labels,milestone,blockedBy,blocking,body,comments")
    i = issue(raw)
    state = raw["state"].lower() + (f" {raw['stateReason'].lower()}" if raw.get("stateReason") else "")
    print(f"#{i['number']} {i['title']} [{state}]")
    print(" ".join(sorted(i["labels"])) + (f" · milestone {i['milestone']}" if i["milestone"] else ""))
    blk = [f"#{b['number']}" + ("" if b["state"] == "OPEN" else " closed") for b in (raw.get("blocking") or {}).get("nodes", [])]
    by = [f"#{b}" + ("" if s == "OPEN" else " closed") for b, s in i["blockers"]]
    if by or blk:
        print(f"blocked by: {', '.join(by) or 'none'} · blocks: {', '.join(blk) or 'none'}")
    print()
    print((raw.get("body") or "").strip())
    comments = raw.get("comments") or []
    hidden = 0 if a.all else max(len(comments) - 1, 0)
    if comments:
        print()
        print(f"## Comments ({hidden} hidden; --all shows them)" if hidden else "## Comments")
        for c in comments[hidden:]:
            print()
            print(f"[{(c.get('author') or {}).get('login', '?')} {c.get('createdAt', '')[:10]}]")
            print(c.get("body", "").strip())


def cmd_chain(a) -> None:
    issues = load_open()
    if a.n not in issues:
        i = view(a.n)
        if i["state"] != "OPEN":
            print(f"#{a.n} is closed  {i['title']}")
            return
        issues[a.n] = i
    g = Blockers(issues)
    seen: set[int] = set()

    def walk(n: int, depth: int, path: list[int]) -> None:
        pad = "  " * depth
        i = issues.get(n)
        if n in path:
            print(f"{pad}#{n} (cycle)")
            return
        if n in seen:
            print(f"{pad}#{n} (above)")
            return
        seen.add(n)
        print(pad + (line(i) if i else f"#{n} open, not in {REPO}"))
        if i:
            for b, s in i["blockers"]:
                if s == "OPEN":
                    walk(b, depth + 1, path + [n])
                else:
                    print(f"{pad}  #{b} closed")

    walk(a.n, 0, [])
    blocks = sorted(n for n, i in issues.items() if any(b == a.n and s == "OPEN" for b, s in i["blockers"]))
    if blocks:
        print("blocks: " + ", ".join(f"#{n}" for n in blocks))
    if g.open_blockers(a.n):
        print("waits on: " + g.waits(a.n))
    for p in g.problems({a.n} | g.reach(a.n)):
        print(p)


def cmd_check(a) -> None:
    issues = load_open()
    g = Blockers(issues)
    blocked = g.blocked()
    problems = g.problems()
    print(f"{len(issues)} open, {len(blocked)} blocked, {len(problems)} blocker problems")
    for n in blocked:
        print(f"#{n} {priority(issues[n])} waits on {g.waits(n)}")
    for p in problems:
        print(p)
    if START_HERE is not None and render_start_here().strip() != current_start_here().strip():
        print("! Start here is out of date: run issues.py start-here")


def set_status(n: int, remove: list[str], new: str) -> None:
    args = ["issue", "edit", str(n), "-R", REPO]
    for l in remove:
        args += ["--remove-label", l]
    gh(*args, "--add-label", f"status:{new}")


def cmd_claim(a) -> None:
    i = view(a.n)
    st = status(i)
    if i["state"] != "OPEN":
        sys.exit(f"#{a.n} is closed")
    if st in IN_PROGRESS:
        sys.exit(f"#{a.n} is already {st}; leave it alone")
    open_by = [b for b, s in i["blockers"] if s == "OPEN"]
    if open_by and not a.force:
        sys.exit(f"#{a.n} is blocked by " + ", ".join(f"#{b}" for b in open_by) + " (--force to claim anyway)")
    set_status(a.n, [l for l in i["labels"] if l.startswith("status:")], "in-progress-agent")
    sync_board([a.n])
    print(f"claimed #{a.n} (was {st or 'no-status'})")


def cmd_release(a) -> None:
    new = a.status.removeprefix("status:")
    if new not in STATUSES or new in IN_PROGRESS:
        sys.exit(f"STATUS must be one of {', '.join(s for s in STATUSES if s not in IN_PROGRESS)}")
    i = view(a.n)
    if status(i) != "in-progress-agent":
        sys.exit(f"#{a.n} is {status(i) or 'no-status'}, not in-progress-agent")
    if a.comment_file:
        post_comment(a.n, a.comment_file)
    set_status(a.n, [l for l in i["labels"] if l.startswith("status:")], new)
    sync_board([a.n])
    print(f"released #{a.n} as {new}")


def post_comment(n: int, path: str) -> None:
    if not os.path.isfile(path):
        sys.exit(f"No such file: {path}")
    gh("issue", "comment", str(n), "-R", REPO, "--body-file", path)


def cmd_comment(a) -> None:
    post_comment(a.n, a.comment_file)
    print(f"commented on #{a.n}")


def cmd_close(a) -> None:
    if not os.path.isfile(a.comment_file):
        sys.exit(f"No such file: {a.comment_file}")
    i = view(a.n)
    if i["state"] != "OPEN":
        sys.exit(f"#{a.n} is already closed")
    drop = [l for l in i["labels"] if l.removeprefix("status:") in IN_PROGRESS]
    if drop:
        args = ["issue", "edit", str(a.n), "-R", REPO]
        for l in drop:
            args += ["--remove-label", l]
        gh(*args)
    gh("issue", "comment", str(a.n), "-R", REPO, "--body-file", a.comment_file)
    reason = "completed" if a.completed else "not planned"
    gh("issue", "close", str(a.n), "-R", REPO, "--reason", reason)
    sync_board([a.n])
    print(f"closed #{a.n} as {reason}")
    issues = load_open()
    issues.pop(a.n, None)
    for n, w in sorted(issues.items()):
        if any(b == a.n for b, _ in w["blockers"]):
            rest = [b for b, s in w["blockers"] if s == "OPEN" and b != a.n]
            if rest:
                print(f"#{n} still waits on " + ", ".join(f"#{b}" for b in rest))
            else:
                print(f"unblocked: #{n} {status(w)}  {w['title']}")


# --- the board ------------------------------------------------------------

def sync_board(only: list[int] | None = None) -> None:
    """Make the board's fields match the issues' labels; add missing labelled issues."""
    if BOARD is None:
        return
    pid = gh_json("project", "view", BOARD, "--owner", OWNER, "--format", "json")["id"]
    fields = {f["name"]: f for f in gh_json("project", "field-list", BOARD, "--owner", OWNER, "--format", "json")["fields"]}
    items = gh_json("project", "item-list", BOARD, "--owner", OWNER, "--format", "json", "--limit", "1000")["items"]
    by_number = {i["content"].get("number"): i for i in items if i.get("content")}
    issues = gh_json("issue", "list", "-R", REPO, "--state", "all", "--limit", "1000", "--json", "number,url,state,labels")
    for iss in sorted(issues, key=lambda x: x["number"]):
        if only is not None and iss["number"] not in only:
            continue
        labels = [l["name"] for l in iss["labels"]]
        if not any(l.startswith("project:") for l in labels):
            continue
        item = by_number.get(iss["number"])
        if not item:
            item = gh_json("project", "item-add", BOARD, "--owner", OWNER, "--url", iss["url"], "--format", "json")
        want = {}
        for l in labels:
            g, _, v = l.partition(":")
            if g in BOARD_FIELDS and BOARD_FIELDS[g] not in want:
                want[BOARD_FIELDS[g]] = v
        want["Status"] = ("Done" if iss["state"] == "CLOSED" else
                          "In Progress" if want.get("Triage", "").startswith("in-progress") else "Todo")
        changed = []
        for name, value in want.items():
            f = fields[name]
            opt = next((o for o in f.get("options", []) if o["name"] == value), None)
            if opt is None:
                print(f"! board has no {name} option '{value}' (#{iss['number']})")
                continue
            if item.get(name.lower()) == value:
                continue
            gh("project", "item-edit", "--id", item["id"], "--project-id", pid, "--field-id", f["id"],
               "--single-select-option-id", opt["id"])
            changed.append(f"{name}={value}")
        if changed:
            print(f"board #{iss['number']}: " + ", ".join(changed))


def cmd_board(a) -> None:
    if BOARD is None:
        sys.exit(f'No "board" in {CONFIG_FILE}: nothing to sync')
    sync_board(a.n or None)


# --- Start here -------------------------------------------------------------

def render_start_here() -> str:
    spec = importlib.util.spec_from_file_location("start_here", HERE / "start_here.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    names = [l["name"] for l in gh_json("label", "list", "-R", REPO, "--limit", "500", "--json", "name")]
    group = lambda g: sorted((n.split(":", 1)[1] for n in names if n.startswith(g + ":")), key=str.lower)
    ms = gh_json("api", f"repos/{REPO}/milestones?state=open&per_page=100")
    board = None
    if BOARD is not None:
        b = gh_json("project", "view", BOARD, "--owner", OWNER, "--format", "json")
        board = {"title": b["title"], "url": b["url"], "public": b.get("public", False)}
    return mod.render(REPO, group("org"), group("project"), group("repo"), sorted(m["title"] for m in ms),
                      GOALS, board)


def current_start_here() -> str:
    return gh_json("issue", "view", str(START_HERE), "-R", REPO, "--json", "body")["body"]


def cmd_start_here(a) -> None:
    if START_HERE is None:
        sys.exit(f'No "start_here" issue number in {CONFIG_FILE}')
    new, old = render_start_here(), current_start_here()
    if new.strip() == old.strip():
        print("Start here unchanged")
        return
    if a.dry_run:
        sys.stdout.write(new)
        return
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write(new)
    try:
        gh("issue", "edit", str(START_HERE), "-R", REPO, "--body-file", f.name)
    finally:
        os.unlink(f.name)
    print("Start here updated")


def main() -> None:
    p = argparse.ArgumentParser(description="Work the notes repo's issues cheaply.")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("survey"); s.add_argument("milestone", nargs="?"); s.set_defaults(f=cmd_survey)
    s = sub.add_parser("list"); s.add_argument("milestone"); s.set_defaults(f=cmd_list)
    s = sub.add_parser("show"); s.add_argument("--all", action="store_true"); s.add_argument("n", type=int); s.set_defaults(f=cmd_show)
    s = sub.add_parser("chain"); s.add_argument("n", type=int); s.set_defaults(f=cmd_chain)
    s = sub.add_parser("check"); s.set_defaults(f=cmd_check)
    s = sub.add_parser("claim"); s.add_argument("--force", action="store_true"); s.add_argument("n", type=int); s.set_defaults(f=cmd_claim)
    s = sub.add_parser("release"); s.add_argument("n", type=int); s.add_argument("status")
    s.add_argument("--comment-file"); s.set_defaults(f=cmd_release)
    s = sub.add_parser("comment"); s.add_argument("n", type=int); s.add_argument("--comment-file", required=True)
    s.set_defaults(f=cmd_comment)
    s = sub.add_parser("close"); s.add_argument("n", type=int)
    r = s.add_mutually_exclusive_group(required=True)
    r.add_argument("--completed", action="store_true"); r.add_argument("--not-planned", action="store_true")
    s.add_argument("--comment-file", required=True); s.set_defaults(f=cmd_close)
    s = sub.add_parser("search"); s.add_argument("--all", action="store_true"); s.add_argument("words", nargs="+")
    s.set_defaults(f=cmd_search)
    s = sub.add_parser("new")
    for flag in ("--title", "--body-file", "--org", "--project", "--type", "--status", "--milestone"):
        s.add_argument(flag, required=True)
    s.add_argument("--repo", action="append", default=[], help="repeat for each; leave out for none")
    s.add_argument("--priority", choices=["now", "soon"])
    s.add_argument("--blocked-by", type=int, action="append", default=[])
    s.add_argument("--create", action="store_true", help="create missing org/project/repo/type labels and the milestone")
    s.add_argument("--milestone-description")
    s.set_defaults(f=cmd_new)
    s = sub.add_parser("status"); s.add_argument("n", type=int); s.add_argument("status")
    s.add_argument("--comment-file"); s.set_defaults(f=cmd_status)
    s = sub.add_parser("priority"); s.add_argument("n", type=int); s.add_argument("priority", choices=["now", "soon", "later"])
    s.add_argument("--comment-file"); s.set_defaults(f=cmd_priority)
    s = sub.add_parser("block"); s.add_argument("--remove", action="store_true"); s.add_argument("n", type=int)
    s.add_argument("blockers", type=int, nargs="+"); s.set_defaults(f=cmd_block)
    s = sub.add_parser("board"); s.add_argument("n", type=int, nargs="*"); s.set_defaults(f=cmd_board)
    s = sub.add_parser("start-here"); s.add_argument("--dry-run", action="store_true"); s.set_defaults(f=cmd_start_here)
    a = p.parse_args()
    configure()
    a.f(a)


if __name__ == "__main__":
    main()
