#!/usr/bin/env python3

from __future__ import annotations

import argparse
import shlex
from pathlib import Path

from conventional_commits import (
    CONVENTIONAL_COMMIT_HEADER,
    is_conventional_commit_message,
)
from github_about import ensure_github_about
from git_push_utils import AUTO_PUSH_SKIP_ENV, GitError, assess_repo, run_git_or_raise

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Commit and push to GitHub when the repository is ready."
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="Repository path. Defaults to the current working directory.",
    )
    parser.add_argument(
        "--message",
        help=(
            "Conventional Commit message to use when a commit is required "
            '(for example, "feat(cli): add guarded push").'
        ),
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute the commit and push instead of printing the plan.",
    )
    parser.add_argument(
        "--allow-stage-all",
        action="store_true",
        help="Allow staging every tracked and untracked change with git add -A.",
    )
    parser.add_argument(
        "--pathspec",
        action="append",
        default=[],
        help="Pathspec to stage for the commit. Repeat as needed.",
    )
    parser.add_argument(
        "--about-description",
        help=(
            "Description to use when the GitHub repository About is empty. "
            "Defaults to the first prose paragraph in README."
        ),
    )
    return parser


def build_commit_commands(
    branch: str | None,
    remote: str | None,
    upstream: str | None,
    commit_message: str | None,
    allow_stage_all: bool,
    pathspecs: list[str],
) -> list[str]:
    commands: list[str] = []
    if pathspecs:
        commands.append(
            shlex.join(["git", "add", "--", *pathspecs])
        )
    elif allow_stage_all:
        commands.append("git add -A")
    else:
        commands.append("# specify --pathspec or --allow-stage-all before executing a commit")
    commands.append(
        shlex.join(["git", "commit", "-m", commit_message or "<message>"])
    )
    if remote and branch:
        if upstream:
            commands.append("git push")
        else:
            commands.append(shlex.join(["git", "push", "-u", remote, branch]))
    return commands


def print_plan(
    report: dict[str, object],
    commit_message: str | None,
    allow_stage_all: bool,
    pathspecs: list[str],
) -> None:
    print(f"recommended_action: {report['recommended_action']}")
    for reason in report["reasons"]:
        print(f"- {reason}")
    commands = list(report["commands"])
    if report["recommended_action"] == "commit_then_push":
        commands = build_commit_commands(
            report["branch"],
            report["preferred_remote"],
            report["upstream"],
            commit_message,
            allow_stage_all,
            pathspecs,
        )
    if commands:
        print("planned_commands:")
        for command in commands:
            print(f"  {command}")


def main() -> int:
    args = build_parser().parse_args()
    if args.allow_stage_all and args.pathspec:
        print("use either --allow-stage-all or --pathspec, not both")
        return 2

    report = assess_repo(Path(args.repo))
    action = report["recommended_action"]

    if action not in {"push", "commit_then_push"} or not report["safe_to_push"]:
        print_plan(report, args.message, args.allow_stage_all, args.pathspec)
        return 2

    if action == "commit_then_push" and not args.message and args.execute:
        print("commit message is required when execution would create a commit")
        return 2

    if (
        action == "commit_then_push"
        and args.message
        and not is_conventional_commit_message(args.message)
    ):
        print(
            "commit message must follow Conventional Commits 1.0.0: "
            "<type>[optional scope][!]: <description>"
        )
        return 2

    if action == "commit_then_push" and args.execute and not (args.allow_stage_all or args.pathspec):
        print("commit execution requires --pathspec or --allow-stage-all")
        return 2

    if not args.execute:
        print_plan(report, args.message, args.allow_stage_all, args.pathspec)
        return 0

    repo = Path(str(report["repo_path"]))
    remote = report["preferred_remote"]
    branch = report["branch"]
    upstream = report["upstream"]

    if not remote or not branch:
        print("remote or branch could not be determined")
        return 2

    try:
        about = ensure_github_about(repo, str(remote), args.about_description)
        if not about.ok:
            print(f"GitHub About check failed: {about.message}")
            return 2
        if about.changed:
            print(f"GitHub About updated: {about.description}")

        created_commit = False
        if action == "commit_then_push":
            if args.pathspec:
                run_git_or_raise(repo, "add", "--", *args.pathspec)
            else:
                run_git_or_raise(repo, "add", "-A")
            run_git_or_raise(
                repo,
                "commit",
                "-m",
                args.message or "",
                env={AUTO_PUSH_SKIP_ENV: "1"},
            )
            created_commit = True

        if upstream:
            run_git_or_raise(repo, "push")
        else:
            run_git_or_raise(repo, "push", "-u", str(remote), str(branch))
    except GitError as error:
        print(str(error))
        return 1

    print(f"pushed branch {branch} to {remote}")
    if created_commit:
        print("created_commit: true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
