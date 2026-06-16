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
- Require explicit `--pathspec` or `--allow-stage-all` before auto-committing changes.

## Key Scripts

```bash
python3 github-push-when-ready/scripts/assess_push_readiness.py --json
python3 github-push-when-ready/scripts/push_if_ready.py --message "Describe the task" --pathspec path/to/file --execute
```

Skill details live in [github-push-when-ready/SKILL.md](github-push-when-ready/SKILL.md).
