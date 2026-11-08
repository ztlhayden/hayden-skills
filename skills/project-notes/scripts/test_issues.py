#!/usr/bin/env python3
"""Tests for issues.py against a fake gh. Run: python3 test_issues.py

The fake is this file run as `test_issues.py fake-gh ARGS...`: it answers the
gh calls issues.py makes from a JSON state file (FAKE_GH_STATE), changes it
for edits, and logs every call. Each test writes a project-notes.json into a
temp folder and passes it as NOTES_ROOT.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "issues.py"
REPO_URL = "https://github.com/acme/notes/issues/"
CONFIG = {"issues_repo": "acme/notes", "board": {"owner": "acme", "number": 3}, "start_here": 8,
          "goals": [{"text": "Ship the new checkout"}, {"text": "Move to issues", "milestone": "shop/checkout"}]}
FIELDS = {"Triage": ["needs-triage", "needs-info", "ready-for-agent", "ready-for-human", "in-progress-me", "in-progress-agent"],
          "Project": ["shop", "blog"], "Org": ["acme"], "Code repo": ["storefront"],
          "Status": ["Todo", "In Progress", "Done"]}


# --- the fake gh ------------------------------------------------------------

def fake_gh(args: list[str]) -> None:
    path = os.environ["FAKE_GH_STATE"]
    st = json.loads(Path(path).read_text())
    st["log"].append(args)
    out = None
    # A queued failure ({"match": [args prefix], "stderr": "..."}) answers the next matching call.
    fail = next((f for f in st.get("fail", []) if args[:len(f["match"])] == f["match"]), None)
    if fail:
        st["fail"].remove(fail)
        Path(path).write_text(json.dumps(st))
        sys.exit(fail["stderr"])

    def opt(name, default=None):
        return args[args.index(name) + 1] if name in args else default

    def render(n: int) -> dict:
        i = st["issues"][str(n)]
        node = lambda b: {"number": b, "state": st["issues"][str(b)]["state"]} if str(b) in st["issues"] else {"number": b, "state": "OPEN"}
        blocking = [int(k) for k, v in st["issues"].items() if n in v.get("blockedBy", [])]
        full = {"number": n, "title": i["title"], "state": i["state"], "stateReason": i.get("stateReason", ""),
                "url": REPO_URL + str(n), "labels": [{"name": l} for l in i["labels"]],
                "milestone": {"title": i["milestone"]} if i.get("milestone") else None,
                "blockedBy": {"nodes": [node(b) for b in i.get("blockedBy", [])], "totalCount": len(i.get("blockedBy", []))},
                "blocking": {"nodes": [node(b) for b in sorted(blocking)], "totalCount": len(blocking)},
                "body": i.get("body", ""), "comments": i.get("comments", [])}
        return {k: full[k] for k in opt("--json").split(",")}

    a = args
    if a[:2] == ["issue", "list"]:
        want = opt("--state", "open")
        words = (opt("--search") or "").lower().split()
        out = [render(int(k)) for k, v in sorted(st["issues"].items(), key=lambda kv: int(kv[0]))
               if (want == "all" or v["state"] == want.upper()) and all(w in v["title"].lower() for w in words)]
    elif a[:2] == ["issue", "create"]:
        n = str(max(int(k) for k in st["issues"]) + 1)
        labels = [v for k, v in zip(a, a[1:]) if k == "--label"]
        st["issues"][n] = {"title": opt("--title"), "state": "OPEN", "labels": labels, "milestone": opt("--milestone"),
                           "blockedBy": [], "body": Path(opt("--body-file")).read_text(), "comments": []}
        print(REPO_URL + n)
    elif a[:2] == ["issue", "view"]:
        out = render(int(a[2]))
    elif a[:2] == ["issue", "edit"]:
        i = st["issues"][a[2]]
        for k, v in zip(a, a[1:]):
            if k == "--remove-label":
                i["labels"].remove(v)
            elif k == "--add-label":
                i["labels"].append(v)
            elif k == "--body-file":
                i["body"] = Path(v).read_text()
            elif k == "--add-blocked-by":
                i.setdefault("blockedBy", []).append(int(v))
            elif k == "--remove-blocked-by":
                i["blockedBy"].remove(int(v))
    elif a[:2] == ["issue", "comment"]:
        st["issues"][a[2]].setdefault("comments", []).append(
            {"author": {"login": "maintainer"}, "createdAt": "2026-11-07T00:00:00Z", "body": Path(opt("--body-file")).read_text()})
    elif a[:2] == ["issue", "close"]:
        st["issues"][a[2]].update(state="CLOSED", stateReason=opt("--reason").upper().replace(" ", "_"))
    elif a[:2] == ["label", "list"]:
        out = [{"name": l} for l in st["labels"]]
    elif a[:2] == ["label", "create"]:
        st["labels"].append(a[2])
    elif a[:2] == ["api", "graphql"]:
        n = int(dict(v.split("=", 1) for k, v in zip(a, a[1:]) if k == "-F")["n"])
        i = st["issues"][str(n)]
        other = {"id": f"X-{n}", "project": {"number": 9, "owner": {"login": "acme"}},  # another board's item
                 "fieldValues": {"nodes": [{"name": "Done", "field": {"name": "Status"}}]}}
        nodes = [other]
        if str(n) in st["items"]:
            item = st["items"][str(n)]
            nodes.append({"id": item["id"], "project": {"number": 3, "owner": {"login": "acme"}},
                          "fieldValues": {"nodes": [{}] + [{"name": item[f.lower()], "field": {"name": f}}
                                                           for f in FIELDS if f.lower() in item]}})
        out = {"data": {"repository": {"issue": {
            "number": n, "url": REPO_URL + str(n), "state": i["state"],
            "labels": {"nodes": [{"name": l} for l in i["labels"]]}, "projectItems": {"nodes": nodes}}}}}
    elif a[:2] == ["api", "rate_limit"]:
        out = {"resources": {"core": {"remaining": 4000, "reset": 0}, "graphql": {"remaining": 0, "reset": 0}}}
    elif a[0] == "api" and "-f" in a:
        st["milestones"].append(opt("-f").split("=", 1)[1])
    elif a[0] == "api":
        out = [{"title": m} for m in st["milestones"]]
    elif a[:2] == ["project", "view"]:
        out = {"id": "P1", "title": "Acme work", "url": "https://github.com/users/acme/projects/3", "public": False}
    elif a[:2] == ["project", "field-list"]:
        out = {"fields": [{"id": f"F-{name}", "name": name, "options": [{"id": f"O-{o}", "name": o} for o in opts]}
                          for name, opts in FIELDS.items()]}
    elif a[:2] == ["project", "item-list"]:
        out = {"items": list(st["items"].values())}
    elif a[:2] == ["project", "item-add"]:
        n = opt("--url").rsplit("/", 1)[1]
        st["items"][n] = out = {"id": f"I-{n}", "content": {"number": int(n)}}
    elif a[:2] == ["project", "item-edit"]:
        item = next(i for i in st["items"].values() if i["id"] == opt("--id"))
        field, option = opt("--field-id")[2:], opt("--single-select-option-id")[2:]
        if opt("--project-id") != "P1" or option not in FIELDS.get(field, []):
            sys.exit("GraphQL: Could not resolve to a node with the global id")
        item[field.lower()] = option
    else:
        sys.exit(f"fake gh: no answer for {a}")
    Path(path).write_text(json.dumps(st))
    if out is not None:
        print(json.dumps(out))


# --- the tests ------------------------------------------------------------

def iss(title, status, prio=None, blocked=(), milestone="shop/checkout", state="OPEN", comments=()):
    labels = ["org:acme", "project:shop", "repo:storefront", "type:task"]
    if status:
        labels.append(f"status:{status}")
    if prio:
        labels.append(f"priority:{prio}")
    return {"title": title, "state": state, "labels": labels, "milestone": milestone, "blockedBy": list(blocked),
            "body": f"Body of {title}.", "comments": [{"author": {"login": "maintainer"}, "createdAt": f"2026-11-0{k + 1}T00:00:00Z",
                                                        "body": c} for k, c in enumerate(comments)]}


def world():
    return {
        "1": iss("Done long ago", None, "soon", state="CLOSED"),
        "2": iss("Helper", "ready-for-agent", "soon"),
        "3": iss("Uses the helper", "ready-for-agent", "soon", blocked=[2]),
        "4": iss("Urgent, waits on a person", "ready-for-agent", "now", blocked=[3, 5]),
        "5": iss("Maintainer decides", "ready-for-human", None),
        "6": iss("Blocker closed", "ready-for-agent", "soon", blocked=[1]),
        "7": iss("Loop a", "ready-for-agent", "soon", blocked=[8], milestone="blog/comments"),
        "8": iss("Loop b", "ready-for-agent", "soon", blocked=[7], milestone="blog/comments"),
        "9": iss("Someone's on it", "in-progress-me", "soon", comments=["first", "second", "third"]),
        "10": iss("Not triaged", "needs-triage", None, milestone=None),
    }


class Issues(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.notes = Path(self.tmp.name) / "notes"
        self.notes.mkdir()
        self.config(CONFIG)
        self.state = Path(self.tmp.name) / "state.json"
        self.save({"issues": world(), "log": [], "items": {},
                   "labels": ["bug", "org:acme", "project:shop", "project:blog", "repo:storefront"],
                   "milestones": ["blog/comments", "shop/checkout"]})

    def tearDown(self):
        self.tmp.cleanup()

    def config(self, cfg):
        (self.notes / "project-notes.json").write_text(json.dumps(cfg))

    def save(self, st):
        self.state.write_text(json.dumps(st))

    def st(self):
        return json.loads(self.state.read_text())

    def labels(self, n):
        return self.st()["issues"][str(n)]["labels"]

    def run_cli(self, *args: str) -> subprocess.CompletedProcess:
        env = dict(os.environ, FAKE_GH_STATE=str(self.state), NOTES_ROOT=str(self.notes),
                   XDG_CACHE_HOME=str(Path(self.tmp.name) / "cache"), ISSUES_RETRY_WAIT="0",
                   ISSUES_GH=f"{sys.executable} -I {Path(__file__).resolve()} fake-gh")
        return subprocess.run([sys.executable, "-I", str(SCRIPT), *args], capture_output=True, text=True, env=env)

    def ok(self, *args: str) -> str:
        r = self.run_cli(*args)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_config_missing_or_wrong(self):
        (self.notes / "project-notes.json").unlink()
        r = self.run_cli("survey")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("project-notes.json", r.stderr)
        self.assertIn('"issues_repo"', r.stderr)  # the example
        self.config({"issues_repo": "notes"})
        self.assertIn('"issues_repo" must be "owner/name"', self.run_cli("survey").stderr)
        self.config({"issues_repo": "acme/notes", "board": {"owner": "acme"}})
        self.assertIn('"board" must be', self.run_cli("survey").stderr)

    def test_without_board_or_start_here(self):
        self.config({"issues_repo": "acme/notes"})
        self.assertIn("claimed #2", self.ok("claim", "2"))
        self.assertFalse(any(c[0] == "project" for c in self.st()["log"]))  # board skipped
        self.assertIn('No "board"', self.run_cli("board").stderr)
        self.assertIn('No "start_here"', self.run_cli("start-here").stderr)
        self.assertNotIn("Start here", self.ok("check"))

    def test_survey_counts_and_ready(self):
        out = self.ok("survey")
        self.assertIn("shop/checkout (6): 4 ready-for-agent, 1 ready-for-human, 1 in-progress-me; "
                      "1 now, 4 soon, 1 later; 2 blocked", out)
        self.assertIn("blog/comments (2): 2 ready-for-agent; 2 soon; 2 blocked", out)
        self.assertIn("(no milestone) (1): 1 needs-triage; 1 untriaged", out)
        st = self.st()
        st["issues"]["11"] = {"title": "Start here", "state": "OPEN", "labels": [], "milestone": None}
        self.save(st)
        self.assertIn("(no milestone) (1):", self.ok("survey"))  # an unlabelled issue isn't a ticket
        ready = out.split("ready:")[1].split("waiting on a person:")[0]
        self.assertIn("#2 soon  Helper", ready)
        self.assertNotIn("#3", ready)  # blocked
        self.assertNotIn("#9", ready)  # in progress
        self.assertIn("#6 soon", ready)  # blocked only by a closed issue: unblocked
        self.assertNotIn("#5", ready)
        self.assertIn("waiting on a person:\n  #5 later  Maintainer decides", out)
        self.assertIn("! cycle #7 > #8 > #7", out)

    def test_survey_one_milestone(self):
        out = self.ok("survey", "blog/comments")
        self.assertNotIn("shop/checkout", out)
        self.assertIn("ready: none", out)
        self.assertNotIn("#2 is soon", out)

    def test_list_one_milestone(self):
        out = self.ok("list", "shop/checkout")
        self.assertEqual(out.splitlines(), [
            "#2 ready-for-agent soon  Helper",
            "#3 ready-for-agent soon blocked-by #2  Uses the helper",
            "#4 ready-for-agent now blocked-by #3,#5  Urgent, waits on a person",
            "#5 ready-for-human later  Maintainer decides",
            "#6 ready-for-agent soon  Blocker closed",  # its only blocker is closed
            "#9 in-progress-me soon  Someone's on it",
        ])
        st = self.st()
        st["issues"]["11"] = {"title": "Bare", "state": "OPEN", "labels": [], "milestone": "blog/comments"}
        self.save(st)
        self.assertIn("#11 no-status later  Bare", self.ok("list", "blog/comments"))
        self.assertEqual(self.ok("list", "nope/none"), "")

    def test_chain_walks_to_the_end(self):
        out = self.ok("chain", "4")
        self.assertIn("#4 now ready-for-agent  Urgent", out)
        self.assertIn("\n  #3 soon ready-for-agent", out)
        self.assertIn("\n    #2 soon ready-for-agent", out)
        self.assertIn("\n  #5 later ready-for-human", out)
        self.assertIn("waits on: #2 agent (ready-for-agent), #5 person (ready-for-human)", out)
        self.assertIn("! #2 is soon, below #4 (now) that waits on it", out)  # two steps away
        self.assertIn("! #3 is soon, below #4 (now)", out)
        self.assertIn("! #5 is later, below #4 (now)", out)
        self.assertNotIn("cycle", out)

    def test_chain_reports_what_it_blocks_and_closed_blockers(self):
        out = self.ok("chain", "2")
        self.assertIn("blocks: #3", out)
        self.assertNotIn("waits on", out)
        out = self.ok("chain", "6")
        self.assertIn("  #1 closed", out)
        self.assertNotIn("!", out)  # a closed blocker is no problem
        self.assertIn("#7 (cycle)", self.ok("chain", "7"))

    def test_check_every_problem(self):
        out = self.ok("check")
        self.assertIn("9 open, 4 blocked, 4 blocker problems", out)
        self.assertIn("#7 soon waits on nothing outside a cycle", out)
        self.assertIn("#3 soon waits on #2 agent (ready-for-agent)", out)
        self.assertNotIn("#6", out)
        self.assertIn("! cycle #7 > #8 > #7", out)
        self.assertIn("! Start here is out of date", out)  # the fake's #8 body isn't one

    def test_show_folds_comments(self):
        out = self.ok("show", "9")
        self.assertIn("#9 Someone's on it [open]", out)
        self.assertIn("(2 hidden; --all shows them)", out)
        self.assertIn("third", out)
        self.assertNotIn("first", out)
        self.assertIn("first", self.ok("show", "--all", "9"))
        self.assertIn("blocked by: #2 · blocks: #4", self.ok("show", "3"))

    def test_claim_swaps_status_and_syncs_board(self):
        self.assertIn("claimed #2 (was ready-for-agent)", self.ok("claim", "2"))
        self.assertIn("status:in-progress-agent", self.labels(2))
        self.assertNotIn("status:ready-for-agent", self.labels(2))
        item = self.st()["items"]["2"]
        self.assertEqual((item["triage"], item["status"], item["project"]), ("in-progress-agent", "In Progress", "shop"))
        self.assertEqual(list(self.st()["items"]), ["2"])  # only the issue it changed
        self.assertIn(["project", "view", "3", "--owner", "acme", "--format", "json"], self.st()["log"])

    def test_claim_refuses(self):
        r = self.run_cli("claim", "9")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("already in-progress-me", r.stderr)
        r = self.run_cli("claim", "3")
        self.assertIn("blocked by #2", r.stderr)
        self.assertIn("status:ready-for-agent", self.labels(3))
        self.assertIn("claimed #3", self.ok("claim", "--force", "3"))
        self.assertIn("is closed", self.run_cli("claim", "1").stderr)

    def test_release(self):
        self.ok("claim", "2")
        self.assertIn("released #2 as ready-for-human", self.ok("release", "2", "status:ready-for-human"))
        self.assertEqual([l for l in self.labels(2) if l.startswith("status:")], ["status:ready-for-human"])
        self.assertEqual(self.st()["items"]["2"]["triage"], "ready-for-human")
        self.assertIn("not in-progress-agent", self.run_cli("release", "2", "ready-for-agent").stderr)
        self.assertIn("STATUS must be", self.run_cli("release", "2", "blocked").stderr)

    def test_release_and_comment_post_a_file(self):
        f = Path(self.tmp.name) / "c.md"
        f.write_text("Stopped: a question.\n")
        self.ok("claim", "2")
        self.ok("release", "2", "ready-for-human", "--comment-file", str(f))
        self.assertEqual(self.st()["issues"]["2"]["comments"][-1]["body"], "Stopped: a question.\n")
        self.assertIn("commented on #9", self.ok("comment", "9", "--comment-file", str(f)))
        self.assertEqual(len(self.st()["issues"]["9"]["comments"]), 4)
        self.assertIn("No such file", self.run_cli("comment", "9", "--comment-file", "nope.md").stderr)

    def test_close_comments_closes_and_reports_unblocked(self):
        self.ok("claim", "2")
        f = Path(self.tmp.name) / "c.md"
        f.write_text("Built it.\n")
        out = self.ok("close", "2", "--completed", "--comment-file", str(f))
        i = self.st()["issues"]["2"]
        self.assertEqual((i["state"], i["stateReason"]), ("CLOSED", "COMPLETED"))
        self.assertEqual(i["comments"][-1]["body"], "Built it.\n")
        self.assertNotIn("status:in-progress-agent", i["labels"])
        self.assertEqual(self.st()["items"]["2"]["status"], "Done")
        self.assertIn("closed #2 as completed", out)
        self.assertIn("unblocked: #3 ready-for-agent  Uses the helper", out)
        # the comment goes before the close
        calls = [c[:2] for c in self.st()["log"]]
        self.assertLess(calls.index(["issue", "comment"]), calls.index(["issue", "close"]))

    def test_close_not_planned_and_still_waiting(self):
        f = Path(self.tmp.name) / "c.md"
        f.write_text("No.\n")
        out = self.ok("close", "5", "--not-planned", "--comment-file", str(f))
        self.assertEqual(self.st()["issues"]["5"]["stateReason"], "NOT_PLANNED")
        self.assertIn("#4 still waits on #3", out)
        self.assertIn("already closed", self.run_cli("close", "5", "--completed", "--comment-file", str(f)).stderr)

    def calls(self, *prefix: str) -> int:
        return sum(1 for c in self.st()["log"] if c[:len(prefix)] == list(prefix))

    def test_board_all_adds_every_labelled_issue(self):
        self.ok("board", "--all")
        items = self.st()["items"]
        self.assertEqual(sorted(items, key=int), [str(n) for n in range(1, 11)])
        self.assertEqual(items["1"]["status"], "Done")
        before = self.calls("project", "item-edit")
        self.ok("board", "--all")
        self.assertEqual(self.calls("project", "item-edit"), before)  # in step
        self.assertIn("Name the issues", self.run_cli("board").stderr)  # the whole board only when asked
        self.assertIn("Name the issues", self.run_cli("board", "--all", "2").stderr)

    def test_one_issue_sync_reads_only_that_issue(self):
        self.ok("claim", "2")
        self.assertEqual(self.calls("project", "item-list"), 0)
        self.assertEqual(self.calls("issue", "list"), 0)
        self.assertEqual(self.calls("api", "graphql"), 1)
        self.assertEqual(self.calls("project", "field-list"), 1)  # the empty cache filled
        st = self.st()
        st["log"] = []
        self.save(st)
        out = self.ok("release", "2", "ready-for-human")
        self.assertEqual(self.st()["items"]["2"]["triage"], "ready-for-human")
        self.assertIn("board #2: Triage=ready-for-human, Status=Todo", out)  # only the fields that differ
        self.assertEqual([c[:2] for c in self.st()["log"]],
                         [["issue", "view"], ["issue", "edit"], ["api", "graphql"],
                          ["project", "item-edit"], ["project", "item-edit"]])  # ids from the cache
        self.assertNotIn("X-2", json.dumps(self.st()["log"]))  # the other board's item is left alone
        out = self.ok("board", "2", "3")
        self.assertIn("board #3:", out)
        self.assertNotIn("board #2", out)  # already in step
        self.assertEqual(self.calls("project", "item-add"), 1)  # #3 wasn't on the board
        self.assertEqual(sorted(self.st()["items"]), ["2", "3"])

    def cache(self) -> Path:
        return Path(self.tmp.name) / "cache" / "project-notes" / "board-acme-3.json"

    def test_cache_miss_and_stale_id_refresh(self):
        self.ok("board", "2")
        ids = json.loads(self.cache().read_text())
        del ids["fields"]["Triage"]["options"]["in-progress-agent"]  # an option added since
        self.cache().write_text(json.dumps(ids))
        before = self.calls("project", "field-list")
        self.ok("claim", "2")
        self.assertEqual(self.st()["items"]["2"]["triage"], "in-progress-agent")
        self.assertEqual(self.calls("project", "field-list"), before + 1)
        self.assertIn("in-progress-agent", json.loads(self.cache().read_text())["fields"]["Triage"]["options"])
        ids = json.loads(self.cache().read_text())
        ids["fields"]["Triage"]["options"]["ready-for-human"] = "O-remade"  # an option remade: new id
        self.cache().write_text(json.dumps(ids))
        self.ok("release", "2", "ready-for-human")
        self.assertEqual(self.st()["items"]["2"]["triage"], "ready-for-human")
        self.assertEqual(self.calls("project", "field-list"), before + 2)
        # a value the board really lacks: one refresh, then a warning
        st = self.st()
        st["issues"]["2"]["labels"].append("repo:elsewhere")
        st["issues"]["2"]["labels"].remove("repo:storefront")
        self.save(st)
        self.assertIn("! board has no Code repo option 'elsewhere' (#2)", self.ok("board", "2"))
        self.assertEqual(self.calls("project", "field-list"), before + 3)

    def test_rate_limit_retried_once(self):
        st = self.st()
        st["fail"] = [{"match": ["api", "graphql"], "stderr": "GraphQL: You have exceeded a secondary rate limit."}]
        self.save(st)
        self.assertIn("claimed #2", self.ok("claim", "2"))
        self.assertEqual(self.calls("api", "graphql"), 2)
        self.assertEqual(self.st()["items"]["2"]["triage"], "in-progress-agent")
        st = self.st()  # the primary limit: its reset comes from rate_limit
        st["fail"] = [{"match": ["project", "item-edit"], "stderr": "GraphQL: API rate limit exceeded for user ID 1."}]
        self.save(st)
        self.ok("release", "2", "ready-for-human")
        self.assertEqual(self.calls("api", "rate_limit"), 1)
        self.assertEqual(self.st()["items"]["2"]["triage"], "ready-for-human")

    def test_rate_limit_twice_leaves_the_board_lagging(self):
        st = self.st()
        st["fail"] = [{"match": ["api", "graphql"], "stderr": "GraphQL: was submitted too quickly"}] * 2
        self.save(st)
        r = self.run_cli("claim", "2")
        self.assertEqual(r.returncode, 0, r.stderr)  # the claim itself went through
        self.assertIn("status:in-progress-agent", self.labels(2))
        self.assertIn("claimed #2", r.stdout)
        self.assertEqual(r.stderr.strip(), "! the board lags (GitHub rate limit): run `issues.py board 2` later")
        self.assertNotIn("2", self.st()["items"])
        st = self.st()
        st["fail"] = [{"match": ["api", "graphql"], "stderr": "secondary rate limit"}] * 2
        self.save(st)
        r = self.run_cli("board", "2")
        self.assertEqual(r.returncode, 1)  # board's own job failed
        self.assertIn("run `issues.py board 2` later", r.stderr)
        st = self.st()
        st["fail"] = [{"match": ["issue", "view"], "stderr": "HTTP 404: Not Found"}]
        self.save(st)
        r = self.run_cli("claim", "2")
        self.assertEqual(r.returncode, 1)  # other failures aren't retried
        self.assertEqual(self.calls("issue", "view"), 2)

    def fixed_labels(self):
        st = self.st()
        st["labels"] += ["type:task", "status:ready-for-agent", "status:needs-triage", "priority:now", "priority:soon"]
        self.save(st)

    def test_search(self):
        out = self.ok("search", "loop")
        self.assertEqual(out.splitlines(), ["#7 ready-for-agent soon [blog/comments]  Loop a",
                                            "#8 ready-for-agent soon [blog/comments]  Loop b"])
        self.assertIn("none", self.ok("search", "long ago"))
        self.assertIn("#1 closed soon [shop/checkout]  Done long ago", self.ok("search", "--all", "long", "ago"))

    def test_new_with_labels_milestone_blockers_and_board(self):
        self.fixed_labels()
        f = Path(self.tmp.name) / "b.md"
        f.write_text("What to build.\n")
        out = self.ok("new", "--title", "Add coupons", "--body-file", str(f), "--org", "acme", "--project", "shop",
                      "--repo", "storefront", "--type", "task", "--status", "ready-for-agent", "--priority", "now",
                      "--milestone", "shop/checkout", "--blocked-by", "2")
        self.assertIn("created #11  Add coupons", out)
        i = self.st()["issues"]["11"]
        self.assertEqual(sorted(i["labels"]), ["org:acme", "priority:now", "project:shop", "repo:storefront",
                                               "status:ready-for-agent", "type:task"])
        self.assertEqual((i["milestone"], i["blockedBy"], i["body"]), ("shop/checkout", [2], "What to build.\n"))
        self.assertEqual(self.st()["items"]["11"]["triage"], "ready-for-agent")
        self.assertIn("#11 waits on #2 agent", out)
        self.assertIn("! #2 is soon, below #11 (now) that waits on it", out)
        self.assertNotIn("Start here", out)  # nothing new to link

    def test_new_refuses_unknown_labels_unless_create(self):
        self.fixed_labels()
        f = Path(self.tmp.name) / "b.md"
        f.write_text("x\n")
        args = ["new", "--title", "Newsletter", "--body-file", str(f), "--org", "acme", "--project", "mail",
                "--type", "task", "--status", "needs-triage", "--milestone", "mail/newsletter"]
        r = self.run_cli(*args)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("project:mail", r.stderr)
        self.assertIn("milestone mail/newsletter", r.stderr)
        self.assertNotIn("11", self.st()["issues"])
        out = self.ok(*args, "--create")
        self.assertIn("created label project:mail", out)
        self.assertIn("created milestone mail/newsletter", out)
        self.assertIn("Start here updated", out)
        self.assertEqual(self.st()["issues"]["11"]["labels"][1], "project:mail")
        bad = [x if x != "needs-triage" else "in-progress-agent" for x in args]
        self.assertIn("--status must be one of", self.run_cli(*bad).stderr)  # new issues aren't claimed

    def test_block_and_unblock(self):
        out = self.ok("block", "5", "2")
        self.assertEqual(self.st()["issues"]["5"]["blockedBy"], [2])
        self.assertIn("#5 blocked by #2", out)
        self.assertIn("#5 waits on #2 agent", out)
        out = self.ok("block", "--remove", "5", "2")
        self.assertEqual(self.st()["issues"]["5"]["blockedBy"], [])
        self.assertIn("#5 no longer blocked by #2", out)
        self.assertIn("can't block itself", self.run_cli("block", "5", "5").stderr)

    def test_status_at_triage(self):
        out = self.ok("status", "10", "ready-for-human")
        self.assertIn("#10 is now ready-for-human (was needs-triage)", out)
        self.assertEqual([l for l in self.labels(10) if l.startswith("status:")], ["status:ready-for-human"])
        self.assertIn("release it instead", self.run_cli("status", "9", "ready-for-agent").stderr)
        self.assertIn("claim and release", self.run_cli("status", "10", "in-progress-agent").stderr)
        self.assertIn("is closed", self.run_cli("status", "1", "ready-for-agent").stderr)

    def test_priority_swaps_label_and_reports(self):
        f = Path(self.tmp.name) / "c.md"
        f.write_text("Blocks #4, which is now.\n")
        out = self.ok("priority", "3", "now", "--comment-file", str(f))
        self.assertIn("#3 is now now", out)
        self.assertIn("priority:now", self.labels(3))
        self.assertNotIn("priority:soon", self.labels(3))
        self.assertEqual(self.st()["issues"]["3"]["comments"][-1]["body"], "Blocks #4, which is now.\n")
        self.assertIn("! #2 is soon, below #3 (now)", out)
        self.assertIn("already now", self.ok("priority", "3", "now"))
        self.ok("priority", "3", "later")
        self.assertFalse([l for l in self.labels(3) if l.startswith("priority:")])

    def test_start_here_rebuilds_from_labels_milestones_and_goals(self):
        self.assertIn("Start here updated", self.ok("start-here"))
        body = self.st()["issues"]["8"]["body"]
        self.assertIn("[blog](https://github.com/acme/notes/issues?q=", body)  # project label
        self.assertIn("[blog/comments](", body)
        self.assertIn("**Board:** [Acme work](https://github.com/users/acme/projects/3), the same issues in columns (private).", body)
        self.assertIn("1. Ship the new checkout\n2. Move to issues ([shop/checkout](", body)
        self.assertIn("(the notes folder)", body)
        self.assertIn("Start here unchanged", self.ok("start-here"))
        st = self.st()
        st["milestones"].append("blog/new-thing")
        self.save(st)
        out = self.ok("start-here", "--dry-run")
        self.assertIn("blog/new-thing", out)
        self.assertNotIn("blog/new-thing", self.st()["issues"]["8"]["body"])
        self.config({"issues_repo": "acme/notes", "start_here": 8})
        out = self.ok("start-here", "--dry-run")
        self.assertNotIn("**Board:**", out)
        self.assertIn("_None yet", out)


if __name__ == "__main__":
    if sys.argv[1:2] == ["fake-gh"]:
        fake_gh(sys.argv[2:])
    else:
        unittest.main()
