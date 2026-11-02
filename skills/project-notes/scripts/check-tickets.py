#!/usr/bin/env python3
"""Check every ticket's Status: and Blocked by: lines, then list ready tickets.

Usage: python3 check-tickets.py [--ready | --summary] [FOLDER]

The notes repo is $NOTES_ROOT, or ~/code/ai-notes when that is unset.

Closed tickets live in their feature's issues/archive/ and open ones in
issues/; a ticket on the wrong side is a problem. `Blocked by:` refs are
found on either side.

Exits 1 when a ticket has a problem. --ready skips the problems and prints
only the tickets ready to work. --summary prints one line per feature with
its count of each status, and marks features whose tickets are all closed. FOLDER (such as
docker-infrastructure/tickets/backups) limits the output and the exit code to
tickets under it, and lists each of them with its status; blockers are still
resolved across the whole repo.
"""
import os
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(os.environ.get("NOTES_ROOT") or "~/code/ai-notes").expanduser().resolve()
TICKET_PY = Path(__file__).resolve().parent / "ticket.py"

# triage-labels.md, plus /wayfinder's `claimed`.
STATUSES = {
    "needs-triage", "needs-info", "ready-for-agent", "ready-for-human",
    "wontfix", "blocked", "resolved", "claimed",
}
CLOSED = {"resolved", "wontfix"}
# Display order for --summary.
ORDER = [
    "claimed", "ready-for-agent", "ready-for-human", "needs-triage",
    "needs-info", "blocked", "resolved", "wontfix",
]
READY = {"ready-for-agent", "ready-for-human"}
# Closed tickets move to <feature>/issues/archive/; finished features move to
# <project>/tickets/archive/.
ARCHIVE = "archive"

STATUS_RE = re.compile(r"^(?:\*\*)?Status:(?:\*\*)?\s*([a-z-]+)", re.M)
BLOCKED_RE = re.compile(r"^(?:\*\*)?Blocked by:(?:\*\*)?\s*(.*)$", re.M | re.I)
PATH_RE = re.compile(r"(?:\.\./|\./)?[\w./-]*issues/\d\d[\w.-]*")
NUM_RE = re.compile(r"(?<![\w/.-])(\d\d)(?![\w/.-])")


def issue_dirs(issues_dir: Path) -> list[Path]:
    """An issues/ folder and its archive/, whichever side the ref starts on."""
    if issues_dir.name == ARCHIVE:
        return [issues_dir, issues_dir.parent]
    return [issues_dir, issues_dir / ARCHIVE]


def find_issue(issues_dir: Path, ref: str) -> Path | None:
    """Resolve `NN`, `.../issues/NN` or `.../issues/NN-slug.md` to a file.

    A closed ticket moves to issues/archive/, so both folders are searched.
    """
    name = Path(ref).name
    number = name[:2]
    for d in issue_dirs(issues_dir):
        if name.endswith(".md") and (d / name).is_file():
            return (d / name).resolve()
        matches = sorted(d.glob(f"{number}-*.md"))
        if matches:
            return matches[0].resolve()
    return None


def feature_of(ticket: Path) -> Path:
    """The feature folder a ticket belongs to, archived ticket or not."""
    issues = ticket.parent
    if issues.name == ARCHIVE:
        issues = issues.parent
    return issues.parent


def blockers(ticket: Path, line: str) -> tuple[list[Path], list[str]]:
    """Return the blocking files a Blocked by: line names, and refs not found."""
    text = re.sub(r"\([^)]*\)", "", line)  # drop asides like "(Partner images)"
    found, missing = [], []
    for ref in PATH_RE.findall(text):
        target_dir = (ticket.parent / ref).parent
        hit = find_issue(target_dir, ref)
        (found.append(hit) if hit else missing.append(ref))
    for number in NUM_RE.findall(PATH_RE.sub("", text)):
        hit = find_issue(ticket.parent, number)
        (found.append(hit) if hit else missing.append(number))
    return found, missing


