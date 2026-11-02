#!/usr/bin/env python3
"""Read tickets cheaply, find what links to them, and close them in one call.

Usage:
  python3 ticket.py show [--all] PATH...
  python3 ticket.py refs PATH
  python3 ticket.py set-status TICKET "STATUS TEXT"
  python3 ticket.py resolve TICKET --status "STATUS TEXT"
                    [--comment "TEXT" | --comment-file FILE] [--tick]
  python3 ticket.py archive [PATH...]

The notes repo is $NOTES_ROOT, or ~/code/ai-notes when that is unset. A
relative PATH is tried from the current folder, then from the notes repo.

show prints a ticket with its older comments hidden: everything above
`## Comments`, the last comment, and anything after the comments. It says how
many comments it hid. When the Status: line mentions comments, or with --all,
it prints them all. Use it to survey tickets; read the whole file before
working on one. PATH is a ticket file or a feature folder (every open ticket
in its issues/; closed ones are in issues/archive/).

A closed ticket (resolved or wontfix) lives in its feature's issues/archive/,
so issues/ shows only open work. set-status and resolve move the ticket to
the side its new status belongs on and fix every path to it in the repo.
archive does the same for every ticket under PATH (default: the whole repo).

refs lists the tickets whose Blocked by: line names PATH (a ticket file or a
feature folder), then every other line in this repo that mentions it.

set-status replaces the value of TICKET's Status: line (plain or bold, with
any wrapped lines under it) with STATUS TEXT, which starts with a status word
from triage-labels.md. resolve does the same, ticks every `- [ ]` box with
--tick, and appends the comment as the last entry under `## Comments`,
creating the heading at the end of the file if there is none. Both leave
every other byte of the file as it was. TICKET is one file in an issues/
folder. Tests: python3 test_ticket.py.
"""
import argparse
import importlib.util
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("check", HERE / "check-tickets.py")
check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check)
ROOT = check.ROOT
ARCHIVE = check.ARCHIVE

COMMENTS_RE = re.compile(r"^## Comments\s*$", re.M)
HEADING_RE = re.compile(r"^## ", re.M)
# A comment starts with its date, sometimes bold or as a list item.
ENTRY_RE = re.compile(r"^(?:- |\*\*)?\d{4}-\d{2}-\d{2}")
STATUS_LINE_RE = re.compile(r"^(?:\*\*)?Status:.*$", re.M)
SKIP_DIRS = {".git", ".claude"}


def resolve(arg: str) -> Path:
    """A path as given, or relative to the repo root."""
    for p in (Path(arg), ROOT / arg):
        if p.exists():
            return p.resolve()
    sys.exit(f"No such ticket or folder: {arg}")


def tickets_at(path: Path, archived: bool = False) -> list[Path]:
    """A ticket, or a feature's open tickets (and its closed ones if archived)."""
    if path.is_file():
        return [path]
    issues = path / "issues" if (path / "issues").is_dir() else path
    found = sorted(issues.glob("*.md"))
    if archived:
        found += sorted((issues / ARCHIVE).glob("*.md"))
    if not found:
        sys.exit(f"No open tickets in {path}")
    return found


def split_comments(body: str) -> list[str]:
    """Split a Comments section into entries, one per dated comment."""
    entries: list[list[str]] = []
    for line in body.splitlines():
        if ENTRY_RE.match(line) or not entries:
            if not line.strip() and not entries:
                continue
            entries.append([])
        entries[-1].append(line)
    return ["\n".join(e).strip() for e in entries if "".join(e).strip()]


