#!/usr/bin/env python3
"""Tests for migrate-issues.py against a fake gh. Run: python3 test_migrate_issues.py

The fake is this file run as `test_migrate_issues.py fake-gh ARGS...`: it
answers the gh calls the migration makes from a JSON state file
(FAKE_GH_STATE), changes it for writes, and logs every call. Each test
builds a small notes tree, project-notes.json included, in a temp folder and
passes it as --root. The issues repo is jdoe/notes; the code is mostly acme's.
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "migrate-issues.py"
URL = "https://github.com/jdoe/notes/issues/"
WRITES = {("issue", "create"), ("issue", "edit"), ("issue", "comment"), ("issue", "close"), ("label", "create")}


# --- the fake gh ------------------------------------------------------------

def fake_gh(args: list[str]) -> None:
    path = os.environ["FAKE_GH_STATE"]
    st = json.loads(Path(path).read_text())
    st["log"].append(args)
    out, a = None, args

    def opt(name, default=None):
        return a[a.index(name) + 1] if name in a else default

    def save():
        Path(path).write_text(json.dumps(st))

    if a[:2] == ["issue", "list"]:
        out = [{"number": int(k), "state": v["state"], "body": v["body"]} for k, v in st["issues"].items()]
    elif a[:2] == ["pr", "list"]:
        out = []
    elif a[:2] == ["label", "list"]:
        out = [{"name": l} for l in st["labels"]]
    elif a[:2] == ["label", "create"]:
        st["labels"].append(a[2])
    elif a[0] == "api" and "-f" in a:
        fields = dict(x.split("=", 1) for x in a if "=" in x and not x.startswith("repos/"))
        n = max([m["number"] for m in st["milestones"]] + [0]) + 1
        st["milestones"].append({"number": n, **fields})
        save()
        print(n)
        return
    elif a[0] == "api":
        out = st["milestones"]
    elif a[:2] == ["issue", "create"]:
        st["creates"] += 1
        if st["creates"] > st.get("fail_after", 10 ** 6):
            save()
            sys.exit("fake gh: the connection stalled")
        n = max([int(k) for k in st["issues"]] + [0]) + 1
        labels = [a[i + 1] for i, x in enumerate(a) if x == "--label"]
        st["issues"][str(n)] = {"title": opt("--title"), "state": "OPEN", "labels": labels, "milestone": opt("--milestone"),
                                "body": Path(opt("--body-file")).read_text(), "comments": [], "blockedBy": []}
        save()
        print(URL + str(n))
        return
    elif a[:2] == ["issue", "view"]:
        i = st["issues"][a[2]]
        full = {"body": i["body"], "state": i["state"], "comments": [{"body": c} for c in i["comments"]],
                "blockedBy": {"nodes": [{"number": b, "state": st["issues"][str(b)]["state"]} for b in i["blockedBy"]],
                              "totalCount": len(i["blockedBy"])}}
        out = {k: full[k] for k in opt("--json").split(",")}
    elif a[:2] == ["issue", "edit"]:
        i = st["issues"][a[2]]
        if "--add-blocked-by" in a:
            i["blockedBy"].append(int(opt("--add-blocked-by")))
        if "--body-file" in a:
            i["body"] = Path(opt("--body-file")).read_text()
    elif a[:2] == ["issue", "comment"]:
        st["issues"][a[2]]["comments"].append(Path(opt("--body-file")).read_text())
    elif a[:2] == ["issue", "close"]:
        st["issues"][a[2]].update(state="CLOSED", reason=opt("--reason"))
    else:
        sys.exit(f"fake gh: no answer for {a}")
    save()
    if out is not None:
        print(json.dumps(out))


# --- the notes tree -----------------------------------------------------------

TREE = {
    "project-notes.json": '{"issues_repo": "jdoe/notes"}\n',
    "tools/README.md": """\
        # Tools

        | Codebase | Role | Where work lands | Tooling | Its own notes |
        | --- | --- | --- | --- | --- |
        | dotfiles (`~/code/jdoe/dotfiles`) | Dotfiles | main | none | README |
        """,
    "web/README.md": """\
        # Web

        | Codebase | Role | Where work lands | Tooling | Its own notes |
        | --- | --- | --- | --- | --- |
        | `acme/site` (`~/code/acme/site`) | The site | A branch | npm | README |
        | lib (`~/code/acme/lib`) | The library | A branch | npm | README |

        Notes.
        """,
    "web/notes.md": "See [the plain ticket](tickets/feat/issues/01-plain.md).\n",
    "web/tickets/feat/spec.md": "# Feat\n\nStatus: ready-for-agent\n\nMake the [site](../../README.md) faster. More later.\n",
    "web/tickets/feat/issues/01-plain.md": """\
        # 01: Plain ticket

        Status: ready-for-agent
        Type: grilling
        Repo: acme/site
        Blocked by: None (can start immediately)

        Read [the spec](../spec.md) and `../spec.md`; PR #41 and lib#3 matter, and ticket 02 follows.
        The old one is [moved](../../../../other/tickets/old/issues/01-old.md). Missing [gone](../nope.md).
        A colour #1d76db, and in code `#12`:

        ```
        #13 stays
        ```

        ## Comments

        - 2026-10-01 (agent): first
          continued
        - 2026-10-02: second
        """,
    "web/tickets/feat/issues/02-bold.md": """\
        # 02 Bold ticket

        **What to build:** Things, after [01](01-plain.md).

        **Blocked by:** 01, ../../other-feat/issues/01-x.md

        **Repo:** `acme/lib`, branch `x`

        **Status:** blocked — waits on 01; ready-for-human once it resolves

        - [ ] a box

        ## Comments

        **2026-10-03 (agent):** bold one
        - 2026-10-03 a dated list line inside it

        **2026-10-04 (maintainer):** two
        """,
    "web/tickets/feat/issues/archive/03-done.md": """\
        # 03: Done

        Status: resolved — merged, PR #9
        Type: build
        Repo: acme/site
        Blocked by: None

        Done work.
        """,
    "web/tickets/feat/issues/04-odd.md": "# 04: Odd\n\nStatus: claimed\nRepo: acme/site\n\nWho knows.\n",
    "web/tickets/feat/issues/05-hands.md": """\
        # 05: By hand

        **Blocked by:** 03

        **Repo:** none (hand steps in the CMS)

        **Status:** blocked

        Click things.
        """,
    "web/tickets/other-feat/issues/01-x.md": "# 01: X\n\nStatus: ready-for-agent\nRepo: acme/site\n\nX.\n",
    "web/tickets/archive/oldfeat/issues/archive/01-a.md": "# 01: A\n\nStatus: resolved\nRepo: acme/site\n\nA.\n",
}
PATHS = {  # predicted and real numbers: #5 is taken, features sort, tickets by name
    6: "web/tickets/feat/issues/01-plain.md", 7: "web/tickets/feat/issues/02-bold.md",
    8: "web/tickets/feat/issues/archive/03-done.md", 9: "web/tickets/feat/issues/04-odd.md",
    10: "web/tickets/feat/issues/05-hands.md", 11: "web/tickets/other-feat/issues/01-x.md",
}


def world():
    return {"issues": {"5": {"title": "Old", "state": "OPEN", "labels": [], "milestone": "other/old", "comments": [],
                             "blockedBy": [], "body": "**Moved from:** `other/tickets/old/issues/01-old.md` on 2026-11-07\n\nOld.\n"}},
            "labels": ["org:acme", "repo:site", "status:ready-for-agent", "status:ready-for-human",
                       "status:needs-triage", "type:task"],
            "milestones": [{"number": 1, "title": "other/old", "description": ""}], "log": [], "creates": 0}


def load_module():
    spec = importlib.util.spec_from_file_location("migrate_issues", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Migrate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.root, self.out, self.state = t / "notes", t / "out", t / "state.json"
        for rel, text in TREE.items():
            f = self.root / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(textwrap.dedent(text))
        self.save(world())
        self.decisions = t / "decisions.json"
        self.decisions.write_text(json.dumps({"status": {PATHS[9]: "needs-triage"}}))

    def tearDown(self):
        self.tmp.cleanup()

    def save(self, st):
        self.state.write_text(json.dumps(st))

    def st(self):
        return json.loads(self.state.read_text())

    def run_cli(self, *args: str) -> subprocess.CompletedProcess:
        env = dict(os.environ, FAKE_GH_STATE=str(self.state),
                   ISSUES_GH=f"{sys.executable} -I {Path(__file__).resolve()} fake-gh")
        return subprocess.run([sys.executable, "-I", str(SCRIPT), "--root", str(self.root), "--date", "2026-11-08", *args],
                              capture_output=True, text=True, env=env)

    def ok(self, *args: str) -> str:
        r = self.run_cli(*args)
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        return r.stdout

    def dry(self, *args):
        self.ok("--dry-run", str(self.out), *args)
        return (self.out / "report.md").read_text()

    def ticket_file(self, n):
        return (self.out / "tickets" / PATHS[n].replace("/", "--")).read_text()

    def writes(self):
        return [c for c in self.st()["log"] if tuple(c[:2]) in WRITES or (c[0] == "api" and "-f" in c)]

    # --- dry run ---

    def test_dry_run_changes_nothing_and_reports(self):
        report = self.dry()
        self.assertEqual(self.writes(), [])
        self.assertIn("2 features, 6 tickets (0 already moved); to move: 5 open, 1 closed", report)
        self.assertIn("| web | 2 | 5 | 1 |", report)
        for label in ("project:web", "repo:lib", "type:grilling"):
            self.assertIn(f"- `{label}`", report)
        self.assertNotIn("- `repo:site`", report)  # exists already
        self.assertIn("- `web/feat` (#2): Make the site faster. Spec: https://github.com/jdoe/notes/blob/main/"
                      "web/tickets/feat/spec.md", report)
        self.assertIn("- `web/other-feat` (#3): No spec.", report)
        self.assertIn(f"- `{PATHS[9]}`: claimed", report)  # unmapped
        self.assertIn(f"- `{PATHS[6]}`: [gone](../nope.md) (links a file", report)
        self.assertIn(f"- `{PATHS[7]}`: ready-for-human (blocked; its status note names it)", report)
        self.assertIn(f"- `{PATHS[10]}`: ready-for-human (blocked; Repo: none", report)
        self.assertIn(f"- `{PATHS[10]}`: Repo: none (hand steps in the CMS)", report)  # no repo label
        self.assertIn(f"- `{PATHS[8]}`: build -> task", report)
        self.assertIn("- `web/notes.md:1` `tickets/feat/issues/01-plain.md` -> #6", report)
        self.assertIn("5 open tickets has a priority", report.replace("None of the ", ""))

    def test_dry_run_bodies_plain_format(self):
        self.dry()
        f = self.ticket_file(6)
        self.assertIn("# #6: Plain ticket", f)
        self.assertIn("- labels: org:acme, project:web, repo:site, status:ready-for-agent, type:grilling", f)
        self.assertIn("- milestone: web/feat", f)
        self.assertIn("**Repo:** acme/site\n**Moved from:** `web/tickets/feat/issues/01-plain.md` on 2026-11-08", f)
        self.assertNotIn("Blocked by:", f)  # none
        self.assertIn("[the spec](https://github.com/jdoe/notes/blob/main/web/tickets/feat/spec.md)", f)
        self.assertIn("[`web/tickets/feat/spec.md`](https://github.com/jdoe/notes/blob/main/web/tickets/feat/spec.md)", f)
        self.assertIn("PR acme/site#41 and acme/lib#3 matter, and ticket #7 follows", f)
        self.assertIn("The old one is moved (#5)", f)  # an already-moved ticket, by its Moved from line
        self.assertIn("A colour #1d76db, and in code `#12`", f)
        self.assertIn("#13 stays", f)
        self.assertIn("==== comment 1\n\n**2026-10-01 (agent):** first\ncontinued", f)
        self.assertIn("==== comment 2\n\n**2026-10-02:** second", f)

    def test_dry_run_bodies_bold_format_blockers_and_closed(self):
        self.dry()
        f = self.ticket_file(7)
        self.assertIn("labels: org:acme, project:web, repo:lib, status:ready-for-human, type:task", f)
        self.assertIn("- blocked by: #6, #11", f)  # within the feature and across
        self.assertIn("**Status note:** waits on 01; ready-for-human once it resolves", f)
        self.assertIn("**Blocked by:** #6, #11", f)
        self.assertIn("**What to build:** Things, after #6.", f)
        self.assertNotIn("**Status:**", f)
        self.assertIn("**2026-10-03 (agent):** bold one\n- 2026-10-03 a dated list line inside it", f)
        self.assertIn("==== comment 2\n\n**2026-10-04 (maintainer):** two", f)
        self.assertNotIn("comment 3", f)
        done = self.ticket_file(8)
        self.assertIn("- closes: completed", done)
        self.assertNotIn("status:", done.split("\n")[2])
        self.assertIn("**Status note:** merged, PR acme/site#9", done)
        hands = self.ticket_file(10)
        self.assertIn("labels: org:acme, project:web, status:ready-for-human, type:task", hands)
        self.assertIn("- blocked by: none", hands)  # its blocker is closed: text only
        self.assertIn("**Blocked by:** #8", hands)

    def test_archived_features_only_on_request(self):
        self.assertNotIn("oldfeat", self.dry())
        self.assertIn("`web/oldfeat`", self.dry("--include-archived"))

    def test_one_feature(self):
        report = self.dry("--feature", "web/other-feat")
        self.assertIn("1 features, 1 tickets", report)

    # --- the real run ---

    def test_run_refuses_unmapped_status(self):
        r = self.run_cli("--run", str(self.out))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("04-odd.md: claimed", r.stderr)
        self.assertEqual(self.writes(), [])

    def test_run_moves_everything(self):
        out = self.ok("--run", str(self.out), "--decisions", str(self.decisions))
        st = self.st()
        self.assertIn("project:web", st["labels"])
        self.assertIn("type:grilling", st["labels"])
        self.assertEqual([m["title"] for m in st["milestones"]], ["other/old", "web/feat", "web/other-feat"])
        self.assertIn("Spec: https://github.com/jdoe/notes/blob/main/web/tickets/feat/spec.md",
                      st["milestones"][1]["description"])
        iss = st["issues"]
        self.assertEqual({int(k) for k in iss}, {5} | set(PATHS))
        self.assertEqual(iss["6"]["title"], "Plain ticket")
        self.assertEqual(iss["6"]["milestone"], "web/feat")
        self.assertIn("ticket #7 follows", iss["6"]["body"])
        self.assertNotIn("Moving:", iss["6"]["body"])
        self.assertEqual(len(iss["6"]["comments"]), 2)
        self.assertEqual(sorted(iss["7"]["blockedBy"]), [6, 11])
        self.assertEqual(iss["10"]["blockedBy"], [])
        self.assertEqual((iss["8"]["state"], iss["8"]["reason"]), ("CLOSED", "completed"))
        self.assertIn("status:needs-triage", iss["9"]["labels"])  # from the decisions file
        self.assertEqual(json.loads((self.out / "map.json").read_text())[PATHS[11]], 11)
        self.assertIn("issues.py board", out)
        self.assertIn("issues.py start-here", out)
        made = {c[2]: c[c.index("--description") + 1] for c in st["log"] if c[:2] == ["label", "create"]}
        self.assertEqual(made["project:web"], "Notes folder: web")
        self.assertEqual(made["repo:lib"], "Code lands in acme/lib")
        self.assertEqual(made["type:grilling"], "A decision to settle with the maintainer")

    def test_owners_come_from_the_repo_maps(self):
        m = load_module()
        m.configure(self.root)
        state = {"moved": {}, "states": {}, "labels": {"repo:legacy"}, "milestones": {},
                 "next_issue": 1, "next_milestone": 1}
        args = types.SimpleNamespace(feature=[], include_archived=False, date="2026-11-08")
        plan = m.build_plan(self.root, state, args, {})
        self.assertEqual(m.REPO, "jdoe/notes")
        self.assertEqual(plan["known"]["dotfiles"], "jdoe")  # a bare name and its ~/code path
        self.assertEqual(plan["known"]["site"], "acme")
        self.assertEqual(plan["default_owner"], "acme")  # two of the three mapped repos
        self.assertEqual(plan["known"]["legacy"], "acme")  # a repo: label no map names
        self.assertEqual(m.label_colour("org:acme")[1], "Work for acme on GitHub")

    def test_needs_the_config(self):
        (self.root / "project-notes.json").unlink()
        r = self.run_cli("--dry-run", str(self.out))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("project-notes.json", r.stderr)
        self.assertEqual(self.st()["log"], [])

    def test_rerun_skips_moved_tickets(self):
        self.ok("--run", str(self.out), "--decisions", str(self.decisions))
        before = len(self.writes())
        self.ok("--run", str(self.out), "--decisions", str(self.decisions))
        self.assertEqual(len(self.writes()), before)
        self.assertIn("6 tickets (6 already moved)", self.dry())

    def test_stopped_run_resumes(self):
        st = self.st()
        st["fail_after"] = 2
        self.save(st)
        self.assertNotEqual(self.run_cli("--run", str(self.out), "--decisions", str(self.decisions)).returncode, 0)
        self.assertEqual(len(self.st()["issues"]), 3)  # #5 and the two made before the stall
        st = self.st()
        st["fail_after"] = 10 ** 6
        self.save(st)
        self.ok("--run", str(self.out), "--decisions", str(self.decisions))
        iss = self.st()["issues"]
        self.assertEqual(sorted(i["title"] for i in iss.values()),
                         sorted(["Old", "Plain ticket", "Bold ticket", "Done", "Odd", "By hand", "X"]))
        self.assertTrue(all("Moving:" not in i["body"] for i in iss.values()))
        # stopped part-way through one issue: only what's missing is done
        st = self.st()
        st["issues"]["6"]["body"] = st["issues"]["6"]["body"].split("\n\n")[0] + "\n\n(Moving: the rest of this issue follows.)\n"
        st["issues"]["6"]["comments"] = st["issues"]["6"]["comments"][:1]
        self.save(st)
        self.ok("--run", str(self.out), "--decisions", str(self.decisions))
        i6 = self.st()["issues"]["6"]
        self.assertEqual(len(i6["comments"]), 2)
        self.assertIn("**2026-10-02:** second", i6["comments"][1])
        self.assertIn("ticket #7 follows", i6["body"])


class Parsing(unittest.TestCase):
    m = load_module()

    def test_status_words(self):
        role = self.m.role_for
        self.assertEqual(role("resolved", "", None)[:2], (None, "completed"))
        self.assertEqual(role("wontfix", "", None)[:2], (None, "not planned"))
        self.assertEqual(role("blocked", "", "acme/x")[0], "ready-for-agent")
        self.assertEqual(role("blocked", "needs-triage first, then ready-for-agent", "x")[0], "needs-triage")
        self.assertEqual(role("in-progress", "", None)[:2], (None, None))
        self.assertEqual(self.m.split_status("ready-for-agent."), ("ready-for-agent", ""))
        self.assertEqual(self.m.split_status("blocked — waits on 02"), ("blocked", "waits on 02"))

    def test_repo_lines(self):
        known = {"storefront": "acme", "shop-lib": "acme", "dotfiles": "jdoe"}
        repos = lambda line: self.m.ticket_repos(line, "p", {}, known)[0]
        self.assertEqual(repos("acme/storefront; shop-lib (renamed field only)"),
                         ["acme/storefront", "acme/shop-lib"])
        self.assertEqual(repos("`acme/admin`, PR acme/admin#29 from `x`"), ["acme/admin"])
        self.assertEqual(repos("none (the notes repo); reads acme/storefront"), [])
        self.assertEqual(repos("to decide (the planned chat-bot, `acme/admin`)"), [])
        self.assertEqual(repos("dotfiles"), ["jdoe/dotfiles"])
        self.assertEqual(repos("someone/else and apps/web"), [])  # owners the maps don't name
        self.assertEqual(self.m.ticket_repos(None, "p", {"p": ["acme/a"]}, known)[0], ["acme/a"])

    def test_comment_styles(self):
        split = self.m.split_comments
        self.assertEqual(split("Grilled with the maintainer.\n\n- a point\n"), ["Grilled with the maintainer.\n\n- a point"])
        self.assertEqual(split("2026-10-21: Briefing first.\n\n2026-10-22: then this.\n"),
                         ["**2026-10-21:** Briefing first.", "**2026-10-22:** then this."])


if __name__ == "__main__":
    if sys.argv[1:2] == ["fake-gh"]:
        fake_gh(sys.argv[2:])
    else:
        unittest.main()
