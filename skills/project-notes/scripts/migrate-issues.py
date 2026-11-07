#!/usr/bin/env python3
"""Move markdown features' tickets to GitHub issues on the notes repo.

Usage:
  python3 migrate-issues.py --dry-run OUT [options]
  python3 migrate-issues.py --run OUT [options]

Options:
  --feature PROJECT/FEATURE   only this feature (repeatable); default every open one
  --include-archived          also move features under <project>/tickets/archive/
  --decisions FILE            the maintainer's answers to the dry run (JSON, below)
  --root DIR                  the notes checkout (default: $NOTES_ROOT, or ~/code/ai-notes)
  --date YYYY-MM-DD           the date on each "Moved from" line (default: today)

The issues repo is "issues_repo" in the notes checkout's project-notes.json
(see issues.py). Code repos' owners come from the project READMEs' repo
maps: a Codebase cell names `owner/name`, or a `~/code/owner/name` path.

--dry-run changes nothing on GitHub (it only lists issues, labels and
milestones). It writes into OUT one file per ticket (title, labels,
milestone, blockers, then the body and each comment as they would be
posted), plan.json, and report.md: counts, the labels and milestones it
would create, links it couldn't resolve, statuses it couldn't map, the
status each blocked ticket takes, tickets without a repo label, and lines
elsewhere in the repo that link to a ticket that moves.

--run does the move: creates missing labels and milestones, then every
issue (title, labels, milestone, and a placeholder body holding the "Moved
from" line), then for each: its blockers, its comments, closing it if the
ticket was resolved or wontfix, and last its real body. OUT/map.json
records path -> issue number as it goes. A re-run skips every ticket whose
issue already has its real body (found by the "Moved from" line), and
finishes any it finds with the placeholder still on, so a stopped run
resumes. It refuses to start while a ticket's status can't be mapped. It
never edits or deletes files here: afterwards remove the moved tickets and
fix the lines the report lists, then run `issues.py board` and
`issues.py start-here`. A moved feature's folder keeps its spec.md (and
map.md), which the milestone's description links.

Labels: org:, project:, repo: (from the ticket's Repo: line, bare names
looked up in the project READMEs' repo maps), status:, type:. No priority:
markdown tickets have none, so moved issues get none unless the decisions
file gives one; the report lists them for triage. A blocked ticket takes the
status it has once unblocked (its status note's role word if it names one,
ready-for-human when its Repo: line is "none", else ready-for-agent), and
GitHub's blocked-by link carries the block, added only between open issues.

The decisions file (all keys optional; paths as the report prints them):
  {"status": {"<ticket path>": "ready-for-human"},
   "type": {"<ticket path>": "grilling"},
   "repos": {"<ticket path>": ["acme/storefront"]},
   "pr_repo": {"<ticket path>": "acme/storefront"},  (whose a bare #41 is)
   "priority": {"<ticket path or project/feature>": "soon"}}

gh runs through issues.py's wrapper (ISSUES_GH picks another gh; the tests
use a fake). Tests: python3 test_migrate_issues.py.
"""
import argparse
import datetime
import importlib.util
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name: str, file: str):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


issues = load("issues", "issues.py")
checker = load("check_tickets", "check-tickets.py")
gh, gh_json = issues.gh, issues.gh_json
# Set by configure() from the notes checkout's project-notes.json.
REPO = GITHUB = BLOB = TREE = ""


def configure(root: Path) -> None:
    global REPO, GITHUB, BLOB, TREE
    issues.configure(issues.load_config(root / "project-notes.json"))
    REPO = issues.REPO
    GITHUB = f"https://github.com/{REPO}"
    BLOB, TREE = f"{GITHUB}/blob/main/", f"{GITHUB}/tree/main/"


OPEN_ROLES = {"needs-triage", "needs-info", "ready-for-agent", "ready-for-human",
              "in-progress-me", "in-progress-agent"}
CLOSED_AS = {"resolved": "completed", "wontfix": "not planned"}
AFTER_BLOCKED = ("ready-for-human", "ready-for-agent", "needs-triage", "needs-info")
TYPES = {"task", "grilling", "prototype", "research"}
TYPE_ALIASES = {"build": "task"}
TYPE_DESC = {"task": "Build or change something", "grilling": "A decision to settle with the maintainer",
             "prototype": "A throwaway prototype to answer a design question",
             "research": "Find something out and write it up"}
COLOURS = {"org": "5319e7", "project": "0e8a16", "repo": "c5def5", "type": "bfdadc"}
PLACEHOLDER = "(Moving: the rest of this issue follows.)"
META = ("Status", "Type", "Repo", "Blocked by")
META_RE = re.compile(r"^(?:\*\*)?(Status|Type|Repo|Blocked by):(?:\*\*)?[ \t]*(.*)$", re.I)
MOVED_RE = re.compile(r"\*\*Moved from:\*\* `([^`]+)`")
NONE_BLOCKERS = re.compile(r"(?i)none\.?(\s*\(can start immediately\.?\))?\.?")
COMMENT_START = {
    "bold": re.compile(r"^\*\*20\d\d-\d\d-\d\d"),
    "list": re.compile(r"^- (?:\*\*)?20\d\d-\d\d-\d\d"),
    "plain": re.compile(r"^20\d\d-\d\d-\d\d[^\n]{0,40}?[:,]"),
}
BODY_LIMIT = 65000


