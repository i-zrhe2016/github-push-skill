---
name: github-push-when-ready
description: Assess whether a Git repository is ready to be committed and pushed to GitHub, then perform the guarded push workflow when it is safe. Use when Codex finishes a coherent unit of code work in a repo that may already be connected to GitHub, or when the user asks to ship, publish, sync, or push changes without pushing half-finished, conflicted, or unsynced work.
---

# GitHub Push When Ready

## Overview

Inspect the current repository, detect whether a GitHub remote is configured, and classify the repo as ready to push, ready to commit then push, or not ready. Prefer the bundled scripts for repeatable checks; only push after the task is complete, validations have passed, and the working tree changes belong to the task at hand.

## Quick Start

Run the readiness check from the repository root:

```bash
python3 <skill-dir>/scripts/assess_push_readiness.py --json
```

Interpret `recommended_action` like this:

- `push`: the repo is clean and has commits ready to publish.
- `commit_then_push`: the repo has local changes and can be committed, then pushed.
- `noop`: nothing needs to be pushed.
- `sync_first`, `resolve_conflicts`, `manual_review`, `no_github_remote`, `not_git_repo`: do not push yet.

To auto-check and auto-push after every new commit, install the managed `post-commit` hook:

```bash
python3 <skill-dir>/scripts/install_post_commit_hook.py --repo .
```

After that, each successful local commit triggers a fresh readiness check. The hook pushes only when the repo reaches the existing safe `push` state. It will not auto-commit leftover changes, and it will skip pushes when the branch is behind upstream, detached, conflicted, or missing a GitHub remote.

## Workflow

1. Run `assess_push_readiness.py` in the target repo.
2. Stop immediately if the repo is not a Git repo, has no GitHub remote, is on a detached HEAD, has conflicts, or is behind its upstream branch.
3. Treat `commit_then_push` as eligible only when the task is complete, checks are green, and the changed files all belong to the current task.
4. Treat `push` as eligible only when the working tree is clean and the local branch is ahead of its upstream or has no upstream yet.
5. Use `push_if_ready.py --execute` for the standard guarded flow, or run the equivalent Git commands manually if the task requires a narrower staging set.

## Push Rules

- Refuse to push unresolved conflicts or code that failed validation.
- Refuse to push if the branch is behind upstream; rebase or pull first.
- Refuse to force-push unless the user explicitly asks for it.
- Refuse to auto-stage all changes when unrelated user work is mixed into the same worktree; ask before combining unrelated edits into one commit.
- Prefer `git push -u <remote> <branch>` when the branch has no upstream yet.
- Prefer clear commit messages tied to the completed task boundary.

## Resources

### `scripts/assess_push_readiness.py`

Use this script first. It inspects branch state, upstream state, worktree cleanliness, conflicts, and GitHub remote wiring, then returns a recommendation plus suggested commands.

### `scripts/push_if_ready.py`

Use this script after the repo is confirmed ready. It performs the guarded flow below:

```bash
python3 <skill-dir>/scripts/push_if_ready.py \
  --message "Describe the completed task" \
  --pathspec path/to/file \
  --execute
```

Behavior:

- Dry-run by default.
- Commit only when the readiness check returns `commit_then_push`.
- Require `--pathspec` or `--allow-stage-all` before creating a commit.
- Push with `git push` when upstream exists.
- Push with `git push -u <remote> <branch>` when upstream is missing.

### `scripts/install_post_commit_hook.py`

Installs a managed Git `post-commit` hook into the target repository. The hook calls `auto_push_post_commit.py` after every successful commit and exits cleanly even when the push is skipped.

Use `--force` only when you intentionally want to replace an existing unmanaged `post-commit` hook. The installer writes a backup file before replacing it.

### `scripts/auto_push_post_commit.py`

Runs the same readiness assessment after each commit and pushes only when `recommended_action` is `push`. This keeps the automatic mode conservative: partial commits, unresolved conflicts, missing GitHub remotes, and branches that are behind upstream are all skipped instead of being forced through.

Set `CODEX_GITHUB_AUTO_PUSH_SKIP=1` to bypass one hook invocation. `push_if_ready.py` sets this automatically for its own commit step so a scripted `commit_then_push` flow does not double-trigger the push.

## Response Pattern

Summarize the decision in three parts:

1. Whether the repo is connected to GitHub.
2. Whether the repo is ready to push now, ready after a commit, or blocked.
3. The exact next command or reason for not pushing.

If a push was executed, report the branch, remote, and whether a commit was created first.
If a push was skipped, report the blocking condition instead of hand-waving.