def all_tickets() -> list[Path]:
    """Every ticket file, archived ones included."""
    # Archived tickets and features are closed, but open tickets may still
    # name them as blockers, so they are read too.
    return sorted(
        p.resolve()
        for pattern in ("*/tickets/*/issues/*.md",
                        "*/tickets/*/issues/archive/*.md",
                        "*/tickets/archive/*/issues/*.md",
                        "*/tickets/archive/*/issues/archive/*.md")
        for p in ROOT.glob(pattern)
    )


def read_status(ticket: Path) -> str | None:
    m = STATUS_RE.search(ticket.read_text())
    return m.group(1) if m else None


def summary(tickets: list[Path], status: dict, scope: Path) -> int:
    """Print one line per feature: its count of tickets in each status."""
    show_archived = "archive" in scope.parts
    features: dict[Path, Counter] = {}
    archived = set()
    for t in tickets:
        feature = feature_of(t)
        if not t.is_relative_to(scope):
            continue
        if feature.parent.name == "archive" and not show_archived:
            archived.add(feature)
            continue
        features.setdefault(feature, Counter())[status[t] or "(none)"] += 1
    rank = {s: i for i, s in enumerate(ORDER)}
    for feature, counts in sorted(features.items()):
        parts = ", ".join(
            f"{n} {s}"
            for s, n in sorted(counts.items(), key=lambda kv: rank.get(kv[0], -1))
        )
        closed = set(counts) <= CLOSED and feature.parent.name != "archive"
        mark = "  [all closed: archive it]" if closed else ""
        total = sum(counts.values())
        print(f"{feature.relative_to(ROOT)} ({total}): {parts}{mark}")
    if archived:
        print(f"\n{len(archived)} archived features not shown.")
    return 0


def main() -> int:
    args = sys.argv[1:]
    ready_only = "--ready" in args
    folders = [a for a in args if not a.startswith("--")]
    scope = Path(folders[0]).resolve() if folders else ROOT
    if not scope.is_dir():
        print(f"No such folder: {folders[0]}")
        return 2
    tickets = all_tickets()
    status = {t: read_status(t) for t in tickets}
    if "--summary" in args:
        return summary(tickets, status, scope)

    problems, ready, listed = [], [], []
    for t in tickets:
        if not t.is_relative_to(scope):
            continue
        rel = t.relative_to(ROOT)
        s = status[t]
        listed.append(f"{s or '(none)':16} {rel}")
        if s is None:
            problems.append(f"{rel}: no Status: line")
            continue
        if s not in STATUSES:
            problems.append(f"{rel}: unknown status '{s}'")
            continue
        in_archive = t.parent.name == ARCHIVE
        if feature_of(t).parent.name != ARCHIVE:
            feature = feature_of(t).relative_to(ROOT)
            if s in CLOSED and not in_archive:
                problems.append(
                    f"{rel}: {s}, but still in issues/;"
                    f" run python3 {TICKET_PY} archive {feature}"
                )
            elif s not in CLOSED and in_archive:
                problems.append(
                    f"{rel}: {s}, but in issues/archive/;"
                    f" run python3 {TICKET_PY} archive {feature}"
                )
        m = BLOCKED_RE.search(t.read_text())
        found, missing = blockers(t, m.group(1)) if m else ([], [])
        for ref in missing:
            problems.append(f"{rel}: blocker '{ref}' names no ticket file")
        open_blockers = [b for b in found if status.get(b) not in CLOSED]
        if s == "blocked" and found and not open_blockers and not missing:
            problems.append(
                f"{rel}: blocked, but every blocker is closed;"
                " move it to ready-for-agent or ready-for-human"
            )
        # A ready ticket with open blockers is ready once they close.
        if s in READY and not open_blockers:
            ready.append(f"{s:16} {rel}")

    if folders and not ready_only:
        print("Tickets:")
        for line in listed:
            print(f"  {line}")
        print()
    if not ready_only:
        for p in problems:
            print(f"problem: {p}")
        if problems:
            print()
    print("Ready to work:" if ready else "No tickets ready to work.")
    for r in ready:
        print(f"  {r}")
    return 1 if problems and not ready_only else 0


if __name__ == "__main__":
    sys.exit(main())