def key(path: str) -> str:
    """A ticket's path with its open/closed side folded, for lookups."""
    return path.replace("/issues/archive/", "/issues/")


# --- the repo maps ------------------------------------------------------------

def owner_pattern(owners) -> str:
    """A regex group matching any of these GitHub owners, longest first."""
    return "(" + "|".join(re.escape(o) for o in sorted(set(owners), key=lambda o: (-len(o), o))) + ")"


def repo_maps(root: Path) -> tuple[dict[str, list[str]], dict[str, str]]:
    """Each project's repos (owner/name) from its README's map, and every known name -> owner.

    A Codebase cell names its repos as `owner/name` before any bracket, or as
    a bare name followed by its local path, `name (~/code/owner/name)`.
    """
    projects, known = {}, {}
    for readme in sorted(root.glob("*/README.md")):
        rows, in_map = [], False
        for line in readme.read_text().split("\n"):
            if line.startswith("| Codebase"):
                in_map = True
                continue
            if not in_map:
                continue
            if not line.startswith("|"):
                break
            if re.match(r"^\|[\s|:-]+\|$", line):
                continue
            cell = line.split("|")[1]
            found = re.findall(r"(?<![\w.~/-])([\w.-]+)/([\w.-]*\w)", cell.split("(")[0])
            if not found:
                m = re.match(r"\s*`?([\w.-]+)`?\s*\(`?~/code/([\w.-]+)/", cell)
                found = [(m.group(2), m.group(1))] if m else []
            for owner, name in found:
                rows.append(f"{owner}/{name}")
                known.setdefault(name, owner)
        if rows:
            projects[readme.parent.name] = rows
    return projects, known


def ticket_repos(repo_line: str | None, project: str, maps, known, owners=None) -> tuple[list[str], str]:
    """The repos a ticket's code lands in, and where that answer came from.

    owners: the GitHub owners an `owner/name` may name (default: known's).
    """
    if repo_line is None:
        rows = maps.get(project, [])
        return (rows, "the project's only repo") if len(rows) == 1 else ([], "no Repo: line")
    text = repo_line.replace("`", "")
    while re.search(r"\([^()]*\)", text):
        text = re.sub(r"\([^()]*\)", "", text)
    if re.match(r"\s*(none|to decide)\b", text, re.I):
        return [], "Repo: " + repo_line
    found = []
    own = owner_pattern(owners or set(known.values()) or {"-"})
    for owner, name in re.findall(rf"\b{own}/([\w.-]*\w)", text):
        if f"{owner}/{name}" not in found:
            found.append(f"{owner}/{name}")
    rest = re.sub(rf"\b{own}/[\w.-]+", " ", text)
    for name in re.findall(r"(?<![\w/.~-])([a-z][\w-]*\w)(?![\w/-])", rest):
        if name in known and f"{known[name]}/{name}" not in found:
            found.append(f"{known[name]}/{name}")
    return found, ("Repo: line" if found else "Repo: " + repo_line)


# --- one ticket ---------------------------------------------------------------

def parse(text: str) -> dict:
    """A ticket file: title, its meta lines, body and comments, either format."""
    lines = text.rstrip("\n").split("\n")
    title = re.sub(r"^#\s*\d+[:.]?\s*", "", lines[0]).strip()
    meta, body = {}, []
    before_heading = True
    for line in lines[1:]:
        if line.startswith("## "):
            before_heading = False
        m = META_RE.match(line) if before_heading else None
        if m:
            name = next(x for x in META if x.lower() == m.group(1).lower())
            if name not in meta:
                meta[name] = m.group(2).strip()
                continue
        body.append(line)
    rest = re.sub(r"\n{3,}", "\n\n", "\n".join(body)).strip("\n")
    comments = []
    parts = re.split(r"^## Comments[ \t]*$", rest, maxsplit=1, flags=re.M)
    if len(parts) == 2:
        rest, comments = parts[0].rstrip("\n"), split_comments(parts[1])
    return {"title": title, "meta": meta, "body": rest, "comments": comments}


def split_comments(text: str) -> list[str]:
    """Split a ## Comments section: a dated line in the section's own style starts a comment.

    Bold dates always start one; list ("- 2026-…") and plain ("2026-…:") ones
    only when the section's first comment uses that style, so a dated list
    inside a bold comment stays in it.
    """
    lines = text.strip("\n").split("\n")
    first = next((s for l in lines for s, r in COMMENT_START.items() if r.match(l)), "bold")
    starts = [COMMENT_START["bold"], COMMENT_START[first]]
    out, cur = [], []
    for line in lines:
        if any(r.match(line) for r in starts) and cur and any(l.strip() for l in cur):
            out.append(cur)
            cur = []
        cur.append(line)
    if any(l.strip() for l in cur):
        out.append(cur)
    res = []
    for c in out:
        if COMMENT_START["list"].match(c[0]):
            c = [c[0][2:]] + [l[2:] if l.startswith("  ") else l for l in c[1:]]
        t = "\n".join(c).strip()
        if re.match(r"20\d\d-\d\d-\d\d", t):  # bold the leading date (and who), as the others are
            t = re.sub(r"^(20\d\d-\d\d-\d\d(?: \([^)]*\))?)(:|,)?",
                       lambda m: f"**{m.group(1)}{m.group(2) or ''}**", t, count=1)
        res.append(t)
    return res


