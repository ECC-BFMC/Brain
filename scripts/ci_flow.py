#!/usr/bin/env python3
"""Automate the PR-gated merge flow for this repo.

Flow:
  1. Create a new branch off the current HEAD.
  2. Commit your changes onto it.
  3. Push and open a pull request against the base branch (default: 2027).
  4. Wait for CI (the GitHub Actions checks) to finish.
  5. If every check passes -> merge the PR (and optionally sync the base locally).
     If any check fails   -> stop and print the link to the failing run.

Requires the GitHub CLI (`gh`) to be installed and authenticated:
    winget install GitHub.cli
    gh auth login

Examples:
    python scripts/ci_flow.py -m "Fix camera base64 import"
    python scripts/ci_flow.py -m "Add CI" -b ci/add-workflow --base master
    python scripts/ci_flow.py -m "wip" --staged --merge-method merge --no-sync
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime


# ----------------------------------------------------------------------------
# Small helpers around subprocess so the flow below reads top-to-bottom.
# ----------------------------------------------------------------------------
def run(cmd: list[str], *, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    """Run a command. By default streams output and raises on non-zero exit."""
    printable = " ".join(cmd)
    print(f"  $ {printable}")
    result = subprocess.run(
        cmd,
        text=True,
        capture_output=capture,
    )
    if check and result.returncode != 0:
        if capture and result.stderr:
            print(result.stderr, file=sys.stderr)
        raise SystemExit(f"Command failed ({result.returncode}): {printable}")
    return result


def out(cmd: list[str]) -> str:
    """Run a command quietly and return its trimmed stdout."""
    return subprocess.run(cmd, text=True, capture_output=True).stdout.strip()


def die(msg: str) -> "None":
    raise SystemExit(f"error: {msg}")


# ----------------------------------------------------------------------------
# Preflight
# ----------------------------------------------------------------------------
def preflight() -> None:
    # Inside a git repo?
    if out(["git", "rev-parse", "--is-inside-work-tree"]) != "true":
        die("not inside a git repository.")

    # gh installed?
    if subprocess.run(["gh", "--version"], capture_output=True, text=True).returncode != 0:
        die(
            "GitHub CLI (gh) not found.\n"
            "  Install:  winget install GitHub.cli\n"
            "  Then:     gh auth login"
        )

    # gh authenticated?
    if subprocess.run(["gh", "auth", "status"], capture_output=True, text=True).returncode != 0:
        die("gh is installed but not authenticated. Run: gh auth login")


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (slug[:40] or "change").rstrip("-")


# ----------------------------------------------------------------------------
# CI waiting
# ----------------------------------------------------------------------------
def wait_for_checks(branch: str, *, timeout: int, interval: int) -> tuple[bool, list[dict]]:
    """Poll the PR's checks until they all complete or timeout.

    Returns (passed, checks) where checks is the last JSON snapshot.
    Buckets reported by gh: pass, fail, pending, skipping, cancel.
    """
    deadline = time.time() + timeout
    fields = "name,state,bucket,link,workflow"
    last: list[dict] = []
    while time.time() < deadline:
        proc = subprocess.run(
            ["gh", "pr", "checks", branch, "--json", fields],
            text=True,
            capture_output=True,
        )
        # Right after opening the PR the checks may not be registered yet;
        # gh exits non-zero with "no checks reported". Treat as "keep waiting".
        if proc.returncode != 0 and not proc.stdout.strip():
            print("  ...waiting for checks to register")
            time.sleep(interval)
            continue

        try:
            last = json.loads(proc.stdout or "[]")
        except json.JSONDecodeError:
            time.sleep(interval)
            continue

        if not last:
            print("  ...no checks yet")
            time.sleep(interval)
            continue

        buckets = [c.get("bucket") for c in last]
        summary = ", ".join(f"{c['name']}={c['bucket']}" for c in last)
        print(f"  checks: {summary}")

        if any(b in ("fail", "cancel") for b in buckets):
            return False, last
        if all(b in ("pass", "skipping") for b in buckets):
            return True, last

        time.sleep(interval)

    print("  timed out waiting for checks to finish.")
    return False, last


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main() -> int:
    p = argparse.ArgumentParser(description="PR-gated merge flow (branch -> PR -> CI -> merge).")
    p.add_argument("-m", "--message", required=True, help="Commit message (also used as PR title).")
    p.add_argument("-b", "--branch", help="New branch name (default: auto from message + timestamp).")
    p.add_argument("--base", default="2027", help="Base branch to merge into (default: 2027).")
    p.add_argument("--staged", action="store_true", help="Commit only staged changes (default: stage all with -A).")
    p.add_argument("--merge-method", choices=["squash", "merge", "rebase"], default="squash",
                   help="How to merge the PR (default: squash).")
    p.add_argument("--no-delete-branch", action="store_true", help="Keep the branch after merge.")
    p.add_argument("--no-sync", action="store_true", help="Don't checkout+pull the base branch after merge.")
    p.add_argument("--timeout", type=int, default=1800, help="Max seconds to wait for CI (default: 1800).")
    p.add_argument("--interval", type=int, default=15, help="Seconds between CI polls (default: 15).")
    args = p.parse_args()

    preflight()

    # 1. Decide the branch name.
    branch = args.branch or f"ci/{slugify(args.message)}-{datetime.now():%Y%m%d-%H%M%S}"

    # Make sure there's actually something to commit.
    if args.staged:
        has_changes = bool(out(["git", "diff", "--cached", "--name-only"]))
        if not has_changes:
            die("no staged changes. Stage files or drop --staged to auto-stage everything.")
    else:
        has_changes = bool(out(["git", "status", "--porcelain"]))
        if not has_changes:
            die("working tree is clean — nothing to commit.")

    print(f"\n== Creating branch '{branch}' off current HEAD ==")
    run(["git", "checkout", "-b", branch])

    print("\n== Committing changes ==")
    if not args.staged:
        run(["git", "add", "-A"])
    # Show what is about to be committed.
    run(["git", "status", "--short"])
    run(["git", "commit", "-m", args.message])

    print("\n== Pushing branch ==")
    run(["git", "push", "-u", "origin", branch])

    print("\n== Opening pull request ==")
    run([
        "gh", "pr", "create",
        "--base", args.base,
        "--head", branch,
        "--title", args.message,
        "--body", f"Automated PR via ci_flow.py.\n\n{args.message}",
    ])
    pr_url = out(["gh", "pr", "view", branch, "--json", "url", "-q", ".url"])
    print(f"  PR: {pr_url}")

    print("\n== Waiting for CI ==")
    passed, checks = wait_for_checks(branch, timeout=args.timeout, interval=args.interval)

    if not passed:
        print("\n[X] CI did not pass. NOT merging.")
        failing = [c for c in checks if c.get("bucket") in ("fail", "cancel")]
        for c in failing:
            print(f"    - {c.get('name')}: {c.get('link')}")
        if not failing:
            print("    (no failing check details — see the PR for the run status)")
        print(f"\n    PR:      {pr_url}")
        print(f"    Branch:  {branch} (left in place for you to fix)")
        return 1

    print("\n[OK] All checks passed. Merging...")
    merge_cmd = ["gh", "pr", "merge", branch, f"--{args.merge_method}"]
    if not args.no_delete_branch:
        merge_cmd.append("--delete-branch")
    run(merge_cmd)
    print(f"  Merged: {pr_url}")

    if not args.no_sync:
        print(f"\n== Syncing local '{args.base}' ==")
        run(["git", "checkout", args.base])
        run(["git", "pull", "origin", args.base])

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
