#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CONFLICT_CODES = {"DD", "AU", "UD", "UA", "DU", "AA", "UU"}


@dataclass
class GitResult:
    returncode: int
    stdout: str
    stderr: str


class GitError(RuntimeError):
    pass


def run_git(repo: Path, *args: str) -> GitResult:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    return GitResult(
        returncode=completed.returncode,
        stdout=completed.stdout.strip(),
        stderr=completed.stderr.strip(),
    )


def run_git_or_raise(repo: Path, *args: str) -> str:
    result = run_git(repo, *args)
    if result.returncode != 0:
        command = shlex.join(["git", "-C", str(repo), *args])
        detail = result.stderr or result.stdout or "git command failed"
        raise GitError(f"{command}: {detail}")
    return result.stdout


def is_github_url(url: str) -> bool:
    return bool(
        re.search(r"(^git@github\.com:|^ssh://git@github\.com/|github\.com[:/])", url)
    )


def parse_remote_urls(raw: str) -> dict[str, dict[str, str]]:
    remotes: dict[str, dict[str, str]] = {}
    for line in raw.splitlines():
        match = re.match(r"(\S+)\s+(\S+)\s+\((fetch|push)\)", line)
        if not match:
            continue
        name, url, direction = match.groups()
        remotes.setdefault(name, {})[direction] = url
    return remotes


def summarize_status(raw: str) -> dict[str, Any]:
    lines = raw.splitlines()
    branch_line = lines[0] if lines else ""
    entries = lines[1:] if branch_line.startswith("## ") else lines
    staged = 0
    unstaged = 0
    untracked = 0
    conflicted = 0
    for entry in entries:
        code = entry[:2]
        if code == "??":
            untracked += 1
            continue
        if code in CONFLICT_CODES or "U" in code:
            conflicted += 1
        if len(code) >= 1 and code[0] not in {" ", "?"}:
            staged += 1
        if len(code) >= 2 and code[1] not in {" ", "?"}:
            unstaged += 1
    return {
        "branch_line": branch_line[3:] if branch_line.startswith("## ") else branch_line,
        "staged": staged,
        "unstaged": unstaged,
        "untracked": untracked,
        "conflicted": conflicted,
        "total_changes": staged + unstaged + untracked + conflicted,
    }


def parse_branch(branch_line: str) -> tuple[str | None, bool]:
    if not branch_line:
        return None, False
    if branch_line.startswith("No commits yet on "):
        return branch_line.removeprefix("No commits yet on "), False
    head = branch_line.split("...", 1)[0]
    if head.startswith("HEAD "):
        return None, True
    return head, False


def parse_ahead_behind(branch_line: str) -> tuple[int, int]:
    ahead = 0
    behind = 0
    match = re.search(r"\[(.+)\]$", branch_line)
    if not match:
        return ahead, behind
    for item in match.group(1).split(","):
        item = item.strip()
        if item.startswith("ahead "):
            ahead = int(item.removeprefix("ahead "))
        if item.startswith("behind "):
            behind = int(item.removeprefix("behind "))
    return ahead, behind


def choose_remote(github_remotes: dict[str, dict[str, str]], upstream: str | None) -> str | None:
    if upstream:
        upstream_remote = upstream.split("/", 1)[0]
        if upstream_remote in github_remotes:
            return upstream_remote
    if "origin" in github_remotes:
        return "origin"
    if github_remotes:
        return sorted(github_remotes)[0]
    return None


def build_push_command(remote: str, branch: str, upstream: str | None) -> str:
    if upstream:
        return "git push"
    return shlex.join(["git", "push", "-u", remote, branch])