def split_status(value: str) -> tuple[str, str]:
    """`blocked — waits on 02` -> ("blocked", "waits on 02")."""
    m = re.match(r"\s*([a-z-]+)[.,;:]?\s*(?:[—–-]+\s*)?(.*)$", value, re.S)
    return (m.group(1), m.group(2).strip()) if m else ("", value.strip())


def role_for(word: str, note: str, repo_line: str | None) -> tuple[str | None, str | None, str]:
    """(open status, close reason, why) for a markdown status; (None, None, why) if unmapped."""
    if word in CLOSED_AS:
        return None, CLOSED_AS[word], word
    if word in OPEN_ROLES:
        return word, None, word
    if word == "blocked":
        hits = [(note.lower().find(r), r) for r in AFTER_BLOCKED if r in note.lower()]
        if hits:
            return min(hits)[1], None, "blocked; its status note names it"
        if repo_line is not None and re.match(r"\s*`?none\b", repo_line, re.I):
            return "ready-for-human", None, "blocked; Repo: none, so a person's work"
        return "ready-for-agent", None, "blocked; specified, so ready-for-agent (default)"
    return None, None, f"'{word or '(none)'}' has no issue status"


# --- links --------------------------------------------------------------------

class Linker:
    """Rewrites a ticket's relative links for GitHub, collecting what it couldn't resolve."""

    def __init__(self, root: Path, numbers: dict[str, int], milestones: dict[str, int], known: dict[str, str],
                 feature_names: set[str]):
        self.root, self.numbers, self.milestones, self.known = root, numbers, milestones, known
        self.feature_names = feature_names
        self.qualified: dict[str, dict[str, set[str]]] = {}  # ticket -> number -> repos it names Owner/repo#n
        self.unresolved: list[tuple[str, str, str]] = []  # (ticket, link text, why)

    def target(self, base: str, ref: str):
        """("issue", n) | ("url", url, shown path) | None for a ref relative to folder base."""
        path, _, anchor = ref.partition("#")
        r = os.path.normpath(os.path.join(base, path)) if path else base
        if r.startswith("..") or os.path.isabs(path):
            return None
        if key(r) in self.numbers:
            return ("issue", self.numbers[key(r)])
        if r.rstrip("/") in self.milestones:
            return ("url", f"{GITHUB}/milestone/{self.milestones[r.rstrip('/')]}", r)
        full = self.root / r
        if full.is_dir():
            return ("url", TREE + r, r)
        if full.is_file():
            return ("url", BLOB + r + (f"#{anchor}" if anchor else ""), r)
        return None

    def rewrite(self, text: str, ticket: str, feature_numbers: dict[str, int], code_repo: str | None) -> str:
        base = os.path.dirname(ticket)
        out, fence = [], False
        for chunk in re.split(r"(^```.*$)", text, flags=re.M):
            if chunk.startswith("```"):
                fence = not fence
                out.append(chunk)
            else:
                out.append(chunk if fence else self._prose(chunk, base, ticket, feature_numbers, code_repo))
        return "".join(out)

    def _prose(self, text, base, ticket, feature_numbers, code_repo):
        held = []

        def hold(s: str) -> str:
            held.append(s)
            return f"\x00{len(held) - 1}\x00"

        def link(m):
            label, ref = m.group(1), m.group(2)
            if re.match(r"^(\w+:|#|/|~)", ref):
                return hold(m.group(0))
            t = self.target(base, ref)
            if not t:
                self.unresolved.append((ticket, m.group(0), "links a file that isn't here; left as written"))
                return hold(m.group(0))
            if t[0] == "issue":
                bare = label.strip("`")  # a link named by its number or path becomes the issue's number
                pathlike = re.fullmatch(r"[\w./-]*\d\d[\w./-]*|[\w./-]*/[\w./-]*", bare)
                return hold(f"#{t[1]}" if pathlike else f"{label} (#{t[1]})")
            return hold(f"[{label}]({t[1]})")

        def tick(m):
            ref = m.group(1)
            if not re.match(r"^(\.\.?/|issues/|archive/)", ref) or re.search(r"\s", ref):
                return hold(m.group(0))
            t = self.target(base, ref)
            if not t:
                self.unresolved.append((ticket, m.group(0), "a path in code, not a file here; left as code"))
                return hold(m.group(0))
            return hold(f"#{t[1]}" if t[0] == "issue" else f"[`{t[2]}`]({t[1]})")

        text = re.sub(r"\[([^\]\n]*)\]\(([^)\s]+)\)", link, text)
        text = re.sub(r"`([^`\n]+)`", tick, text)

        def short(m):  # storefront#14 -> acme/storefront#14
            name = m.group(1)
            return f"{self.known[name]}/{name}#{m.group(2)}" if name in self.known else m.group(0)

        text = re.sub(r"(?<![\w/.-])([a-z][\w-]*\w)#(\d+)(?![\w-])", short, text)

        def bare(m):  # a markdown ticket's #41 is a code repo's, never a notes repo issue
            if code_repo:
                return f"{code_repo}#{m.group(1)}"
            named = self.qualified.get(ticket, {}).get(m.group(1), set())
            if len(named) == 1:  # the ticket names it in full elsewhere
                return f"{next(iter(named))}#{m.group(1)}"
            said = re.search(r"([a-z][\w-]*\w)(?:'s)? (?:PR|pull request|issue) $", text[max(0, m.start() - 60):m.start()])
            if said and said.group(1) in self.known:  # "storefront PR #36"
                return f"{self.known[said.group(1)]}/{said.group(1)}#{m.group(1)}"
            line = text[text.rfind("\n", 0, m.start()) + 1:text.find("\n", m.end()) % (len(text) + 1)]
            line = re.sub(r"\x00(\d+)\x00", lambda h: held[int(h.group(1))], line).strip()
            if len(line) > 160:
                at = max(0, line.find(m.group(0)) - 80)
                line = ("…" if at else "") + line[at:at + 160] + "…"
            self.unresolved.append((ticket, line or m.group(0),
                                    f"bare {m.group(0)}: the ticket names several code repos or none; "
                                    "give one as \"pr_repo\""))
            return m.group(0)

        text = re.sub(r"(?<![\w/&#])#(\d+)(?![\w-])", bare, text)

        def tickets(m):  # "ticket 21", "tickets 12 and 32" in the same feature
            before = text[max(0, m.start() - 40):m.start()]
            prev = re.findall(r"([\w'-]+)\s*$", before)
            if prev and (prev[-1].endswith("'s") or prev[-1] in self.feature_names):
                return m.group(0)
            return m.group(1) + re.sub(r"\b\d\d\b", lambda d: f"#{feature_numbers[d.group(0)]}"
                                       if d.group(0) in feature_numbers else d.group(0), m.group(2))

        text = re.sub(r"\b([Tt]ickets? )(\d\d(?:(?:,? and |, | or )\d\d)*)\b(?![–-]\d| to \d)", tickets, text)
        return re.sub(r"\x00(\d+)\x00", lambda m: held[int(m.group(1))], text)


