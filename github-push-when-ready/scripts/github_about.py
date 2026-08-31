#!/usr/bin/env python3

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from git_push_utils import load_remote_urls


MAX_DESCRIPTION_LENGTH = 350


@dataclass(frozen=True)
class AboutResult:
    ok: bool
    changed: bool
    description: str | None
    message: str


def github_repo_slug(remote_url: str) -> str | None:
    """Return owner/repository for a supported GitHub remote URL."""
    if remote_url.startswith("git@github.com:"):
        path = remote_url.removeprefix("git@github.com:")
    else:
        parsed = urlparse(remote_url)
        if parsed.hostname != "github.com":
            return None
        path = parsed.path

    path = path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    parts = path.split("/")
    if len(parts) != 2 or not all(parts):
        return None
    return "/".join(parts)


def normalize_description(value: str | None) -> str:
    """Normalize and cap a GitHub repository description."""
    if not value:
        return ""
    value = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", value)
    value = re.sub(r"`([^`]+)`", r"\1", value)
    value = " ".join(value.split()).strip()
    return value[:MAX_DESCRIPTION_LENGTH].rstrip()


def readme_description(repo: Path) -> str:
    """Use the first prose paragraph in a README as an About fallback."""
    readme = next(
        (
            repo / name
            for name in ("README.md", "README.rst", "README.txt", "README")
            if (repo / name).is_file()
        ),
        None,
    )
    if readme is None:
        return ""

    paragraph: list[str] = []
    in_code_block = False
    for raw_line in readme.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        if not line:
            if paragraph:
                break
            continue
        if not paragraph and (
            line.startswith("#")
            or line.startswith("<!--")
            or line.startswith("![")
        ):
            continue
        if line.startswith(("- ", "* ", "> ")) and not paragraph:
            continue
        if line.startswith("#"):
            break
        paragraph.append(line)

    return normalize_description(" ".join(paragraph))


def _run_gh(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["gh", *args],
        check=False,
        capture_output=True,
        text=True,
    )


def _gh_description(slug: str) -> tuple[str | None, str | None]:
    result = _run_gh("api", f"repos/{slug}", "--jq", '.description // ""')
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "GitHub API request failed"
        return None, detail
    return normalize_description(result.stdout), None


def ensure_github_about(
    repo: Path,
    remote: str,
    description: str | None = None,
) -> AboutResult:
    """Ensure the selected GitHub remote has a non-empty repository description."""
    remote_urls = load_remote_urls(repo).get(remote, {})
    slug = next(
        (
            github_repo_slug(url)
            for url in (remote_urls.get("push"), remote_urls.get("fetch"))
            if url and github_repo_slug(url)
        ),
        None,
    )
    if slug is None:
        return AboutResult(
            ok=False,
            changed=False,
            description=None,
            message=f"remote {remote!r} is not a supported GitHub repository URL",
        )

    if shutil.which("gh") is None:
        return AboutResult(
            ok=False,
            changed=False,
            description=None,
            message="GitHub CLI (gh) is required to check or complete repository About metadata",
        )

    current, error = _gh_description(slug)
    if error:
        return AboutResult(ok=False, changed=False, description=None, message=error)
    if current:
        return AboutResult(ok=True, changed=False, description=current, message="GitHub About is complete")

    candidate = normalize_description(description) if description is not None else readme_description(repo)
    if not candidate:
        return AboutResult(
            ok=False,
            changed=False,
            description=None,
            message="GitHub About is empty and no description could be derived from the README",
        )

    update = _run_gh("repo", "edit", slug, "--description", candidate)
    if update.returncode != 0:
        detail = update.stderr.strip() or update.stdout.strip() or "GitHub About update failed"
        return AboutResult(ok=False, changed=False, description=None, message=detail)

    verified, error = _gh_description(slug)
    if error:
        return AboutResult(ok=False, changed=True, description=candidate, message=error)
    if not verified:
        return AboutResult(
            ok=False,
            changed=True,
            description=candidate,
            message="GitHub About update completed but the description is still empty",
        )
    return AboutResult(
        ok=True,
        changed=True,
        description=verified,
        message="GitHub About was completed from the README",
    )