def show(ticket: Path, everything: bool) -> None:
    text = ticket.read_text()
    print(f"== {ticket.relative_to(ROOT)}")
    m = COMMENTS_RE.search(text)
    if not m:
        print(text.strip())
        return
    head = text[: m.start()]
    rest = text[m.end():]
    nxt = HEADING_RE.search(rest)
    body, tail = (rest[: nxt.start()], rest[nxt.start():]) if nxt else (rest, "")
    entries = split_comments(body)

    status = STATUS_LINE_RE.search(head)
    points_at_comments = bool(
        status and re.search(r"\bcomments?\b", status.group(0), re.I)
    )
    if everything or points_at_comments or len(entries) <= 1:
        shown, note = entries, None
        if points_at_comments and len(entries) > 1 and not everything:
            note = f"(all {len(entries)} comments shown: the Status: line points to them)"
    else:
        shown = entries[-1:]
        note = (
            f"({len(entries) - 1} earlier comments hidden. Read the full file"
            " before working on this ticket.)"
        )
    if note:
        print(note)
    print(head.strip())
    print("\n## Comments\n")
    if shown is not entries and note:
        print(note + "\n")
    print("\n\n".join(shown))
    if tail.strip():
        print("\n" + tail.strip())


def refs(target: Path) -> None:
    targets = set(tickets_at(target, archived=True))
    feature = check.feature_of(target) if target.is_file() else target
    slug = re.escape(feature.name)
    if target.is_file():
        patterns = [rf"(?<![\w-]){slug}/issues/(?:{ARCHIVE}/)?{target.name[:2]}(?!\d)"]
    else:
        patterns = [
            rf"tickets/(?:archive/)?{slug}(?![\w-])",
            rf"(?<![\w-]){slug}/issues/",
        ]
    mention = re.compile("|".join(patterns))

    print(f"Blocked by {target.relative_to(ROOT)}:")
    blocked = []
    for t in check.all_tickets():
        if t in targets:
            continue
        m = check.BLOCKED_RE.search(t.read_text())
        if m and targets & set(check.blockers(t, m.group(1))[0]):
            blocked.append(f"  {check.read_status(t) or '(none)':16} {t.relative_to(ROOT)}")
    print("\n".join(blocked) if blocked else "  (none)")

    print("\nOther mentions:")
    inside = target if target.is_file() else feature
    hits = []
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT)
        if (
            p.suffix not in {".md", ".py", ".sh"}
            or SKIP_DIRS & set(rel.parts)
            or p == inside
            or p.is_relative_to(inside)
        ):
            continue
        for n, line in enumerate(p.read_text().splitlines(), 1):
            if mention.search(line) and not check.BLOCKED_RE.match(line):
                hits.append(f"  {rel}:{n}: {line.strip()[:160]}")
    print("\n".join(hits) if hits else "  (none)")


# The Status: line, plain or bold, and the wrapped lines under it: lines up to
# a blank line, a heading, a list item or the next `Field:` line.
STATUS_BLOCK_RE = re.compile(
    r"^(?P<label>(?:\*\*)?Status:(?:\*\*)?)[ \t]*[^\r\n]*"
    r"(?:\r?\n(?![ \t]*\r?\n|[ \t]*\r?$|#|[ \t]*[-*] |(?:\*\*)?[A-Z][\w -]*:)[^\r\n]*)*",
    re.M,
)
BOX_RE = re.compile(r"^([ \t]*[-*] )\[ \]", re.M)


class TicketError(Exception):
    pass


def is_ticket_path(p: Path) -> bool:
    """A .md file in issues/ or issues/archive/."""
    parent = p.parent.parent if p.parent.name == ARCHIVE else p.parent
    return p.suffix == ".md" and parent.name == "issues"


def ticket_file(arg: str) -> Path:
    """One ticket: an existing .md file in an issues/ folder."""
    for p in (Path(arg), ROOT / arg):
        if p.is_file():
            p = p.resolve()
            break
    else:
        raise TicketError(f"No such ticket file: {arg}")
    if not is_ticket_path(p):
        raise TicketError(f"Not a ticket (a .md file in an issues/ folder): {arg}")
    return p


def placed(ticket: Path, status: str | None) -> Path:
    """Where a ticket belongs: issues/archive/ when closed, issues/ when open.

    Tickets of an archived feature stay where they are.
    """
    if check.feature_of(ticket).parent.name == ARCHIVE:
        return ticket
    issues = ticket.parent.parent if ticket.parent.name == ARCHIVE else ticket.parent
    return (issues / ARCHIVE if status in check.CLOSED else issues) / ticket.name