# --- the plan -----------------------------------------------------------------

def github_state() -> dict:
    """What's on GitHub already: moved tickets, issue states, labels, milestones, the next number."""
    raws = gh_json("issue", "list", "-R", REPO, "--state", "all", "--limit", "5000",
                   "--json", "number,state,body") or []
    prs = gh_json("pr", "list", "-R", REPO, "--state", "all", "--limit", "1", "--json", "number") or []
    moved, states = {}, {}
    for r in raws:
        states[r["number"]] = r["state"]
        m = MOVED_RE.search(r.get("body") or "")
        if m:
            moved[key(m.group(1))] = {"number": r["number"], "done": PLACEHOLDER not in r["body"]}
    labels = {l["name"] for l in gh_json("label", "list", "-R", REPO, "--limit", "1000", "--json", "name") or []}
    ms = gh_json("api", f"repos/{REPO}/milestones?state=all&per_page=100") or []
    top = max([r["number"] for r in raws] + [p["number"] for p in prs] + [0])
    return {"moved": moved, "states": states, "labels": labels,
            "milestones": {m["title"]: m["number"] for m in ms},
            "next_issue": top + 1, "next_milestone": max([m["number"] for m in ms] + [0]) + 1}


def features(root: Path, only: list[str], archived: bool) -> list[tuple[str, Path]]:
    """(project/feature, folder) for each feature folder with ticket files."""
    found = []
    for d in sorted(root.glob("*/tickets/*/")) + (sorted(root.glob("*/tickets/archive/*/")) if archived else []):
        if d.name == "archive" or not (list(d.glob("issues/*.md")) + list(d.glob("issues/archive/*.md"))):
            continue
        name = f"{d.parts[-3] if d.parent.name != 'archive' else d.parts[-4]}/{d.name}"
        if only and name not in only:
            continue
        found.append((name, d))
    return found


def milestone_description(folder: Path, root: Path) -> str:
    spec = folder / "spec.md"
    for doc in (spec, folder / "map.md"):
        if doc.is_file():
            paras = [p.strip() for p in re.split(r"\n\s*\n", doc.read_text()) if p.strip()]
            prose = next((p for p in paras if not re.match(r"^[#|>`-]|^\*\*|^\d+\.|^[A-Z][\w ]{0,20}:\s", p)), "")
            prose = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", " ".join(prose.split()))
            first = re.split(r"(?<=[.!?])\s", prose)[0]
            if len(first) > 200:
                first = first[:200].rsplit(" ", 1)[0] + "…"
            rel = doc.relative_to(root).as_posix()
            return (first + " " if first else "") + f"{'Spec' if doc == spec else 'Map'}: {BLOB}{rel}"
    return "No spec."


BLOCKER_PATH = r"(?:\.\./|\./)[\w./-]*?issues/(?:archive/)?\d\d[\w.-]*"


