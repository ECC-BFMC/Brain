#!/usr/bin/env python3
"""Automate the PR-gated merge flow for this repo.

Flow:
  1. Create a new branch off the current HEAD.
  2. Commit your changes onto it.
  3. Push and open a pull request against the base branch (default: current branch).
  4. Wait for CI (the GitHub Actions checks) to finish.
  5. If every check passes -> merge the PR (and optionally sync the base locally).
     If any check fails   -> stop and print the link to the failing run.

Arguments (short):
  -m, --message        Required. Commit message, also used as the PR title.
  -b, --branch         New branch name. Default: auto from message + timestamp.
  --base               Branch to merge into. Default: the branch you're on now.
  --staged             Commit only staged files. Default: stage everything (-A).
  --merge-method       squash | merge | rebase. Default: squash.
  --no-delete-branch   Keep the feature branch after merge (default deletes it).
  --no-sync            Don't checkout+pull the base after merge (default syncs).
  --timeout            Max seconds to wait for CI. Default: 1800 (30 min).
  --interval           Seconds between CI status polls. Default: 15.
  --silent             Background the script and suppress output (for cron jobs). Default: False.
  
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
import os
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


def best_effort(cmd: list[str]) -> None:
    """Run a cleanup command, ignoring any failure."""
    print(f"  $ {' '.join(cmd)}")
    subprocess.run(cmd, text=True, capture_output=True)


def relaunch_detached() -> str:
    """Re-run this script in the background, logging to a file.

    Used by --silent (e.g. cron jobs): the child runs the full flow detached
    from the terminal while the caller returns immediately. Output goes to a
    timestamped log file (not the terminal) so a failed background run is still
    diagnosable. The --silent flag is stripped from the child's argv so it
    doesn't background itself again. Returns the log file path.
    """
    argv = [a for a in sys.argv if a != "--silent"]

    log_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "runtime", "temp"
    )
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"ciFlow_{datetime.now():%Y%m%d_%H%M%S}.log")
    logfile = open(log_path, "wb")

    kwargs: dict = {"stdin": subprocess.DEVNULL, "stdout": logfile, "stderr": subprocess.STDOUT}
    if os.name == "nt":
        # CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP: no console window, detached.
        kwargs["creationflags"] = 0x08000000 | 0x00000200
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen([sys.executable, *argv], **kwargs)
    return log_path


# ----------------------------------------------------------------------------
# Preflight
# ----------------------------------------------------------------------------
def _returncode(cmd: list[str]) -> "int | None":
    """Run a command quietly. Returns its exit code, or None if the
    executable isn't installed (FileNotFoundError on a missing program)."""
    try:
        return subprocess.run(cmd, capture_output=True, text=True).returncode
    except FileNotFoundError:
        return None


def preflight() -> None:
    # git installed and inside a repo?
    if _returncode(["git", "--version"]) is None:
        die("git not found on PATH.")
    if out(["git", "rev-parse", "--is-inside-work-tree"]) != "true":
        die("not inside a git repository.")

    # gh installed?
    if _returncode(["gh", "--version"]) is None:
        die(
            "GitHub CLI (gh) not found.\n"
            "  Install:  winget install GitHub.cli\n"
            "  Then:     gh auth login\n"
            "  (open a new terminal after installing so PATH refreshes)"
        )

    # gh authenticated?
    if _returncode(["gh", "auth", "status"]) != 0:
        die("gh is installed but not authenticated. Run: gh auth login")


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (slug[:40] or "change").rstrip("-")


def safe_branch_name(name: str) -> str:
    """Avoid git ref conflicts before creating a branch.

    Git stores refs as files, so a branch named ``ci`` (a file) blocks creating
    ``ci/anything`` (which needs ``ci`` to be a directory) -> 'cannot lock ref'.
    If any leading path segment of ``name`` already exists as a branch, flatten
    the slashes to dashes so ``git checkout -b`` can't fail on the collision.
    """
    if "/" not in name:
        return name
    existing = set(
        out(["git", "for-each-ref", "--format=%(refname:short)", "refs/heads"]).splitlines()
    )
    parts = name.split("/")
    for i in range(1, len(parts)):
        if "/".join(parts[:i]) in existing:
            return name.replace("/", "-")
    return name


def gh_repo() -> str:
    """Derive OWNER/REPO from the 'origin' remote so gh doesn't rely on a
    configured default remote (this repo has several remotes)."""
    url = out(["git", "remote", "get-url", "origin"])
    m = re.search(r"[:/]([^/]+/[^/]+?)(?:\.git)?$", url)
    if not m:
        die(f"could not parse owner/repo from origin url: {url!r}")
    return m.group(1)


