#!/usr/bin/env python3

from __future__ import annotations

import argparse
import shlex
from pathlib import Path

from git_push_utils import run_git, run_git_or_raise

MANAGED_MARKER = "github-push-when-ready auto-push hook"
BACKUP_SUFFIX = ".pre-codex-auto-push.bak"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install a post-commit hook that auto-pushes when the repo is ready."
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="Repository path. Defaults to the current working directory.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing unmanaged post-commit hook after backing it up.",
    )
    return parser


def resolve_repo(repo_arg: str) -> Path:
    repo = Path(repo_arg).resolve()
    return Path(run_git_or_raise(repo, "rev-parse", "--show-toplevel"))


def resolve_hook_path(repo: Path) -> Path:
    hooks_path = run_git(repo, "config", "--get", "core.hooksPath")
    if hooks_path.returncode == 0 and hooks_path.stdout:
        configured = Path(hooks_path.stdout)
        if configured.is_absolute():
            return configured / "post-commit"
        return (repo / configured).resolve() / "post-commit"

    git_dir = Path(run_git_or_raise(repo, "rev-parse", "--git-dir"))
    if not git_dir.is_absolute():
        git_dir = (repo / git_dir).resolve()
    return git_dir / "hooks" / "post-commit"


def build_hook_body(skill_dir: Path) -> str:
    auto_push_script = skill_dir / "scripts" / "auto_push_post_commit.py"
    script_arg = shlex.quote(str(auto_push_script))
    return "\n".join(
        [
            "#!/bin/sh",
            f"# {MANAGED_MARKER}",
            'repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"',
            f'python3 {script_arg} --repo "$repo_root"',
            "status=$?",
            'if [ "$status" -ne 0 ]; then',
            '  printf \'%s\\n\' "github-push-when-ready: auto-push reported an error." >&2',
            "fi",
            "exit 0",
            "",
        ]
    )


def main() -> int:
    args = build_parser().parse_args()
    skill_dir = Path(__file__).resolve().parent.parent
    repo = resolve_repo(args.repo)
    hook_path = resolve_hook_path(repo)
    hook_path.parent.mkdir(parents=True, exist_ok=True)
    new_body = build_hook_body(skill_dir)

    if hook_path.exists():
        existing_body = hook_path.read_text()
        if existing_body == new_body:
            print(f"post-commit hook already installed at {hook_path}")
            return 0
        if MANAGED_MARKER not in existing_body:
            if not args.force:
                print(f"existing unmanaged post-commit hook found at {hook_path}; rerun with --force to replace it")
                return 2
            backup_path = hook_path.with_name(hook_path.name + BACKUP_SUFFIX)
            hook_path.replace(backup_path)
            print(f"backed up existing hook to {backup_path}")

    hook_path.write_text(new_body)
    hook_path.chmod(0o755)
    print(f"installed auto-push post-commit hook at {hook_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