def blocker_refs(root: Path, ticket: Path, line: str, numbers: dict[str, int]) -> tuple[list[str], list[str]]:
    """The tickets (repo paths) a Blocked by: line names, and the refs that name none.

    Like check-tickets.py's, but also reads paths into issues/archive/, and
    paths to tickets already moved (their files gone).
    """
    text = re.sub(r"\([^)]*\)", "", line)
    found, missing = [], []
    base = ticket.parent.relative_to(root).as_posix()
    for ref in re.findall(BLOCKER_PATH, text):
        r = os.path.normpath(os.path.join(base, ref))
        hit = checker.find_issue((ticket.parent / ref).parent, ref)
        if hit:
            found.append(hit.relative_to(root).as_posix())
        elif key(r) in numbers:
            found.append(r)
        else:
            missing.append(ref)
    for number in checker.NUM_RE.findall(re.sub(BLOCKER_PATH, "", text)):
        hit = checker.find_issue(ticket.parent, number)
        (found.append(hit.relative_to(root).as_posix()) if hit else missing.append(number))
    return found, missing


def build_plan(root: Path, state: dict, args, decisions: dict) -> dict:
    maps, known = repo_maps(root)
    mapped = Counter(r.split("/")[0] for rows in maps.values() for r in rows)
    owners = set(mapped) | {REPO.split("/")[0]}
    # a repo: label the maps don't name belongs to the owner most of them name
    default_owner = mapped.most_common(1)[0][0] if mapped else REPO.split("/")[0]
    own = owner_pattern(owners)
    for label in state["labels"]:
        if label.startswith("repo:"):
            known.setdefault(label[5:], default_owner)
    feats = features(root, args.feature, args.include_archived)
    tickets, n, mn = [], state["next_issue"], state["next_milestone"]
    milestones = dict(state["milestones"])
    feature_rows = []
    for name, folder in feats:
        title = name
        if title not in milestones:
            milestones[title] = mn
            feature_rows.append({"title": title, "number": mn, "new": True,
                                 "description": milestone_description(folder, root)})
            mn += 1
        else:
            feature_rows.append({"title": title, "number": milestones[title], "new": False})
        files = sorted(list(folder.glob("issues/*.md")) + list(folder.glob("issues/archive/*.md")),
                       key=lambda p: (p.name, p.parent.name))
        for f in files:
            rel = f.relative_to(root).as_posix()
            t = parse(f.read_text())
            t.update(path=rel, file=f, feature=name, folder=folder, project=name.split("/")[0])
            prev = state["moved"].get(key(rel))
            if prev:
                t["number"], t["done"] = prev["number"], prev["done"]
            else:
                t["number"], t["done"] = n, False
                n += 1
            # known names from every Repo: line, so bare names resolve
            for owner, rname in re.findall(rf"\b{own}/([\w.-]*\w)", t["meta"].get("Repo", "")):
                known.setdefault(rname, owner)
            tickets.append(t)
    numbers = {k: v["number"] for k, v in state["moved"].items()}
    numbers.update({key(t["path"]): t["number"] for t in tickets})
    folder_ms = {}
    for name, folder in feats:
        folder_ms[folder.relative_to(root).as_posix()] = milestones[name]
    # "checkout ticket 24" or "search's ticket 03" names another feature's ticket: left as written
    names = {p.parent.name for p in root.glob("*/tickets/")} | {p.name for p in root.glob("*/tickets/*/")}
    linker = Linker(root, numbers, folder_ms, known, names - {"archive"})

    report = {"unmapped": [], "blocked": [], "types": [], "no_repo": [], "no_org": [],
              "blockers_markdown": [], "blockers_unresolved": [], "too_long": []}
    by_path = {t["path"]: t for t in tickets}
    for t in tickets:
        meta, path = t["meta"], t["path"]
        word, note = split_status(meta.get("Status", ""))
        role, close, why = role_for(word, note, meta.get("Repo"))
        if path in decisions.get("status", {}):
            d = decisions["status"][path]
            role, close, why = (None, CLOSED_AS[d], "decisions file") if d in CLOSED_AS else (d, None, "decisions file")
        if role is None and close is None:
            report["unmapped"].append((path, meta.get("Status", "(no Status: line)")))
        elif word == "blocked" and why != "decisions file":
            report["blocked"].append((path, role, why))
        typ = (meta.get("Type") or "task").strip().lower()
        typ = decisions.get("type", {}).get(path, TYPE_ALIASES.get(typ, typ))
        if typ not in TYPES:
            report["types"].append((path, meta.get("Type"), "task"))
            typ = "task"
        elif meta.get("Type") and meta["Type"].lower() != typ:
            report["types"].append((path, meta["Type"], typ))
        if path in decisions.get("repos", {}):
            repos, rwhy = decisions["repos"][path], "decisions file"
        else:
            repos, rwhy = ticket_repos(meta.get("Repo"), t["project"], maps, known, owners)
        if not repos:
            report["no_repo"].append((path, rwhy))
        orgs = {r.split("/")[0] for r in repos} or {r.split("/")[0] for r in maps.get(t["project"], [])}
        t.update(role=role, close=close, repos=repos, orgs=orgs, type=typ)
    for t in tickets:
        if not t["orgs"]:  # no repo, no map: the org the project's other tickets work in
            t["orgs"] = {o for x in tickets if x["project"] == t["project"] for o in x["orgs"]}
            if len(t["orgs"]) != 1:
                report["no_org"].append(t["path"])
                t["orgs"] = set()
        prio = decisions.get("priority", {}).get(t["path"]) or decisions.get("priority", {}).get(t["feature"])
        t["labels"] = ([f"org:{o}" for o in sorted(t["orgs"])] + [f"project:{t['project']}"]
                       + [f"repo:{r.split('/')[1]}" for r in t["repos"]]
                       + ([f"status:{t['role']}"] if t["role"] else []) + [f"type:{t['type']}"]
                       + ([f"priority:{prio}"] if prio else []))
        whole = "\n".join([t["body"], *t["comments"], *t["meta"].values()])
        named = {}
        for owner, name, n in re.findall(rf"\b{own}/([\w.-]*\w)#(\d+)", whole):
            named.setdefault(n, set()).add(f"{owner}/{name}")
        for name, n in re.findall(r"(?<![\w/.-])([a-z][\w-]*\w)#(\d+)", whole):
            if name in known:
                named.setdefault(n, set()).add(f"{known[name]}/{name}")
        linker.qualified[t["path"]] = named

    for t in tickets:
        meta, path = t["meta"], t["path"]
        code_repo = decisions.get("pr_repo", {}).get(path) or (t["repos"][0] if len(t["repos"]) == 1 else None)
        feature_numbers = {Path(o["path"]).name[:2]: o["number"] for o in tickets if o["feature"] == t["feature"]}
        rw = lambda s: linker.rewrite(s, path, feature_numbers, code_repo)
        # blockers: GitHub links between open issues; the rest stays as text
        blocked_by, line = [], meta.get("Blocked by", "")
        if line and not NONE_BLOCKERS.fullmatch(line.strip()):
            refs, missing = blocker_refs(root, t["file"], line, numbers)
            report["blockers_unresolved"] += [(path, ref) for ref in missing]
            for r in refs:
                other = by_path.get(r) or next((o for o in tickets if key(o["path"]) == key(r)), None)
                if other:
                    is_open, num = other["close"] is None, other["number"]
                elif key(r) in numbers:
                    num = numbers[key(r)]
                    is_open = state["states"].get(num, "OPEN") == "OPEN"
                else:
                    if checker.read_status(root / r) not in checker.CLOSED:
                        report["blockers_markdown"].append((path, r))
                    continue
                if t["close"] is None and is_open:
                    blocked_by.append(num)
        head = []
        _, note = split_status(meta.get("Status", ""))
        if note:
            head.append(f"**Status note:** {rw(note)}")
        if line and not NONE_BLOCKERS.fullmatch(line.strip()):
            nums = {Path(o["path"]).name[:2]: o["number"] for o in tickets if o["feature"] == t["feature"]}
            text = rw(line)

            def raw_path(m):  # a bare path, as Blocked by: lines write them
                ref = m.group(0)
                found = linker.target(os.path.dirname(path), ref)
                if not found and checker.find_issue((t["file"].parent / ref).parent, ref):
                    found = linker.target(os.path.dirname(path), os.path.relpath(
                        checker.find_issue((t["file"].parent / ref).parent, ref), t["file"].parent))
                if not found:
                    return ref
                return f"#{found[1]}" if found[0] == "issue" else f"[`{found[2]}`]({found[1]})"

            text = re.sub(r"(?<![\w(`/.-])" + BLOCKER_PATH, raw_path, text)
            # bare numbers name this feature's tickets; asides in brackets are prose, left alone
            text = re.sub(r"(\([^()]*\))|(?<![\w/.#-])(\d\d)(?![\w/.-])",
                          lambda m: m.group(1) or (f"#{nums[m.group(2)]}" if m.group(2) in nums else m.group(2)), text)
            head.append(f"**Blocked by:** {text}")
        if meta.get("Repo"):
            head.append(f"**Repo:** {rw(meta['Repo'])}")
        head.append(f"**Moved from:** `{path}` on {args.date}")
        body = "\n".join(head) + "\n\n" + rw(t["body"]) + "\n"
        comments = [rw(c) + "\n" for c in t["comments"]]
        if len(body) > BODY_LIMIT or any(len(c) > BODY_LIMIT for c in comments):
            report["too_long"].append(path)
        t.update(body=body, comments_out=comments, blocked_by=sorted(set(blocked_by)))
    report["unresolved"] = linker.unresolved
    report["refs"] = outside_refs(root, tickets)
    want = sorted({l for t in tickets for l in t["labels"]})
    new_labels = [l for l in want if l not in state["labels"]]
    return {"tickets": tickets, "features": feature_rows, "new_labels": new_labels, "report": report,
            "known": known, "default_owner": default_owner}


