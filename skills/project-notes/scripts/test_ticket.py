#!/usr/bin/env python3
"""Tests for ticket.py's set-status and resolve. Run: python3 test_ticket.py"""
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "ticket.py"
_spec = importlib.util.spec_from_file_location("ticket", SCRIPT)
ticket = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ticket)

PLAIN = """# 03: A ticket

Status: ready-for-agent
Blocked by: 01

## What to build

- [ ] the first box
- [x] a box already done
  - [ ] a nested box

## Comments

**2026-10-28 (agent):** first comment.
"""

BOLD_WRAPPED = """# 04: Older ticket

**Blocked by:** None
**Status:** ready-for-human — waits on the
maintainer, who decides the
three gaps.

## Decisions

- [ ] one
"""


class TicketWrites(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.issues = Path(self.tmp.name) / "feature" / "issues"
        self.issues.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name: str, text: str) -> Path:
        p = self.issues / name
        p.write_bytes(text.encode())
        return p

    def run_cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-I", str(SCRIPT), *args],
            capture_output=True, text=True,
        )

    def test_set_status_plain_changes_only_the_line(self):
        p = self.write("03-a.md", PLAIN)
        r = self.run_cli("set-status", str(p), "blocked — on 02")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(
            p.read_text(),
            PLAIN.replace("Status: ready-for-agent", "Status: blocked — on 02"),
        )

    def test_set_status_bold_replaces_wrapped_lines(self):
        p = self.write("04-b.md", BOLD_WRAPPED)
        r = self.run_cli("set-status", str(p), "resolved — decided")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(p.read_text(), """# 04: Older ticket

**Blocked by:** None
**Status:** resolved — decided

## Decisions

- [ ] one
""")

    def test_resolve_ticks_and_appends_comment(self):
        p = self.write("03-a.md", PLAIN)
        r = self.run_cli(
            "resolve", str(p), "--status", "resolved — on f (abc1234)",
            "--comment", "**2026-10-30 (agent):** merged.", "--tick",
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(p.read_text(), """# 03: A ticket

Status: resolved — on f (abc1234)
Blocked by: 01

## What to build

- [x] the first box
- [x] a box already done
  - [x] a nested box

## Comments

**2026-10-28 (agent):** first comment.

**2026-10-30 (agent):** merged.
""")

    def test_resolve_comment_before_a_later_heading_without_tick(self):
        text = PLAIN + "\n## Notes\n\nkept\n"
        p = self.write("03-a.md", text)
        f = Path(self.tmp.name) / "c.md"
        f.write_text("**2026-10-30 (agent):** two\nlines.\n")
        r = self.run_cli("resolve", str(p), "--status", "resolved", "--comment-file", str(f))
        self.assertEqual(r.returncode, 0, r.stderr)
        out = p.read_text()
        self.assertIn("first comment.\n\n**2026-10-30 (agent):** two\nlines.\n\n## Notes\n\nkept\n", out)
        self.assertIn("- [ ] the first box", out)

    def test_resolve_creates_comments_heading(self):
        p = self.write("04-b.md", BOLD_WRAPPED)
        r = self.run_cli("resolve", str(p), "--status", "resolved", "--comment", "done")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(p.read_text().endswith("- [ ] one\n\n## Comments\n\ndone\n"))

    def test_crlf_and_other_bytes_kept(self):
        p = self.write("03-a.md", PLAIN.replace("\n", "\r\n"))
        r = self.run_cli("set-status", str(p), "blocked")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(
            p.read_bytes(),
            PLAIN.replace("\n", "\r\n").replace("ready-for-agent", "blocked").encode(),
        )

    def test_refuses_non_ticket_path(self):
        other = Path(self.tmp.name) / "notes.md"
        other.write_text(PLAIN)
        r = self.run_cli("set-status", str(other), "resolved")
        self.assertEqual(r.returncode, 1)
        self.assertIn("Not a ticket", r.stderr)
        self.assertEqual(other.read_text(), PLAIN)
        r = self.run_cli("set-status", str(self.issues / "99-none.md"), "resolved")
        self.assertEqual(r.returncode, 1)
        self.assertIn("No such ticket", r.stderr)

    def test_refuses_missing_status_line(self):
        text = "# 05: no status\n\n- [ ] box\n"
        p = self.write("05-c.md", text)
        r = self.run_cli("resolve", str(p), "--status", "resolved", "--tick")
        self.assertEqual(r.returncode, 1)
        self.assertIn("no Status: line", r.stderr)
        self.assertEqual(p.read_text(), text)

    def test_refuses_unknown_status_word(self):
        p = self.write("03-a.md", PLAIN)
        r = self.run_cli("set-status", str(p), "done")
        self.assertEqual(r.returncode, 1)
        self.assertIn("must start with", r.stderr)
        self.assertEqual(p.read_text(), PLAIN)


class ArchiveTickets(unittest.TestCase):
    """Closed tickets move to issues/archive/; paths to them follow."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.feature = self.root / "proj" / "tickets" / "feat"
        self.issues = self.feature / "issues"
        self.issues.mkdir(parents=True)
        (self.feature / "spec.md").write_text("# Spec\n")
        (self.root / "proj" / "research").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel: str, text: str) -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        return p

    def test_move_fixes_paths_in_and_to_the_ticket(self):
        done = self.write(
            "proj/tickets/feat/issues/01-done.md",
            "Status: resolved\nSpec: `../spec.md`, notes in ../../../research/.\n"
            "See [02](02-open.md).\n",
        )
        self.write(
            "proj/tickets/feat/issues/02-open.md",
            "Status: blocked\nBlocked by: [01](01-done.md)\n",
        )
        self.write(
            "proj/README.md",
            "Root style: proj/tickets/feat/issues/01-done.md\n"
            "Project style: tickets/feat/issues/01-done.md\n"
            "Untouched: tickets/feat/spec.md\n",
        )
        dest = self.issues / "archive" / "01-done.md"
        ticket.move_tickets({done: dest}, self.root)

        self.assertFalse(done.exists())
        self.assertEqual(
            dest.read_text(),
            "Status: resolved\nSpec: `../../spec.md`, notes in ../../../../research/.\n"
            "See [02](../02-open.md).\n",
        )
        self.assertEqual(
            (self.issues / "02-open.md").read_text(),
            "Status: blocked\nBlocked by: [01](archive/01-done.md)\n",
        )
        self.assertEqual(
            (self.root / "proj" / "README.md").read_text(),
            "Root style: proj/tickets/feat/issues/archive/01-done.md\n"
            "Project style: tickets/feat/issues/archive/01-done.md\n"
            "Untouched: tickets/feat/spec.md\n",
        )

    def test_reopening_moves_back_and_drops_empty_archive(self):
        arch = self.write("proj/tickets/feat/issues/archive/01-x.md", "Status: blocked\n")
        dest = ticket.placed(arch, "blocked")
        self.assertEqual(dest, self.issues / "01-x.md")
        ticket.move_tickets({arch: dest}, self.root)
        self.assertTrue(dest.exists())
        self.assertFalse((self.issues / "archive").exists())

    def test_placed(self):
        t = self.issues / "01-x.md"
        self.assertEqual(ticket.placed(t, "wontfix"), self.issues / "archive" / "01-x.md")
        self.assertEqual(ticket.placed(t, "ready-for-agent"), t)
        old = self.root / "proj" / "tickets" / "archive" / "feat" / "issues" / "01-x.md"
        self.assertEqual(ticket.placed(old, "resolved"), old)

    def test_blocker_number_found_in_archive(self):
        closed = self.write("proj/tickets/feat/issues/archive/01-done.md", "Status: resolved\n")
        t = self.write("proj/tickets/feat/issues/02-open.md", "Status: blocked\n")
        found, missing = ticket.check.blockers(t, "01")
        self.assertEqual((found, missing), ([closed], []))
        # And from inside archive/, back to an open ticket.
        found, _ = ticket.check.blockers(closed, "02")
        self.assertEqual(found, [t])


if __name__ == "__main__":
    unittest.main()
