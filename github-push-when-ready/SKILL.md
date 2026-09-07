---
name: github-push-when-ready
description: Guard every Git commit, GitHub push, and pull request by assessing repository readiness, enforcing Conventional Commits 1.0.0, keeping one feature per commit, completing GitHub About metadata, and publishing only when safe. Use whenever Codex is about to commit, push, or open a PR, finishes a coherent unit of code work in a GitHub-connected repo, or is asked to ship, publish, or sync changes.
---

# GitHub Push When Ready

## Overview

Inspect the current repository, detect whether a GitHub remote is configured, and classify the repo as ready to commit and push, ready to open a pull request, or not ready. Prefer the bundled scripts for repeatable checks; only publish after the task is complete, validations have passed, and the working tree changes belong to the task at hand. For feature work, the default delivery path is `commit -> push feature branch -> open PR`; a PR does not replace the commit.

## Mandatory Use and Commit Boundaries

- Invoke this skill before every action or script that will create a Git commit, push to GitHub, or open/update a pull request. Do not run a direct `git commit`, `git push`, amend, or equivalent publishing workflow first and assess afterward.
- For a feature, fix, or documentation change intended for review, work on a feature branch different from the repository's default branch. Commit the completed unit first, push that branch, and then open one PR for the unit. Push directly to the default branch only when the user or repository policy explicitly requires it.
- Group changes by coherent user-visible feature, fix, refactor, or documentation-only task. When the worktree contains independent units, commit each unit separately.
- Keep a feature's implementation, directly related tests, and documentation in the same commit when they form one atomic change. Do not split commits merely by file type.
- If a pending change set contains multiple features, split it into one feature per commit. A commit must not combine unrelated features; keep each feature's implementation, tests, and documentation together.
- Enforce Conventional Commits 1.0.0 for every new commit: `<type>[optional scope][!]: <description>`. The type must be lowercase, the description must be non-empty, and a scope must be non-empty when present. Body and footer content remain allowed by the specification.
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

Before a GitHub push, treat the repository About as required metadata. For this skill, About means a non-empty GitHub repository description; homepage and topics are optional. If it is empty, derive a concise description from the README or provide one explicitly, update it with GitHub CLI, and verify the update before pushing. If the update cannot be completed, do not push.

After a successful feature-branch push, check for an existing open PR before creating one. Do not create duplicate PRs. If none exists, verify that GitHub CLI is authenticated and create the PR against the repository's default branch:

```bash
gh pr create --fill --base <default-branch> --head <feature-branch>
```

If the current branch is the default branch, stop before opening a PR and ask for or create a feature branch. If PR creation fails after the push, report the pushed branch and the exact PR blocker; do not claim the feature is delivered through a PR.

To enforce commit messages and auto-check/auto-push after every new commit, install the managed `commit-msg` and `post-commit` hooks:

```bash
python3 <skill-dir>/scripts/install_post_commit_hook.py --repo .
```

After that, invalid commit messages are rejected before a commit is created. Each valid local commit then triggers a fresh readiness check. The post-commit hook pushes only when the repo reaches the existing safe `push` state. It will not auto-commit leftover changes, and it will skip pushes when the branch is behind upstream, detached, conflicted, or missing a GitHub remote.

## Workflow

1. Inspect `git status` and the relevant diff, identify the repository's default branch, and choose a feature branch when the change is intended for review.
2. Run `assess_push_readiness.py` in the target repo before the first commit or push.
3. Stop immediately if the repo is not a Git repo, has no GitHub remote, is on a detached HEAD, has conflicts, or is behind its upstream branch.
4. Treat `commit_then_push` as eligible only when the current functional unit is complete, its checks are green, and the selected paths or hunks contain no unrelated work.
5. Before any push, verify unpublished commit subjects follow Conventional Commits 1.0.0 and check/complete the GitHub repository About description. The guarded scripts do this automatically when executed.
6. Treat `push` as eligible only when the working tree is clean, the local branch is ahead of its upstream or has no upstream yet, and About verification succeeds.
7. Use `push_if_ready.py --execute` with explicit `--pathspec` values for the standard guarded commit-and-push flow. If one file mixes multiple functional units, stage only the intended hunks manually after assessment, then use the equivalent guarded commit and push commands.
8. After the push succeeds, check for an open PR for the feature branch and create one with `gh pr create` when needed. Record the PR URL or the blocker.
9. For another functional unit, re-inspect the remaining diff and restart this workflow from the readiness assessment.

## Push Rules

- Refuse to push unresolved conflicts or code that failed validation.
- Refuse to push if the branch is behind upstream; rebase or pull first.
- Refuse to push when the GitHub repository About description is empty or could not be verified after an attempted update.
- Refuse to force-push unless the user explicitly asks for it.
- Refuse to auto-stage all changes when unrelated user work is mixed into the same worktree; ask before combining unrelated edits into one commit.
- Refuse to combine independent features into one commit merely because they were completed in the same session.
- Prefer `git push -u <remote> <branch>` when the branch has no upstream yet.
- Prefer clear commit messages tied to the completed task boundary.
- Prefer one PR per coherent feature, fix, or documentation change; keep related tests and documentation in that PR.
- Do not treat a successful commit or push as a successful PR. Report each stage separately.

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
- Reject commit messages whose first line does not follow the Conventional Commits 1.0.0 header format.
- Require `--pathspec` or `--allow-stage-all` before creating a commit.
- Check the selected GitHub repository About before committing or pushing; if its description is missing, fill it from the README or `--about-description`, then verify it.
- Push with `git push` when upstream exists.
- Push with `git push -u <remote> <branch>` when upstream is missing.
- It does not create a pull request. After it succeeds, check for an existing PR and run `gh pr create --fill --base <default-branch> --head <feature-branch>` when needed.

### `scripts/install_post_commit_hook.py`

Installs managed Git `commit-msg` and `post-commit` hooks into the target repository. The `commit-msg` hook rejects messages that violate Conventional Commits 1.0.0. The `post-commit` hook calls `auto_push_post_commit.py` after every successful commit and exits cleanly even when the push is skipped.

Use `--force` only when you intentionally want to replace an existing unmanaged hook. The installer writes a backup file before replacing it.

### `scripts/auto_push_post_commit.py`

Runs the same readiness assessment after each valid commit, completes/verifies GitHub About metadata, and pushes only when `recommended_action` is `push`. It does not open PRs because a post-commit hook lacks the review title/body and branch intent; use the explicit PR step after the push. This keeps the automatic mode conservative: partial commits, unresolved conflicts, missing GitHub remotes, missing About metadata, and branches that are behind upstream are all skipped instead of being forced through.

Set `CODEX_GITHUB_AUTO_PUSH_SKIP=1` to bypass one hook invocation. `push_if_ready.py` sets this automatically for its own commit step so a scripted `commit_then_push` flow does not double-trigger the push.

## Response Pattern

Summarize the decision in three parts:

1. Whether the repo is connected to GitHub.
2. Whether the repo is ready to commit, ready to push, or blocked.
3. Whether a PR already exists, was created, or is blocked, with the exact next command when applicable.

If a push was executed, report the branch, remote, and whether a commit was created first. If a PR was created or found, report its URL.
If a push was skipped, report the blocking condition instead of hand-waving.