def outside_refs(root: Path, tickets: list[dict]) -> list[tuple[str, int, str, int]]:
    """Lines in other files here that link to a ticket that moves: (file, line, ref, issue)."""
    moving = {key(t["path"]): t["number"] for t in tickets}
    own = {t["path"] for t in tickets}
    found = []
    for f in sorted(root.rglob("*.md")):
        rel = f.relative_to(root).as_posix()
        if rel in own or rel.startswith((".", "issues/")) or "/node_modules/" in rel:
            continue
        for i, line in enumerate(f.read_text(errors="replace").split("\n"), 1):
            for ref in re.findall(r"\]\(([^)\s#]+)|`([^`\s]+\.md)`", line):
                ref = ref[0] or ref[1]
                if "issues/" not in ref:
                    continue
                r = os.path.normpath(os.path.join(os.path.dirname(rel), ref))
                if key(r) in moving:
                    found.append((rel, i, ref, moving[key(r)]))
    return found


# --- dry run --------------------------------------------------------------------

def write_dry_run(plan: dict, out: Path, state: dict) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for t in plan["tickets"]:
        f = out / "tickets" / (t["path"].replace("/", "--"))
        f.parent.mkdir(parents=True, exist_ok=True)
        lines = [f"# #{t['number']}{' (already moved)' if t['done'] else ''}: {t['title']}", "",
                 f"- labels: {', '.join(t['labels'])}", f"- milestone: {t['feature']}",
                 f"- blocked by: {', '.join(f'#{b}' for b in t['blocked_by']) or 'none'}",
                 f"- closes: {t['close'] or 'no'}", "", "=" * 20 + " body", "", t["body"]]
        for k, c in enumerate(t["comments_out"], 1):
            lines += ["=" * 20 + f" comment {k}", "", c]
        f.write_text("\n".join(lines))
    json.dump({"numbers": {t["path"]: t["number"] for t in plan["tickets"]},
               "features": plan["features"], "new_labels": plan["new_labels"]},
              open(out / "plan.json", "w"), indent=1)
    (out / "report.md").write_text(render_report(plan, state))


