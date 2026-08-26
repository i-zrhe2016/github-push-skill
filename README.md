# github-push-skill

Codex skill for deciding when a repository is ready to commit and push to GitHub.

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
- Block pushes when the branch is behind upstream, detached, or conflicted.
- Distinguish between `push`, `commit_then_push`, and `noop`.
- Require the skill's readiness check before every commit or GitHub push.
- Require new commit messages to follow Conventional Commits (`type(scope): description`).
- Split independent work into feature-scoped commits while keeping each feature's implementation, tests, and documentation atomic.
- Require explicit `--pathspec` or `--allow-stage-all` before auto-committing changes.
- Optionally install a `post-commit` hook that re-checks readiness and auto-pushes each new commit when it is safe.

## Key Scripts

```bash
python3 github-push-when-ready/scripts/assess_push_readiness.py --json
python3 github-push-when-ready/scripts/push_if_ready.py --message "feat(scope): describe the task" --pathspec path/to/file --execute
python3 github-push-when-ready/scripts/install_post_commit_hook.py --repo .
```

## Automatic Push Mode

Install the managed Git hook inside any repository where you want auto-push behavior:

```bash
python3 /path/to/github-push-when-ready/scripts/install_post_commit_hook.py --repo /path/to/repo
```

After installation, every successful `git commit` triggers the skill's readiness check again. The hook only pushes when the repo is already in the safe `push` state, so it still refuses to push branches that are behind upstream, detached, conflicted, or missing a GitHub remote.

If a repository already has its own `post-commit` hook, the installer refuses to overwrite it unless you pass `--force`. In that case it writes a backup next to the original hook first.

Skill details live in [github-push-when-ready/SKILL.md](github-push-when-ready/SKILL.md).
