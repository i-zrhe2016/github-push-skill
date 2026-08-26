---
name: github-push-when-ready
description: Guard every Git commit and GitHub push by assessing repository readiness, splitting independent work into feature-scoped commits, and publishing only when safe. Use whenever Codex is about to commit or push, finishes a coherent unit of code work in a GitHub-connected repo, or is asked to ship, publish, or sync changes.
---

# GitHub Push When Ready

## Overview

Inspect the current repository, detect whether a GitHub remote is configured, and classify the repo as ready to push, ready to commit then push, or not ready. Prefer the bundled scripts for repeatable checks; only push after the task is complete, validations have passed, and the working tree changes belong to the task at hand.

## Mandatory Use and Commit Boundaries

- Invoke this skill before every action or script that will create a Git commit or push to GitHub. Do not run a direct `git commit`, `git push`, amend, or equivalent publishing workflow first and assess afterward.
- Group changes by coherent user-visible feature, fix, refactor, or documentation-only task. When the worktree contains independent units, commit each unit separately.
- Keep a feature's implementation, directly related tests, and documentation in the same commit when they form one atomic change. Do not split commits merely by file type.
- Format every new commit message as Conventional Commits: `<type>[optional scope][!]: <description>`. Use a lowercase type such as `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `build`, `ci`, `perf`, or `style`; add a scope only when it makes the affected area clearer. Mark breaking changes with `!` and explain them in the commit body or a `BREAKING CHANGE:` footer when useful.
- Review the diff for each planned commit and stage only its paths or hunks. Prefer explicit `--pathspec` values; never use `--allow-stage-all` when unrelated or independently committable work is present.
- Validate each functional unit before committing it. Re-run the readiness assessment before each subsequent commit or push because the repository state has changed.
- Do not create empty commits or push again when the assessment returns `noop`.

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

1. Inspect `git status` and the relevant diff, then identify coherent functional commit boundaries.
2. Run `assess_push_readiness.py` in the target repo before the first commit or push.
3. Stop immediately if the repo is not a Git repo, has no GitHub remote, is on a detached HEAD, has conflicts, or is behind its upstream branch.
4. Treat `commit_then_push` as eligible only when the current functional unit is complete, its checks are green, and the selected paths or hunks contain no unrelated work.
5. Treat `push` as eligible only when the working tree is clean and the local branch is ahead of its upstream or has no upstream yet.
6. Use `push_if_ready.py --execute` with explicit `--pathspec` values for the standard guarded flow. If one file mixes multiple functional units, stage only the intended hunks manually after assessment, then use the equivalent guarded commit and push commands.
7. For another functional unit, re-inspect the remaining diff and restart this workflow from the readiness assessment.

## Push Rules

- Refuse to push unresolved conflicts or code that failed validation.
- Refuse to push if the branch is behind upstream; rebase or pull first.
- Refuse to force-push unless the user explicitly asks for it.
- Refuse to auto-stage all changes when unrelated user work is mixed into the same worktree; ask before combining unrelated edits into one commit.
- Refuse to combine independent features into one commit merely because they were completed in the same session.
- Prefer `git push -u <remote> <branch>` when the branch has no upstream yet.
- Prefer clear commit messages tied to the completed task boundary.

## Resources

### `scripts/assess_push_readiness.py`

Use this script first. It inspects branch state, upstream state, worktree cleanliness, conflicts, and GitHub remote wiring, then returns a recommendation plus suggested commands.

### `scripts/push_if_ready.py`

Use this script after the repo is confirmed ready. It performs the guarded flow below:

```bash
python3 <skill-dir>/scripts/push_if_ready.py \
  --message "feat(scope): describe the completed task" \
  --pathspec path/to/file \
  --execute
```

Behavior:

- Dry-run by default.
- Commit only when the readiness check returns `commit_then_push`.
- Reject commit messages whose first line does not follow the Conventional Commits header format.
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