def render_report(plan: dict, state: dict) -> str:
    ts, r = plan["tickets"], plan["report"]
    todo = [t for t in ts if not t["done"]]
    o = ["# Migration dry run", ""]
    o.append(f"{len(plan['features'])} features, {len(ts)} tickets ({len(ts) - len(todo)} already moved); "
             f"to move: {sum(1 for t in todo if not t['close'])} open, {sum(1 for t in todo if t['close'])} closed. "
             f"Issue numbers from #{state['next_issue']} are predicted.")
    o += ["", "| Project | Features | Open | Closed |", "| --- | --- | --- | --- |"]
    projects = sorted({t["project"] for t in todo})
    for p in projects:
        pt = [t for t in todo if t["project"] == p]
        o.append(f"| {p} | {len({t['feature'] for t in pt})} | {sum(1 for t in pt if not t['close'])} | "
                 f"{sum(1 for t in pt if t['close'])} |")
    status = Counter(t["role"] or f"closed {t['close']}" for t in todo)
    o += ["", "Statuses: " + ", ".join(f"{n} {s}" for s, n in status.most_common())]
    o += ["", f"## Labels to create ({len(plan['new_labels'])})", ""] + [f"- `{l}`" for l in plan["new_labels"]]
    new_ms = [f for f in plan["features"] if f["new"]]
    o += ["", f"## Milestones to create ({len(new_ms)})", ""]
    o += [f"- `{f['title']}` (#{f['number']}): {f['description']}" for f in new_ms]
    o += ["", f"## Unresolved links ({len(r['unresolved'])})", ""]
    o += [f"- `{p}`: {txt.replace(chr(10), ' ')} ({why})" for p, txt, why in r["unresolved"]]
    o += ["", f"## Unmapped statuses ({len(r['unmapped'])})", ""]
    o += [f"- `{p}`: {s}" for p, s in r["unmapped"]] or ["None."]
    o += ["", f"## Blocked tickets: the status each takes ({len(r['blocked'])})", ""]
    o += [f"- `{p}`: {role} ({why})" for p, role, why in r["blocked"]]
    o += ["", f"## Blockers staying markdown ({len(r['blockers_markdown'])}), or not found ({len(r['blockers_unresolved'])})", ""]
    o += [f"- `{p}` waits on `{b}` (open, not moving)" for p, b in r["blockers_markdown"]]
    o += [f"- `{p}`: blocker `{b}` names no ticket" for p, b in r["blockers_unresolved"]]
    o += ["", f"## Types changed ({len(r['types'])})", ""]
    o += [f"- `{p}`: {a} -> {b}" for p, a, b in r["types"]]
    o += ["", f"## No repo label ({len(r['no_repo'])})", ""]
    o += [f"- `{p}`: {why}" for p, why in r["no_repo"]]
    if r["no_org"]:
        o += ["", f"## No org label ({len(r['no_org'])})", ""] + [f"- `{p}`" for p in r["no_org"]]
    o += ["", "## Priority", "",
          f"None of the {sum(1 for t in todo if not t['close'])} open tickets has a priority (markdown has none), "
          "so they arrive with no priority label. issues.py reads that as later once triaged; give each one at "
          "its next triage, or list them in the decisions file's \"priority\"."]
    if r["too_long"]:
        o += ["", "## Too long for an issue", ""] + [f"- `{p}`" for p in r["too_long"]]
    o += ["", f"## Links elsewhere to tickets that move ({len(r['refs'])})", "",
          "Point these at the issue's URL once it exists (the dry run's numbers are predicted)."]
    o += [f"- `{f}:{i}` `{ref}` -> #{n}" for f, i, ref, n in r["refs"]]
    return "\n".join(o) + "\n"


# --- the real run -----------------------------------------------------------------

def label_colour(label: str) -> tuple[str, str]:
    group, _, v = label.partition(":")
    if group == "org":
        return COLOURS["org"], f"Work for {v} on GitHub"
    if group == "project":
        return COLOURS["project"], f"Notes folder: {v}"
    if group == "type":
        return COLOURS["type"], TYPE_DESC.get(v, v)
    return COLOURS.get(group, "ededed"), ""


