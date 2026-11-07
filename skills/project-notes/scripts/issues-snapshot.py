#!/usr/bin/env python3
"""Write every issue of the notes repo's issues repo to issues/snapshot.json.

Run nightly by the notes repo's .github/workflows/issues-snapshot.yml, a
copy of this skill repo's templates/issues-snapshot.yml. Open and closed
issues, with comments, labels, milestone and blockers, in a stable order
so the commit's diff shows only real changes. For offline reading and
recovery only; normal work reads the issues with gh.

Usage: issues-snapshot.py [--repo OWNER/NAME] [--out PATH]
--repo defaults to "issues_repo" in $NOTES_ROOT/project-notes.json (see
issues.py). Needs `gh` signed in (GH_TOKEN in the Action).
"""
import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

QUERY = """
query($owner: String!, $name: String!, $after: String) {
  repository(owner: $owner, name: $name) {
    issues(first: 50, after: $after, states: [OPEN, CLOSED],
           orderBy: {field: CREATED_AT, direction: ASC}) {
      pageInfo { hasNextPage endCursor }
      nodes {
        number title state stateReason url createdAt updatedAt closedAt
        author { login }
        body
        labels(first: 100) { nodes { name } }
        milestone { title }
        blockedBy(first: 100) { nodes { number } }
        blocking(first: 100) { nodes { number } }
        parent { number }
        subIssues(first: 100) { nodes { number } }
        comments(first: 100) {
          pageInfo { hasNextPage endCursor }
          nodes { author { login } createdAt body url }
        }
      }
    }
  }
}
"""

MORE_COMMENTS = """
query($owner: String!, $name: String!, $number: Int!, $after: String) {
  repository(owner: $owner, name: $name) {
    issue(number: $number) {
      comments(first: 100, after: $after) {
        pageInfo { hasNextPage endCursor }
        nodes { author { login } createdAt body url }
      }
    }
  }
}
"""


def graphql(query, **variables):
    cmd = ["gh", "api", "graphql", "-f", "query=" + query]
    for key, value in variables.items():
        if value is None:
            continue
        cmd += ["-F" if isinstance(value, int) else "-f", f"{key}={value}"]
    out = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
    return json.loads(out)["data"]["repository"]


def numbers(conn):
    return sorted(n["number"] for n in conn["nodes"])


def comment(c):
    return {
        "author": (c["author"] or {}).get("login"),
        "created": c["createdAt"],
        "body": c["body"],
        "url": c["url"],
    }


def all_comments(owner, name, issue):
    conn = issue["comments"]
    found = list(conn["nodes"])
    while conn["pageInfo"]["hasNextPage"]:
        conn = graphql(MORE_COMMENTS, owner=owner, name=name,
                       number=issue["number"],
                       after=conn["pageInfo"]["endCursor"])["issue"]["comments"]
        found += conn["nodes"]
    return [comment(c) for c in found]


def snapshot(repo):
    owner, name = repo.split("/")
    issues, after = [], None
    while True:
        page = graphql(QUERY, owner=owner, name=name, after=after)["issues"]
        for i in page["nodes"]:
            issues.append({
                "number": i["number"],
                "title": i["title"],
                "state": i["state"],
                "state_reason": i["stateReason"],
                "url": i["url"],
                "author": (i["author"] or {}).get("login"),
                "created": i["createdAt"],
                "updated": i["updatedAt"],
                "closed": i["closedAt"],
                "labels": sorted(l["name"] for l in i["labels"]["nodes"]),
                "milestone": (i["milestone"] or {}).get("title"),
                "blocked_by": numbers(i["blockedBy"]),
                "blocking": numbers(i["blocking"]),
                "parent": (i["parent"] or {}).get("number"),
                "sub_issues": numbers(i["subIssues"]),
                "body": i["body"],
                "comments": all_comments(owner, name, i),
            })
        if not page["pageInfo"]["hasNextPage"]:
            break
        after = page["pageInfo"]["endCursor"]
    issues.sort(key=lambda i: i["number"])
    return {"repo": repo, "issues": issues}


def configured_repo():
    spec = importlib.util.spec_from_file_location("issues", HERE / "issues.py")
    issues = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(issues)
    return issues.load_config()["issues_repo"]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", help="OWNER/NAME (default: the config's issues_repo)")
    ap.add_argument("--out", default="issues/snapshot.json")
    args = ap.parse_args()
    data = snapshot(args.repo or configured_repo())
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=1, sort_keys=True,
                              ensure_ascii=False) + "\n")
    print(f"{len(data['issues'])} issues -> {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