# A path to a .md file, and (in a moved file) any path starting ./ or ../.
MD_PATH_RE = re.compile(r"(?<![\w./-])((?:\.{1,2}/)*[\w-][\w.-]*(?:/[\w.-]+)*\.md)(?![\w-])")
UP_PATH_RE = re.compile(r"(?<![\w./-])((?:\.{1,2}/)+[\w./-]*)")


def _norm(p: Path) -> Path:
    return Path(os.path.normpath(p))


def relink(moves: dict[Path, Path], root: Path = ROOT) -> list[Path]:
    """After moving files (old → new), fix every .md file's paths to them.

    A path is read the way it was written: relative to the file, to the repo
    root, or to the project folder; the new one is written the same way. The
    moved files' own relative paths are fixed too. Returns the files changed.
    """
    old_of = {new: old for old, new in moves.items()}
    changed = []
    for f in sorted(root.rglob("*.md")):
        if SKIP_DIRS & set(f.relative_to(root).parts):
            continue
        old_f = old_of.get(f, f)
        moved = f in old_of
        parts = old_f.relative_to(root).parts
        project = root / parts[0] if len(parts) > 1 else root

        def fix_md(m: re.Match) -> str:
            t = m.group(1)
            for base, rel in ((old_f.parent, True), (root, False), (project, False)):
                target = _norm(base / t)
                if target in moves:
                    new_target = moves[target]
                elif target.exists() and target not in old_of:
                    new_target = target
                else:
                    continue
                if new_target == target and not (rel and moved):
                    return t
                start = f.parent if rel else base
                new = os.path.relpath(new_target, start)
                if t.startswith("./") and not new.startswith("."):
                    new = "./" + new
                return new
            return t

        def fix_up(m: re.Match) -> str:
            t = m.group(1)
            core = t.rstrip(".")
            if core.endswith(".md") or core in {"", ".", ".."}:
                return t
            target = _norm(old_f.parent / core)
            if not target.exists():
                return t
            new = os.path.relpath(moves.get(target, target), f.parent)
            if core.endswith("/"):
                new += "/"
            return new + t[len(core):]

        text = f.read_bytes().decode("utf-8")
        new = MD_PATH_RE.sub(fix_md, text)
        if moved:
            new = UP_PATH_RE.sub(fix_up, new)
        if new != text:
            f.write_bytes(new.encode("utf-8"))
            changed.append(f)
    return changed


def move_tickets(moves: dict[Path, Path], root: Path = ROOT) -> list[Path]:
    """Move tickets, fix paths to them, and drop an archive/ left empty.

    Returns the other files whose paths were fixed.
    """
    moves = {_norm(a): _norm(b) for a, b in moves.items() if a != b}
    for old, new in moves.items():
        if new.exists():
            raise TicketError(f"Can't move {old.name}: {new} already exists")
    for old, new in moves.items():
        new.parent.mkdir(exist_ok=True)
        old.rename(new)
    changed = relink(moves, root)
    for old in moves:
        if old.parent.name == ARCHIVE and old.parent.is_dir() and not any(old.parent.iterdir()):
            old.parent.rmdir()
    return [f for f in changed if f not in moves.values()]


def file_by_status(path: Path) -> tuple[Path, list[Path]]:
    """Move one ticket to the side its Status: says.

    Returns where it is now and the other files whose paths were fixed.
    """
    dest = placed(path, check.read_status(path))
    if dest == path:
        return path, []
    return dest, move_tickets({path: dest})


def archive_cmd(paths: list[str]) -> int:
    """Move every ticket under PATHs to the side its status says."""
    scopes = [resolve(p) for p in paths] or [ROOT]
    moves = {}
    for t in check.all_tickets():
        if any(t.is_relative_to(s) for s in scopes):
            dest = placed(t, check.read_status(t))
            if dest != t:
                moves[t] = dest
    try:
        move_tickets(moves)
    except (TicketError, OSError) as e:
        print(f"ticket.py archive: {e}", file=sys.stderr)
        return 1
    for old, new in sorted(moves.items()):
        print(f"{old.relative_to(ROOT)} -> {new.relative_to(ROOT)}")
    print(f"{len(moves)} tickets moved.")
    return 0


