# github-push-skill

Codex skill for deciding when a repository is ready to commit, push, and open a pull request.

## About

This skill keeps each commit focused on one feature, enforces Conventional Commits 1.0.0 for every new commit, and uses the review path `commit -> push feature branch -> open PR` for feature work. It requires a non-empty GitHub repository description before pushing. When the description is missing, the guarded push scripts derive one from the first prose paragraph in `README` or accept an explicit description, update the repository About metadata, and verify it before publishing.

## Contents

- `github-push-when-ready/`: installable skill directory

## Install

Copy the skill into your local Codex skills directory:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -a github-push-when-ready "${CODEX_HOME:-$HOME/.codex}/skills/"
```

## What It Does

- Detect whether the current directory is a Git repository.
- Detect whether a GitHub remote is configured.
- Keep reviewable work on a feature branch instead of pushing directly to the default branch.
- Block pushes when the branch is behind upstream, detached, or conflicted.
- Distinguish between `push`, `commit_then_push`, and `noop`.
- Require the skill's readiness check before every commit or GitHub push.
- Require every new commit message to follow Conventional Commits 1.0.0 (`<type>[optional scope][!]: <description>`).
- Reject invalid commit messages with the managed `commit-msg` hook before a commit is created.
- Split independent work into one feature-scoped commit at a time while keeping each feature's implementation, tests, and documentation atomic.
- Require a completed and verified GitHub repository About description before pushing.
- Require explicit `--pathspec` or `--allow-stage-all` before auto-committing changes.
- Install managed `commit-msg` and `post-commit` hooks that enforce the format, re-check readiness, and auto-push each new commit when it is safe.
- Check for an existing open PR after pushing and create one with GitHub CLI when needed.

## Key Scripts

```bash
python3 github-push-when-ready/scripts/assess_push_readiness.py --json
python3 github-push-when-ready/scripts/push_if_ready.py --message "feat(scope): describe the task" --pathspec path/to/file --execute
# Optional when README does not contain a usable summary:
python3 github-push-when-ready/scripts/push_if_ready.py --message "feat(scope): describe the task" --about-description "A concise repository description" --pathspec path/to/file --execute
gh pr create --fill --base <default-branch> --head <feature-branch>
python3 github-push-when-ready/scripts/install_post_commit_hook.py --repo .
```

## Pull Request Workflow

For one feature or fix, use one feature branch and keep its implementation, tests, and documentation together:

```text
feature branch -> commit -> push -> check for an existing PR -> open PR
```

The PR is created only after the commit has been pushed. Do not create duplicate PRs. A successful commit or push is not itself a successful PR; report the PR URL or the blocker separately. If the current branch is the default branch, create or switch to a feature branch before using the PR workflow.

## Automatic Push Mode

Install the managed Git hooks inside any repository where you want mandatory commit validation and auto-push behavior:

```bash
python3 /path/to/github-push-when-ready/scripts/install_post_commit_hook.py --repo /path/to/repo
```

After installation, non-conforming `git commit` messages are rejected by `commit-msg`. Every successful commit then triggers the skill's readiness check again. The post-commit hook completes and verifies the GitHub repository About description before pushing; it still refuses to push branches that are behind upstream, detached, conflicted, or miss About metadata. The hook only pushes; it does not create a PR. Use the explicit `gh pr create` step after the push.

If a repository already has its own `commit-msg` or `post-commit` hook, the installer refuses to overwrite it unless you pass `--force`. In that case it writes a backup next to the original hook first.

Skill details live in [github-push-when-ready/SKILL.md](github-push-when-ready/SKILL.md).