# ----------------------------------------------------------------------------
# CI waiting
# ----------------------------------------------------------------------------
def wait_for_checks(branch: str, *, repo: str, timeout: int, interval: int) -> tuple[bool, list[dict]]:
    """Poll the PR's checks until they all complete or timeout.

    Returns (passed, checks) where checks is the last JSON snapshot.
    Buckets reported by gh: pass, fail, pending, skipping, cancel.
    """
    deadline = time.time() + timeout
    fields = "name,state,bucket,link,workflow"
    last: list[dict] = []
    while time.time() < deadline:
        proc = subprocess.run(
            ["gh", "pr", "checks", branch, "--repo", repo, "--json", fields],
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
    p.add_argument("--base", default=None,
                   help="Base branch to merge into (default: the branch you're currently on).")
    p.add_argument("--staged", action="store_true", help="Commit only staged changes (default: stage all with -A).")
    p.add_argument("--merge-method", choices=["squash", "merge", "rebase"], default="squash",
                   help="How to merge the PR (default: squash).")
    p.add_argument("--no-delete-branch", action="store_true", help="Keep the branch after merge.")
    p.add_argument("--no-sync", action="store_true", help="Don't checkout+pull the base branch after merge.")
    p.add_argument("--timeout", type=int, default=1800, help="Max seconds to wait for CI (default: 1800).")
    p.add_argument("--interval", type=int, default=15, help="Seconds between CI polls (default: 15).")
    p.add_argument("--silent", action="store_true",
                   help="Background the script and suppress output (for cron jobs).")
    args = p.parse_args()

    # Detach into the background and return immediately (e.g. for cron jobs).
    # The relaunched child runs without --silent, so it executes the flow below.
    if args.silent:
        log_path = relaunch_detached()
        print(f"Backgrounded (pid detached). Logging to: {log_path}")
        return 0

    preflight()

    # Capture the branch we're on NOW — this is the PR base, since it's the
    # branch we want to update. Must be read before we checkout the new branch.
    base = args.base or out(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if base == "HEAD":
        die("detached HEAD — checkout a branch first, or pass --base explicitly.")

    repo = gh_repo()
    print(f"repo: {repo}  |  base: {base}")

    # 1. Decide the branch name. Auto-generated names are made ref-safe so an
    # existing branch like 'ci' can't block creating 'ci/<slug>'.
    branch = args.branch or safe_branch_name(
        f"ci/{slugify(args.message)}-{datetime.now():%Y%m%d-%H%M%S}"
    )
    if branch == base:
        die(f"new branch name ({branch}) matches the base branch; choose a different -b.")

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

    # Track progress so that, if we fail BEFORE the PR exists, we can roll back
    # to the base branch and remove the half-created branch. Otherwise a failed
    # run strands you on the feature branch, and the next run's auto-detected
    # base picks up that stray branch instead of the real base.
    pushed = False
    pr_created = False
    try:
        print("\n== Committing changes ==")
        if not args.staged:
            run(["git", "add", "-A"])
        # Show what is about to be committed.
        run(["git", "status", "--short"])
        run(["git", "commit", "-m", args.message])

        print("\n== Pushing branch ==")
        run(["git", "push", "-u", "origin", branch])
        pushed = True

        print("\n== Opening pull request ==")
        run([
            "gh", "pr", "create",
            "--repo", repo,
            "--base", base,
            "--head", branch,
            "--title", args.message,
            "--body", f"Automated PR via ci_flow.py.\n\n{args.message}",
        ])
        pr_created = True
        pr_url = out(["gh", "pr", "view", branch, "--repo", repo, "--json", "url", "-q", ".url"])
        print(f"  PR: {pr_url}")

        print("\n== Waiting for CI ==")
        passed, checks = wait_for_checks(branch, repo=repo, timeout=args.timeout, interval=args.interval)

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
        merge_cmd = ["gh", "pr", "merge", branch, "--repo", repo, f"--{args.merge_method}"]
        if not args.no_delete_branch:
            merge_cmd.append("--delete-branch")
        run(merge_cmd)
        print(f"  Merged: {pr_url}")

        if not args.no_sync:
            print(f"\n== Syncing local '{base}' ==")
            run(["git", "checkout", base])
            run(["git", "pull", "origin", base])

        print("\nDone.")
        return 0

    except SystemExit:
        # Roll back only if the PR was never created; once a PR exists we leave
        # everything in place so you can inspect/retry it.
        if not pr_created:
            print(f"\n== Rolling back to '{base}' (failure before PR was created) ==")
            best_effort(["git", "checkout", base])
            best_effort(["git", "branch", "-D", branch])
            if pushed:
                best_effort(["git", "push", "origin", "--delete", branch])
        raise


if __name__ == "__main__":
    sys.exit(main())