def with_status(text: str, status: str) -> str:
    status = status.strip()
    if not status or "\n" in status:
        raise TicketError("The status text must be one non-empty line")
    word = re.match(r"[a-z-]+", status)
    if not word or word.group(0) not in check.STATUSES:
        raise TicketError(
            f"The status must start with one of: {', '.join(sorted(check.STATUSES))}"
        )
    m = STATUS_BLOCK_RE.search(text)
    if not m:
        raise TicketError("The ticket has no Status: line")
    return f"{text[: m.start()]}{m.group('label')} {status}{text[m.end():]}"


def with_comment(text: str, comment: str) -> str:
    comment = comment.strip("\n").rstrip()
    if not comment:
        raise TicketError("The comment is empty")
    m = COMMENTS_RE.search(text)
    if not m:
        return f"{text.rstrip(chr(10))}\n\n## Comments\n\n{comment}\n"
    nxt = HEADING_RE.search(text, m.end())
    end = nxt.start() if nxt else len(text)
    body = text[:end].rstrip("\n")
    after = f"\n\n{text[end:]}" if nxt else "\n"
    return f"{body}\n\n{comment}{after}"


def rewrite(path: Path, change) -> None:
    # Bytes in, bytes out, so line endings and the rest stay as they were.
    text = path.read_bytes().decode("utf-8")
    new = change(text)
    if new != text:
        path.write_bytes(new.encode("utf-8"))


def set_status(path: Path, status: str) -> None:
    rewrite(path, lambda t: with_status(t, status))


def resolve_ticket(path: Path, status: str, comment: str | None, tick: bool) -> None:
    def change(text: str) -> str:
        text = with_status(text, status)
        if tick:
            text = BOX_RE.sub(r"\1[x]", text)
        if comment is not None:
            text = with_comment(text, comment)
        return text

    rewrite(path, change)


def write_cmd(cmd: str, rest: list[str]) -> int:
    parser = argparse.ArgumentParser(prog=f"ticket.py {cmd}")
    parser.add_argument("ticket")
    if cmd == "set-status":
        parser.add_argument("status")
    else:
        parser.add_argument("--status", required=True)
        group = parser.add_mutually_exclusive_group()
        group.add_argument("--comment")
        group.add_argument("--comment-file")
        parser.add_argument("--tick", action="store_true")
    a = parser.parse_args(rest)
    try:
        path = ticket_file(a.ticket)
        if cmd == "set-status":
            set_status(path, a.status)
        else:
            comment = a.comment
            if a.comment_file:
                comment = Path(a.comment_file).read_text()
            resolve_ticket(path, a.status, comment, a.tick)
        moved_to, relinked = (
            file_by_status(path) if path.is_relative_to(ROOT) else (path, [])
        )
    except (TicketError, OSError) as e:
        print(f"ticket.py {cmd}: {e}", file=sys.stderr)
        return 1
    print(f"{cmd}: {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}")
    if moved_to != path:
        print(f"moved to {moved_to.relative_to(ROOT)}")
        for f in relinked:
            print(f"fixed paths in {f.relative_to(ROOT)}")
    return 0


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] not in {"show", "refs", "set-status", "resolve", "archive"}:
        print(__doc__.strip())
        return 2
    cmd, rest = args[0], args[1:]
    if cmd == "archive":
        return archive_cmd(rest)
    if cmd in {"set-status", "resolve"}:
        return write_cmd(cmd, rest)
    if cmd == "show":
        everything = "--all" in rest
        paths = [a for a in rest if a != "--all"]
        if not paths:
            sys.exit("show needs a ticket file or feature folder")
        first = True
        for arg in paths:
            for t in tickets_at(resolve(arg)):
                if not first:
                    print()
                show(t, everything)
                first = False
    else:
        if len(rest) != 1:
            sys.exit("refs needs one ticket file or feature folder")
        refs(resolve(rest[0]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