def create_labels_and_milestones(plan: dict) -> None:
    known = plan["known"]
    for label in plan["new_labels"]:
        colour, desc = label_colour(label)
        if label.startswith("repo:"):
            name = label[5:]
            desc = f"Code lands in {known.get(name, plan['default_owner'])}/{name}"
        gh("label", "create", label, "--repo", REPO, "--color", colour, "--description", desc)
        print(f"label {label}")
    for f in plan["features"]:
        if f["new"]:
            got = gh("api", f"repos/{REPO}/milestones", "-f", f"title={f['title']}",
                     "-f", f"description={f['description']}", "--jq", ".number")
            print(f"milestone {f['title']} #{got}")


def run(plan: dict, out: Path, state: dict, date: str) -> None:
    """Move every ticket in the plan; labels and milestones exist by now."""
    out.mkdir(parents=True, exist_ok=True)
    mapfile = out / "map.json"
    done = json.loads(mapfile.read_text()) if mapfile.is_file() else {}
    done.update({t["path"]: t["number"] for t in plan["tickets"] if state["moved"].get(key(t["path"]))})
    mapfile.write_text(json.dumps(done, indent=1))
    tmp = out / "bodies"
    tmp.mkdir(exist_ok=True)
    fresh = [t for t in plan["tickets"] if not state["moved"].get(key(t["path"]))]
    for t in fresh:  # titles first, so every link can name its number
        pf = tmp / "placeholder.md"
        pf.write_text(f"**Moved from:** `{t['path']}` on {date}\n\n{PLACEHOLDER}\n")
        args = ["issue", "create", "--repo", REPO, "--title", t["title"], "--body-file", str(pf),
                "--milestone", t["feature"]]
        for l in t["labels"]:
            args += ["--label", l]
        n = int(gh(*args).rsplit("/", 1)[1])
        done[t["path"]] = n
        mapfile.write_text(json.dumps(done, indent=1))
        if n != t["number"]:
            sys.exit(f"{t['path']} became #{n}, not #{t['number']} (someone made an issue?): "
                     "links would be wrong; re-run to plan again from what's there")
        print(f"#{n} {t['title']}")
    for t in plan["tickets"]:
        if t["done"]:
            continue
        n = t["number"]
        now = gh_json("issue", "view", str(n), "-R", REPO, "--json", "body,comments,blockedBy,state")
        if PLACEHOLDER not in now["body"]:
            continue
        have = {b["number"] for b in (now.get("blockedBy") or {}).get("nodes", [])}
        for b in t["blocked_by"]:
            if b not in have:
                gh("issue", "edit", str(n), "--repo", REPO, "--add-blocked-by", str(b))
        for k, c in enumerate(t["comments_out"][len(now.get("comments", [])):], len(now.get("comments", []))):
            cf = tmp / f"{n}-c{k}.md"
            cf.write_text(c)
            gh("issue", "comment", str(n), "--repo", REPO, "--body-file", str(cf))
        if t["close"] and now["state"] == "OPEN":
            gh("issue", "close", str(n), "--repo", REPO, "--reason", t["close"])
        bf = tmp / f"{n}.md"
        bf.write_text(t["body"])
        gh("issue", "edit", str(n), "--repo", REPO, "--body-file", str(bf))
        print(f"#{n} moved{' and closed' if t['close'] else ''}")
    (out / "report.md").write_text(render_report(plan, state))
    print(f"\nDone. Next: remove the moved ticket files and fix the {len(plan['report']['refs'])} links "
          f"in {out / 'report.md'} ('Links elsewhere'), add any new Project/Code repo/Org options to the "
          f"board's fields, then run python3 {HERE / 'issues.py'} board and python3 {HERE / 'issues.py'} start-here.")


def main() -> None:
    p = argparse.ArgumentParser(description="Move markdown tickets to GitHub issues.")
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", metavar="OUT")
    mode.add_argument("--run", metavar="OUT")
    p.add_argument("--feature", action="append", default=[])
    p.add_argument("--include-archived", action="store_true")
    p.add_argument("--decisions")
    p.add_argument("--root", default=str(issues.NOTES_ROOT))
    p.add_argument("--date", default=datetime.date.today().isoformat())
    a = p.parse_args()
    decisions = json.loads(Path(a.decisions).read_text()) if a.decisions else {}
    root = Path(a.root).expanduser().resolve()
    configure(root)
    state = github_state()
    plan = build_plan(root, state, a, decisions)
    if a.dry_run:
        write_dry_run(plan, Path(a.dry_run), state)
        print(render_report(plan, state).split("\n## ")[0].strip())
        print(f"\nWrote {a.dry_run}/report.md and one file per ticket in {a.dry_run}/tickets/")
        return
    if plan["report"]["unmapped"]:
        sys.exit("Statuses with no issue status; give each one in --decisions first:\n" +
                 "\n".join(f"  {p}: {s}" for p, s in plan["report"]["unmapped"]))
    if plan["new_labels"] or any(f["new"] for f in plan["features"]):
        create_labels_and_milestones(plan)
        state = github_state()  # the milestones' real numbers, for links
        plan = build_plan(root, state, a, decisions)
    run(plan, Path(a.run), state, a.date)


if __name__ == "__main__":
    main()