def assess_repo(repo_path: str | Path) -> dict[str, Any]:
    repo = Path(repo_path).resolve()
    top_level = run_git(repo, "rev-parse", "--show-toplevel")
    if top_level.returncode != 0:
        return {
            "repo_path": str(repo),
            "is_git_repo": False,
            "github_remote_connected": False,
            "recommended_action": "not_git_repo",
            "safe_to_push": False,
            "reasons": ["Current path is not inside a Git repository."],
            "commands": [],
        }

    repo = Path(top_level.stdout)
    status = summarize_status(run_git_or_raise(repo, "status", "--porcelain=v1", "--branch"))
    branch, detached = parse_branch(status["branch_line"])
    ahead, behind = parse_ahead_behind(status["branch_line"])

    upstream_result = run_git(repo, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
    upstream = upstream_result.stdout if upstream_result.returncode == 0 else None

    if upstream:
        counts = run_git(repo, "rev-list", "--left-right", "--count", f"{upstream}...HEAD")
        if counts.returncode == 0 and counts.stdout:
            behind_count, ahead_count = counts.stdout.split()
            behind = int(behind_count)
            ahead = int(ahead_count)

    remotes = parse_remote_urls(run_git_or_raise(repo, "remote", "-v"))
    github_remotes = {
        name: urls
        for name, urls in remotes.items()
        if any(is_github_url(url) for url in urls.values())
    }
    preferred_remote = choose_remote(github_remotes, upstream)
    has_commits = run_git(repo, "rev-parse", "--verify", "HEAD").returncode == 0
    has_changes = any(status[key] > 0 for key in ("staged", "unstaged", "untracked", "conflicted"))

    reasons: list[str] = []
    commands: list[str] = []
    recommended_action = "noop"
    safe_to_push = False

    if not github_remotes:
        recommended_action = "no_github_remote"
        reasons.append("No GitHub remote is configured for this repository.")
    elif detached or not branch:
        recommended_action = "manual_review"
        reasons.append("Repository is on a detached HEAD or branch name could not be determined.")
    elif status["conflicted"] > 0:
        recommended_action = "resolve_conflicts"
        reasons.append("Working tree contains unresolved merge conflicts.")
    elif behind > 0:
        recommended_action = "sync_first"
        reasons.append(f"Branch is behind upstream by {behind} commit(s).")
        if preferred_remote and upstream:
            remote_branch = upstream.split("/", 1)[1]
            commands.append(shlex.join(["git", "pull", "--rebase", preferred_remote, remote_branch]))
    elif has_changes:
        recommended_action = "commit_then_push"
        safe_to_push = True
        reasons.append("Working tree has local changes that can be committed before pushing.")
        if preferred_remote and branch:
            commands.extend(["git add -A", 'git commit -m "<message>"', build_push_command(preferred_remote, branch, upstream)])
    elif ahead > 0 or (preferred_remote and has_commits and not upstream):
        recommended_action = "push"
        safe_to_push = True
        if ahead > 0:
            reasons.append(f"Branch is ahead of upstream by {ahead} commit(s).")
        else:
            reasons.append("Branch has no upstream yet and can be published to GitHub.")
        if preferred_remote and branch:
            commands.append(build_push_command(preferred_remote, branch, upstream))
    elif not has_commits:
        recommended_action = "noop"
        reasons.append("Repository has no commits to publish yet.")
    else:
        recommended_action = "noop"
        reasons.append("Repository is clean and has nothing new to push.")

    return {
        "repo_path": str(repo),
        "is_git_repo": True,
        "github_remote_connected": bool(github_remotes),
        "github_remotes": [
            {
                "name": name,
                "fetch_url": urls.get("fetch"),
                "push_url": urls.get("push"),
            }
            for name, urls in sorted(github_remotes.items())
        ],
        "preferred_remote": preferred_remote,
        "branch": branch,
        "detached_head": detached,
        "upstream": upstream,
        "ahead": ahead,
        "behind": behind,
        "has_commits": has_commits,
        "worktree": {
            "staged": status["staged"],
            "unstaged": status["unstaged"],
            "untracked": status["untracked"],
            "conflicted": status["conflicted"],
            "clean": not has_changes,
        },
        "recommended_action": recommended_action,
        "safe_to_push": safe_to_push,
        "reasons": reasons,
        "commands": commands,
    }


def print_json(data: dict[str, Any]) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))
