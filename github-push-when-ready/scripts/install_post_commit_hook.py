#!/usr/bin/env python3

from __future__ import annotations

import argparse
import shlex
from pathlib import Path

from git_push_utils import run_git, run_git_or_raise

MANAGED_MARKER = "github-push-when-ready auto-push hook"
BACKUP_SUFFIX = ".pre-codex-auto-push.bak"
CONVENTIONAL_COMMIT_MARKER = "github-push-when-ready conventional-commits hook"
CONVENTIONAL_COMMIT_BACKUP_SUFFIX = ".pre-codex-conventional-commits.bak"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Install a commit-msg Conventional Commits validator and a post-commit "
            "auto-push hook."
        )
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="Repository path. Defaults to the current working directory.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace existing unmanaged hooks after backing them up.",
    )
    return parser


def resolve_repo(repo_arg: str) -> Path:
    repo = Path(repo_arg).resolve()
    return Path(run_git_or_raise(repo, "rev-parse", "--show-toplevel"))


def resolve_hooks_dir(repo: Path) -> Path:
    hooks_path = run_git(repo, "config", "--get", "core.hooksPath")
    if hooks_path.returncode == 0 and hooks_path.stdout:
        configured = Path(hooks_path.stdout)
        if configured.is_absolute():
            return configured
        return (repo / configured).resolve()

    git_dir = Path(run_git_or_raise(repo, "rev-parse", "--git-dir"))
    if not git_dir.is_absolute():
        git_dir = (repo / git_dir).resolve()
    return git_dir / "hooks"


def resolve_hook_path(repo: Path, hook_name: str = "post-commit") -> Path:
    return resolve_hooks_dir(repo) / hook_name


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


def build_conventional_commit_hook_body(skill_dir: Path) -> str:
    validator = skill_dir / "scripts" / "conventional_commits.py"
    script_arg = shlex.quote(str(validator))
    return "\n".join(
        [
            "#!/bin/sh",
            f"# {CONVENTIONAL_COMMIT_MARKER}",
            f'exec python3 {script_arg} "$1"',
            "",
        ]
    )


def _check_unmanaged_hook(hook_path: Path, marker: str, new_body: str) -> str | None:
    if not hook_path.exists():
        return None
    existing_body = hook_path.read_text()
    if existing_body == new_body or marker in existing_body:
        return None
    return f"existing unmanaged {hook_path.name} hook found at {hook_path}; rerun with --force to replace it"


def _install_hook(
    hook_path: Path,
    new_body: str,
    marker: str,
    backup_suffix: str,
    force: bool,
) -> str:
    hook_path.parent.mkdir(parents=True, exist_ok=True)
    if hook_path.exists():
        existing_body = hook_path.read_text()
        if existing_body == new_body:
            return f"{hook_path.name} hook already installed at {hook_path}"
        if marker not in existing_body:
            if not force:
                raise RuntimeError(
                    f"existing unmanaged {hook_path.name} hook found at {hook_path}; "
                    "rerun with --force to replace it"
                )
            backup_path = hook_path.with_name(hook_path.name + backup_suffix)
            hook_path.replace(backup_path)
            backup_message = f"backed up existing hook to {backup_path}\n"
        else:
            backup_message = ""
    else:
        backup_message = ""

    hook_path.write_text(new_body)
    hook_path.chmod(0o755)
    return f"{backup_message}installed {hook_path.name} hook at {hook_path}"


def main() -> int:
    args = build_parser().parse_args()
    skill_dir = Path(__file__).resolve().parent.parent
    repo = resolve_repo(args.repo)
    hooks = [
        (
            resolve_hook_path(repo, "commit-msg"),
            build_conventional_commit_hook_body(skill_dir),
            CONVENTIONAL_COMMIT_MARKER,
            CONVENTIONAL_COMMIT_BACKUP_SUFFIX,
        ),
        (
            resolve_hook_path(repo, "post-commit"),
            build_hook_body(skill_dir),
            MANAGED_MARKER,
            BACKUP_SUFFIX,
        ),
    ]

    for hook_path, new_body, marker, _backup_suffix in hooks:
        error = _check_unmanaged_hook(hook_path, marker, new_body)
        if error and not args.force:
            print(error)
            return 2

    for hook_path, new_body, marker, backup_suffix in hooks:
        print(_install_hook(hook_path, new_body, marker, backup_suffix, args.force))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
