from __future__ import annotations

import sys
import unittest
from pathlib import Path
from subprocess import CompletedProcess, run
from tempfile import TemporaryDirectory
from unittest.mock import patch


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "github-push-when-ready" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from push_if_ready import is_conventional_commit_message  # noqa: E402
from github_about import ensure_github_about, github_repo_slug, readme_description  # noqa: E402
from install_post_commit_hook import (  # noqa: E402
    CONVENTIONAL_COMMIT_MARKER,
    build_conventional_commit_hook_body,
)


class ConventionalCommitMessageTests(unittest.TestCase):
    def test_accepts_standard_headers(self) -> None:
        messages = [
            "feat: add guarded push",
            "fix(cli): reject missing pathspec",
            "refactor(push-flow)!: change readiness contract",
            "feat(user interface): support keyboard navigation",
            "docs: explain commit format\n\nAdditional context.",
            "feat: add body\n\nBody paragraph.\n\nBREAKING CHANGE: update API",
        ]

        for message in messages:
            with self.subTest(message=message):
                self.assertTrue(is_conventional_commit_message(message))

    def test_rejects_nonstandard_headers(self) -> None:
        messages = [
            "Add guarded push",
            "Feat: add guarded push",
            "fix(cli) reject missing colon",
            "fix: ",
            " fix: leading whitespace",
            "fix: trailing whitespace ",
            "fix( scope): leading whitespace in scope",
            "fix(scope ): trailing whitespace in scope",
            "fix(): empty scope",
            "fix:description without required space",
        ]

        for message in messages:
            with self.subTest(message=message):
                self.assertFalse(is_conventional_commit_message(message))


class ConventionalCommitHookTests(unittest.TestCase):
    def _git(self, repo: Path, *args: str) -> CompletedProcess[str]:
        return run(
            ["git", "-C", str(repo), *args],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_installer_rejects_nonconventional_direct_git_commits(self) -> None:
        with TemporaryDirectory() as directory:
            repo = Path(directory)
            self.assertEqual(self._git(repo, "init", "-q").returncode, 0)
            self.assertEqual(
                self._git(repo, "config", "user.name", "Test User").returncode,
                0,
            )
            self.assertEqual(
                self._git(repo, "config", "user.email", "test@example.com").returncode,
                0,
            )

            install = run(
                [
                    sys.executable,
                    str(SCRIPTS_DIR / "install_post_commit_hook.py"),
                    "--repo",
                    str(repo),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(install.returncode, 0, install.stdout + install.stderr)

            commit_msg_hook = repo / ".git" / "hooks" / "commit-msg"
            self.assertTrue(commit_msg_hook.is_file())
            self.assertIn(CONVENTIONAL_COMMIT_MARKER, commit_msg_hook.read_text())

            (repo / "file.txt").write_text("content\n", encoding="utf-8")
            self.assertEqual(self._git(repo, "add", "file.txt").returncode, 0)
            invalid = self._git(repo, "commit", "-m", "Add file")
            self.assertNotEqual(invalid.returncode, 0)
            self.assertNotEqual(self._git(repo, "rev-parse", "--verify", "HEAD").returncode, 0)

            valid = self._git(repo, "commit", "-m", "feat: add file")
            self.assertEqual(valid.returncode, 0, valid.stdout + valid.stderr)

class ConventionalCommitHookBodyTests(unittest.TestCase):
    def test_hook_calls_validator_with_commit_message_path(self) -> None:
        body = build_conventional_commit_hook_body(SCRIPTS_DIR.parent)
        self.assertIn("#!/bin/sh", body)
        self.assertIn(CONVENTIONAL_COMMIT_MARKER, body)
        self.assertIn('"$1"', body)


class GithubAboutTests(unittest.TestCase):
    def test_parses_supported_github_remote_urls(self) -> None:
        urls = [
            "https://github.com/example/project.git",
            "git@github.com:example/project.git",
            "ssh://git@github.com/example/project",
        ]

        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(github_repo_slug(url), "example/project")

    def test_reads_first_prose_paragraph(self) -> None:
        with TemporaryDirectory() as directory:
            repo = Path(directory)
            (repo / "README.md").write_text(
                "# Project\n\nA concise project summary.\n\n## Details\n",
                encoding="utf-8",
            )
            self.assertEqual(readme_description(repo), "A concise project summary.")

    @patch("github_about.shutil.which", return_value="/usr/bin/gh")
    @patch(
        "github_about.load_remote_urls",
        return_value={"origin": {"push": "https://github.com/example/project.git"}},
    )
    @patch("github_about._run_gh")
    def test_fills_missing_description_and_verifies_it(
        self,
        run_gh,
        _load_remote_urls,
        _which,
    ) -> None:
        run_gh.side_effect = [
            CompletedProcess([], 0, "", ""),
            CompletedProcess([], 0, "", ""),
            CompletedProcess([], 0, "A concise project summary.", ""),
        ]
        with TemporaryDirectory() as directory:
            repo = Path(directory)
            (repo / "README.md").write_text(
                "# Project\n\nA concise project summary.\n",
                encoding="utf-8",
            )
            result = ensure_github_about(repo, "origin")

        self.assertTrue(result.ok)
        self.assertTrue(result.changed)
        self.assertEqual(result.description, "A concise project summary.")
        self.assertEqual(
            run_gh.call_args_list[1].args,
            ("repo", "edit", "example/project", "--description", "A concise project summary."),
        )


if __name__ == "__main__":
    unittest.main()
